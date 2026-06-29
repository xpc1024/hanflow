"""PrivacyStrategy — the privacy routing policy + PII detection/redaction (§4.4).

Rules:
1. sensitivity<=internal AND no PII → strategy does not engage (returns []).
2. sensitivity>=confidential OR PII detected:
   a. only return is_local=True providers
   b. if PII, mark candidate reason 'redact' (caller redacts then calls local)
   c. enforce='hard' and no local provider → raise PrivacyViolationError
3. Returned candidates have score=Inf (top priority — privacy veto).

Data sensitivity comes from node ``sensitivity`` + runtime PII detection (the
strictest wins). PII is detected pre-routing, redacted before local call, and
restored after output. Audits go to trace + logs.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel

from hanflow.core.errors import PrivacyViolationError
from hanflow.models.strategies.base import ModelCandidate, RoutingRequest, RoutingStrategy

_SENSITIVITY_RANK = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\b1[3-9]\d{9}\b")
_IDCARD = re.compile(r"\b\d{17}[\dXx]\b")
_CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


class PIIResult(BaseModel):
    emails: list[str] = []
    phones: list[str] = []
    id_cards: list[str] = []
    cards: list[str] = []

    @property
    def has_any(self) -> bool:
        return bool(self.emails or self.phones or self.id_cards or self.cards)


class RedactionMap(BaseModel):
    tokens: dict[str, str] = {}  # placeholder → original


class PIIConfig(BaseModel):
    regex: bool = True
    ner_model: str | None = None


class PrivacyRule(BaseModel):
    when: str
    then: dict[str, Any]


class PrivacyConfig(BaseModel):
    rules: list[PrivacyRule] = []
    enforce: Literal["hard", "soft"] = "hard"
    audit: bool = True
    pii_detection: PIIConfig = PIIConfig()
    local_providers: list[str] = []


class PrivacyStrategy(RoutingStrategy):
    name = "privacy"

    def __init__(self, config: PrivacyConfig) -> None:
        self.config = config

    def candidates(
        self, request: RoutingRequest, providers: dict[str, Any]
    ) -> list[ModelCandidate]:
        sensitive = _SENSITIVITY_RANK[request.sensitivity] >= _SENSITIVITY_RANK["confidential"]
        pii = (
            self._detect_pii_sync(request.messages)
            if self.config.pii_detection.regex
            else PIIResult()
        )
        engages = sensitive or pii.has_any
        if not engages:
            return []

        local = [
            (name, p)
            for name, p in providers.items()
            if getattr(p, "is_local", False) or name in self.config.local_providers
        ]
        if not local:
            if self.config.enforce == "hard":
                raise PrivacyViolationError(
                    "no local provider available for sensitive/PII data",
                    details={"sensitivity": request.sensitivity, "pii": pii.has_any},
                )
            return []  # soft: warn + degrade (caller logs)

        reason = "privacy:redact" if pii.has_any else "privacy:local"
        return [
            ModelCandidate(provider=name, model="", score=float("inf"), reason=reason)
            for name, _ in local
        ]

    # --- PII detection / redaction ----------------------------------------- #
    async def detect_pii(self, messages: list[Any]) -> PIIResult:
        return self._detect_pii_sync(messages)

    def _detect_pii_sync(self, messages: list[Any]) -> PIIResult:
        text = " ".join(_msg_text(m) for m in messages)
        return PIIResult(
            emails=_EMAIL.findall(text),
            phones=_PHONE.findall(text),
            id_cards=_IDCARD.findall(text),
            cards=_CARD.findall(text),
        )

    async def redact(
        self, messages: list[Any], pii: PIIResult
    ) -> tuple[list[Any], RedactionMap]:
        mapping: dict[str, str] = {}
        redacted: list[Any] = []
        for m in messages:
            content = _msg_text(m)
            for kind, hits in (
                ("email", pii.emails),
                ("phone", pii.phones),
                ("idcard", pii.id_cards),
                ("card", pii.cards),
            ):
                for hit in hits:
                    if hit in mapping.values():
                        placeholder = next(p for p, v in mapping.items() if v == hit)
                    else:
                        placeholder = f"<<{kind}:{uuid.uuid4().hex[:6]}>>"
                        mapping[placeholder] = hit
                    content = content.replace(hit, placeholder)
            new_m = dict(m)
            new_m["content"] = content
            redacted.append(new_m)
        return redacted, RedactionMap(tokens=mapping)


def _msg_text(m: Any) -> str:
    if isinstance(m, dict):
        return str(m.get("content", ""))
    return str(getattr(m, "content", ""))
