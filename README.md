# LangFord
**Language (Model) For Organizational Reasoning & Delegation**  
A Telegram-first AI assistant that can *actually do things*: read and summarize news, draft replies, create calendar entries, pull information from your email, and more — by choosing the right tools on its own.

---

## What it is
LangFord is a lightweight agent runtime that lives in Telegram. You chat with it like a normal assistant, but under the hood it can call real integrations (Calendar, email, web) to complete requests end-to-end.

Think: “Hey, remind me tomorrow 9:00 to call Alex and add it to my calendar” → it schedules it.  
Or: “Summarize today’s headlines about AI regulation and send me the 5 key points” → it fetches, filters, and summarizes.

---

## Highlights
- **Telegram-native UX**: no extra UI, no dashboards — just messages.
- **Tool selection done by the model**: you don’t need to remember commands like `/calendar_add`.
- **Practical workflows**:
  - create calendar events
  - email reading / extracting action items
  - web/news digest
  - quick research with sources (when enabled)
  - “do this for me” style delegation with guardrails
- **Composable tools**: adding a new capability is “just another tool”, not a rewrite.
- **Provider-flexible**: designed around an LLM client + an agent loop (works with common OpenAI-compatible endpoints).

---

## Example chats
**Calendar**
- “Schedule ‘Project sync’ next Tuesday 14:30 for 45 minutes.”
- “Move my dentist appointment to Friday afternoon.”
- “What do I have tomorrow morning?”

**Email**
- “Check my inbox for anything urgent from HR and summarize it.”
- “Find the last email about ‘invoice 2026-02’ and tell me what’s needed.”
- “Draft a reply: confirm receipt and ask for the missing attachment.”

**News**
- “Give me a morning briefing: AI, geopolitics, finance — short.”
- “Summarize the latest on [topic] in 5 bullets and link sources.”

**General assistant**
- “Turn this message into a polite reply.”
- “Extract tasks from this text and create reminders.”

---

## How it works (in one minute)
LangFord runs an agent loop:
1. **You send a message** in Telegram.
2. The **agent decides** whether it can answer directly or needs a tool.
3. If needed, it **calls tools** (calendar/email/web) with structured inputs.
4. Results are **stitched into a final response**, with the action completed.

The goal is to keep the interface simple (chat), while making the backend capable (tools).

---

## Project layout (high level)
> Folder names may evolve, but the structure is intentionally simple.

- `interface/` – Telegram bot entrypoint + message handling  
- `agents/` – agent orchestration / routing logic  
- `tools/` – integrations (calendar, email, web scraping, etc.)  
- `prompts/` – system prompts + tool instructions  
- `core/` – shared utilities (config, clients, helpers)

---

## Quickstart
### 1) Install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
````

### 2) Configure environment

Create a `.env` file (or export env vars). Typical values:

* `TELEGRAM_BOT_TOKEN` – your bot token from BotFather
* `OPENAI_API_KEY` (or your OpenAI-compatible key)
* Optional: credentials for Google / Microsoft integrations (depending on which tools you enable)

> If you don’t configure calendar/email, LangFord still works as a chat assistant — it just won’t execute those actions.

### 3) Run

```bash
python -m interface.telegram_bot
```

---

## Tools & integrations

LangFord is built to support multiple tool backends. Out of the box (or by default templates), you’ll typically see:

* **Web/news** via HTML extraction + article parsing
* **Google integrations** (Calendar / Gmail) via OAuth + Google APIs
* **Microsoft integrations** (Graph) via MSAL (optional, if enabled)

If you don’t want an integration, disable the tool — the agent will stop using it.

---

## Adding a new tool

1. Create a new tool module in `tools/` (keep it small and single-purpose).
2. Define:

   * what the tool does
   * the inputs it expects
   * the output shape (keep it predictable)
3. Register it with the agent/router so the model can discover it.
4. Add a short usage note in `prompts/` so the model knows when to call it.

A good tool is boring: deterministic inputs, deterministic outputs, clear failure modes.

---

## Safety & guardrails

This project is meant to be useful, not reckless.
Recommended defaults:

* **confirmation before destructive actions** (delete/move/cancel)
* **explicit scopes** for email/calendar access
* **logging** of tool calls (so you can audit what happened)
* **rate limits** to avoid runaway loops

---

## Roadmap ideas

* Daily scheduled briefing (news + calendar overview)
* “Inbox to tasks” mode (extract tasks → calendar/reminders)
* Personal knowledge base (lightweight memory with opt-in)
* More tool adapters (Notion, Slack, Jira, GitHub, etc.)

---


