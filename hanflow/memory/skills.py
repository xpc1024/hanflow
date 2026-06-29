"""SkillsLoader — declarative SKILL.md capability loading (§7.2).

Each skill is a Markdown file with YAML front-matter (name/description/trigger/
tools) + a body of instructions. Matching is two-stage: keyword pre-filter
(default, cheap) + optional LLM re-rank (off by default). ``render_prompt``
turns a set of skills into a system prompt fragment injected into sub-agents.
``skill.tools`` bounds a sub-agent's tool whitelist (capability boundary).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from hanflow.core.errors import HanflowError
from hanflow.observability.trace import TraceExporter

_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


class SkillTrigger(BaseModel):
    keywords: list[str] = []
    task_type: str | None = None
    description_match: bool = True


class SkillDoc(BaseModel):
    name: str
    description: str
    version: str = "0.1.0"
    trigger: SkillTrigger
    instructions: str
    tools: list[str] = []
    inputs: dict[str, Any] = {}
    source_path: str


class SkillMatch(BaseModel):
    skill: SkillDoc
    score: float
    reason: str


class SkillsLoader:
    def __init__(self, skills_dirs: list[Path], trace: TraceExporter) -> None:
        self.skills_dirs = [Path(d) for d in skills_dirs]
        self.trace = trace
        self._skills: dict[str, SkillDoc] = {}

    async def load_all(self) -> None:
        for d in self.skills_dirs:
            if not d.exists():
                continue
            for md in d.rglob("*.md"):
                doc = self._parse(md)
                if doc is not None:
                    self._skills[doc.name] = doc

    def _parse(self, path: Path) -> SkillDoc | None:
        text = path.read_text(encoding="utf-8")
        m = _FRONT_MATTER.match(text)
        if not m:
            return None
        meta = yaml.safe_load(m.group(1)) or {}
        instructions = m.group(2).strip()
        return SkillDoc(
            name=meta.get("name", path.stem),
            description=meta.get("description", ""),
            version=str(meta.get("version", "0.1.0")),
            trigger=SkillTrigger(**(meta.get("trigger") or {})),
            instructions=instructions,
            tools=meta.get("tools", []),
            inputs=meta.get("inputs", {}),
            source_path=str(path),
        )

    async def load_skill(self, name: str) -> SkillDoc:
        if name not in self._skills:
            raise HanflowError(f"skill not found: {name!r}")
        return self._skills[name]

    async def match_skills(
        self, task: str, *, task_type: str | None = None, limit: int = 3
    ) -> list[SkillMatch]:
        task_lower = task.lower()
        scored: list[SkillMatch] = []
        for doc in self._skills.values():
            hits = sum(1 for kw in doc.trigger.keywords if kw.lower() in task_lower)
            type_hit = task_type is not None and doc.trigger.task_type == task_type
            score = hits + (1 if type_hit else 0)
            if score > 0:
                scored.append(
                    SkillMatch(
                        skill=doc,
                        score=float(score),
                        reason=f"keywords={hits},type={type_hit}",
                    )
                )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def render_prompt(self, skills: list[SkillDoc]) -> str:
        if not skills:
            return ""
        parts = ["# Active skills"]
        for s in skills:
            parts.append(f"\n## {s.name}\n{s.description}\n\n{s.instructions}")
        return "\n".join(parts)
