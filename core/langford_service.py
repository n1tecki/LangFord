# core/langford_service.py
from typing import Optional
from smolagents import ToolCallingAgent, LogLevel
from core.llm import llm_object
from core.managed_agents import build_agents
from core.managed_prompts import load_agent_prompts

_llm = None
_butler: Optional[ToolCallingAgent] = None


def init_langford():
    global _llm, _butler
    if _butler is not None:
        return

    _llm = llm_object()
    agents = build_agents(model=_llm.model)
    prompts = load_agent_prompts("langford")

    _butler = ToolCallingAgent(
        model=_llm.model,
        tools=[],
        managed_agents=[agents.calendar, agents.email, agents.news, agents.weather],
        name="langford",
        description=prompts.description,
        instructions=prompts.system,
        verbosity_level=LogLevel.DEBUG,
        add_base_tools=False,
        max_steps=8,
    )


def run_langford(message: str) -> str:
    assert _butler is not None, "init_langford() must be called first"
    msg = message.strip()
    if msg.lower() == "brief":
        query = "Please provide my full morning executive brief for today."
        return _butler.run(query, reset=True)
    return _butler.run(msg, reset=False)
