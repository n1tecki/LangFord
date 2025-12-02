from smolagents import Tool, ToolCallingAgent
from typing import Sequence
from tools.weather.check_weather import get_weather
from core.managed_prompts import load_agent_prompts

prompts = load_agent_prompts("weather_agent")

def weather_agent(model: str) -> ToolCallingAgent:
    weather_agent = ToolCallingAgent(
        model=model,
        tools=[
            get_weather,
        ],
        name="weather_agent",
        description=prompts.description,
        instructions=prompts.system,
        add_base_tools=False,
    )

    return weather_agent
