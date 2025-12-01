from dataclasses import dataclass
from smolagents import ToolCallingAgent

from agents.calendar_agent import calendar_agent
from agents.email_agent import email_agent
from agents.news_agent import news_agent
from agents.weather_agent import weather_agent


@dataclass
class AgentContainer:
    news: ToolCallingAgent
    email: ToolCallingAgent
    calendar: ToolCallingAgent
    weather: ToolCallingAgent


def build_agents(model: str) -> AgentContainer:
    return AgentContainer(
        calendar=calendar_agent(model),
        email=email_agent(model),
        news=news_agent(model),
        weather=weather_agent(model),
    )
