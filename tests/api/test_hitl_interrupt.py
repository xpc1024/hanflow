from datetime import UTC, datetime

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from hanflow.core.dsl import WorkflowDSL
from hanflow.core.result import HITLRecord
from hanflow.orchestration.compiler import Compiler
from hanflow.orchestration.registry import NodeExecutorRegistry


@pytest.mark.asyncio
async def test_hitl_node_pauses_then_resumes(ctx):
    """A HITL node interrupts; resuming with approve continues to the next node."""
    dsl = WorkflowDSL(
        name="w",
        nodes=[
            {"id": "gate", "type": "HITL", "config": {"actions": ["approve"]}},  # type: ignore[call-arg]
            {"id": "after", "type": "LLM", "depends_on": ["gate"], "config": {"template": "ok"}},  # type: ignore[call-arg]
        ],
    )
    compiler = Compiler(NodeExecutorRegistry.default())
    compiled = compiler.compile(dsl, checkpoint=MemorySaver(), ctx=ctx)

    config = {"configurable": {"thread_id": "t1"}}
    # First invoke hits the HITL node → pauses (interrupt)
    result = await compiled.graph.ainvoke(ctx.state, config=config)
    assert "__interrupt__" in result  # graph paused at the gate

    # Resume with an approve HITLRecord
    record = HITLRecord(
        action="approve",
        decided_by="tester",
        decided_at=datetime.now(UTC),
        duration_seconds=1.0,
    )
    result2 = await compiled.graph.ainvoke(
        Command(resume={"hitl": record.model_dump(mode="json")}), config=config
    )
    # After resume, the 'after' node should have run
    after = result2["node_states"].get("after")
    assert after is not None
    status = after.status if hasattr(after, "status") else after.get("status")
    assert status == "succeeded"
