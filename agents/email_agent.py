from smolagents import Tool, ToolCallingAgent
from typing import Sequence
from tools.email.check_mails import check_mails
from core.managed_prompts import load_agent_prompts

prompts = load_agent_prompts("email_agent")

def email_agent(model: str) -> ToolCallingAgent:
    email_agent = ToolCallingAgent(
        model=model,
        tools=[
            check_mails,
        ],
        name="email_agent",
        description=prompts.description,
        instructions=prompts.system,
        add_base_tools=False,
        max_steps=3,
    )

    return email_agent
