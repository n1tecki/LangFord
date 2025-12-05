from smolagents import Tool, ToolCallingAgent
from typing import Sequence
from tools.news.get_news import news_report
from tools.news.financial_market import get_financial_market_updates
from core.managed_prompts import load_agent_prompts

prompts = load_agent_prompts("news_agent")

def news_agent(model: str) -> ToolCallingAgent:
    news_agent = ToolCallingAgent(
        model=model,
        tools=[
            news_report,
            get_financial_market_updates
        ],
        name="news_agent",
        description=prompts.description,
        instructions=prompts.system,
        add_base_tools=False,
        max_steps=3,
    )

    return news_agent
