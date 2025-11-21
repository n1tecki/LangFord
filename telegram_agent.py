import datetime
import logging
from typing import Tuple, List
from dotenv import load_dotenv
import os

from smolagents import ToolCallingAgent, LogLevel
from llm import llm_object
from tools.calendar.create_events import create_events
from tools.calendar.check_events import check_events
from tools.weather.check_weather import get_weather
from tools.news.get_news import news_report
from tools.final_answer import final_answer
from tools.email.check_mails import outlook_important_emails

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- your existing bits -----------------

load_dotenv()
TOOLS: List = [
    create_events,
    check_events,
    get_weather,
    news_report,
    final_answer,
    outlook_important_emails,
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
        verbosity_level=LogLevel.OFF,  # use LogLevel.DEBUG for debugging
        add_base_tools=False,
        max_steps=max_step,
    )
    # Replace the default system prompt with our custom one
    agent.prompt_templates["system_prompt"] += system_prompt
    return agent


# ----------------- global objects for the bot -----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

llm = None
main_agent = None
brief_agent = None


def init_agents():
    global llm, main_agent, brief_agent
    llm = llm_object()
    system_prompt, brief_prompt = load_prompts()
    main_agent = create_agent(llm, system_prompt)
    brief_agent = create_agent(llm, brief_prompt, max_step=10)


def run_agent(user_msg: str) -> str:
    """Core logic shared by Telegram and any other frontend."""
    user_msg = user_msg.strip()

    if user_msg.lower() == "brief":
        result = brief_agent.run("brief", reset=True)
    else:
        llm.remember("user", user_msg)
        result = main_agent.run(user_msg, reset=False)
        llm.remember("assistant", result)

    return show(result)


# ----------------- Telegram handlers -----------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Respond to /start command."""
    await update.message.reply_text(
        "Hello, I am your Langford agent on Telegram.\n"
        "Just send me a message to talk to the agent.\n"
        "Send 'brief' to get your daily executive brief."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available commands:\n"
        "/start – introduction\n"
        "/help – this help message\n"
        "Any normal message – forwarded to the agent\n"
        "'brief' – generates your daily brief"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message."""
    if update.message is None or update.message.text is None:
        return

    user_text = update.message.text
    user_id = update.effective_user.id
    logger.info("Message from %s: %s", user_id, user_text)

    try:
        reply = run_agent(user_text)
    except Exception:
        logger.exception("Error while running agent:")
        reply = "Something went wrong in the backend. Please try again in a moment."

    await update.message.reply_text(reply)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "I don't know that command. Just send me a normal message or use /help."
        )


# ----------------- main entrypoint -----------------


def main():
    # 1) Init your agents
    init_agents()

    # 2) Read Telegram token
    token = os.getenv("TELEGRAM_API")
    if not token:
        raise RuntimeError("Please set TELEGRAM_BOT_TOKEN environment variable.")

    # 3) Build Telegram application
    application = ApplicationBuilder().token(token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))

    # Text messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # 4) Start polling
    application.run_polling()


if __name__ == "__main__":
    main()
