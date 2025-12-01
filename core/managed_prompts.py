from pathlib import Path
from dataclasses import dataclass
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR.parent / "prompts"
now_iso = datetime.now(ZoneInfo("Europe/Vienna")).isoformat(timespec="seconds")


@dataclass
class AgentPromptBundle:
    description: str
    system: str


def load_agent_prompts(agent_name: str) -> AgentPromptBundle:
    path = PROMPTS_DIR / f"{agent_name}.yaml"

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    description = data["description"]
    system = data["system_prompt"].replace("{{NOW_ISO}}", now_iso)

    return AgentPromptBundle(
        description=description, 
        system=system
    )
