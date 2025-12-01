from smolagents import Tool, ToolCallingAgent
from typing import Sequence
from tools.calendar.check_events import check_events
from tools.calendar.create_events import create_events
from tools.calendar.resolve_date_expression import resolve_date_expression
from core.managed_prompts import load_agent_prompts

prompts = load_agent_prompts("calendar_agent")

def calendar_agent(model: str) -> ToolCallingAgent:
    calendar_agent = ToolCallingAgent(
        model=model,
        tools=[
            check_events, 
            create_events,
            resolve_date_expression
        ],
        name="calendar_agent",
        description=(
            prompts.description,
        ),
        instructions=(
            prompts.system
        ),
    )

    return calendar_agent