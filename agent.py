from smolagents import ToolCallingAgent, LogLevel
from llm import llm_object
from tools.calendar.create_events import create_events
from tools.calendar.check_events import check_events
from tools.weather.check_weather import get_weather
from tools.news.get_news import news_report
from tools.email.check_mails import outlook_important_emails
from tools.finance.market_overview import get_finviz_market_updates
import datetime
from typing import Tuple, List


TOOLS: List = [
    create_events,
    check_events,
    get_weather,
    news_report,
    outlook_important_emails,
    get_finviz_market_updates,
]


def show(text):
    # Make sure we work with a plain string
    s = str(text)
    s = s.replace("\\r\\n", "\n")
    s = s.replace("\\n", "\n")
    s = s.replace("\\r", "\n")
    s = s.replace("\\\\n", "\n")
    return s


def _build_prompt(path: str) -> str:
    """Load a base prompt from file and enrich it with dynamic context."""
    with open(path, encoding="utf-8") as fp:
        prompt = fp.read()

    now = datetime.datetime.now()
    prompt += f"\n Today is {now}"
    prompt += "\n The person of interes is in Vienna, Austria"
    prompt += "\n Persons request: "
    return prompt


def load_prompts() -> Tuple[str, str]:
    """Load system and brief prompts with dynamic context once at startup."""
    system_prompt = _build_prompt("prompts/system_prompt.txt")
    brief_prompt = _build_prompt("prompts/brief_prompt.txt")
    return system_prompt, brief_prompt


def create_agent(llm, system_prompt: str, max_step: int = 6) -> ToolCallingAgent:
    """Create a ToolCallingAgent with a given system prompt."""
    agent = ToolCallingAgent(
        tools=TOOLS,
        model=llm.model,
        verbosity_level=LogLevel.DEBUG,  # LogLevel.DEBUG
        add_base_tools=False,
        max_steps=max_step,
    )
    # Replace the default system prompt with our custom one
    agent.prompt_templates["system_prompt"] += system_prompt
    return agent


def handle_brief(llm, brief_prompt: str) -> None:
    """Handle the special 'brief' command."""
    brief_agent = create_agent(llm, brief_prompt, max_step=10)
    user_msg = "brief"  # semantic tag for your logs/memory
    llm.remember("user", user_msg)
    result = brief_agent.run(user_msg, reset=True)
    llm.remember("assistant", result)
    return result


def repl():
    """Main interactive loop."""
    llm = llm_object()
    system_prompt, brief_prompt = load_prompts()

    # Initial agent for regular conversation
    agent = create_agent(llm, system_prompt)

    print("Interactive agent ready. Type 'exit' to quit.\n")

    while True:
        try:
            user_msg = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not user_msg:
            continue

        # Brief on current day
        if user_msg.lower() == "brief":
            result = handle_brief(llm, brief_prompt)

        # Reset chat context + agent
        if user_msg.lower() in {"purge", "reset", "clear", "restart"}:
            agent = create_agent(llm, system_prompt)
            print("Assistant: context cleared. Starting fresh.\n")
            continue

        # Exit application
        if user_msg.lower() in {"exit", "quit", "q"}:
            print("Bye!")
            break

        # Regular question answering
        else:
            llm.remember("user", user_msg)
            result = agent.run(user_msg, reset=False)
            llm.remember("assistant", result)

        print(f"Assistant: {show(result)}")


if __name__ == "__main__":
    repl()
