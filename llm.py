from __future__ import annotations

import os

import httpx
from openai import OpenAI
from transformers import AutoTokenizer
from smolagents import OpenAIModel


class llm_object:
    """Simple wrapper for an OpenAI-compatible chat endpoint."""

    def __init__(self) -> None:
        self.history = []

        # Choose provider via env var: "custom" (default) or "groq"
        provider = os.getenv("LLM_PROVIDER", "custom").lower()

        # Shared tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3", use_fast=True
        )

        if provider == "groq":
            base_url = "https://api.groq.com/openai/v1/"
            api_key = os.getenv("GROQ_API_KEY", "x")
            model_name = os.getenv("GROQ_MODEL_ID", "llama-3.1-70b-versatile")
            verify = True
        else:
            base_url = os.getenv(
                "CUSTOM_LLM_BASE_URL",
                "https://fastchat-api.k8s.sg.iaea.org/v1/",
            )
            api_key = os.getenv("CUSTOM_LLM_API_KEY", "x")
            model_name = os.getenv(
                "CUSTOM_LLM_MODEL_ID",
                "Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
            )
            verify = False  # self-signed cert on your FastChat

        # Store on self *before* using them anywhere else
        self.base_url = base_url
        self.model_name = model_name

        httpx_client = httpx.Client(
            http2=True,
            verify=verify,
            timeout=httpx.Timeout(timeout=360.0, connect=5.0),
        )

        # Low-level OpenAI-compatible client
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=api_key,
            http_client=httpx_client,
        )

        # High-level smolagents model (this is what you pass to ToolCallingAgent)
        self.model = OpenAIModel(
            model_id=self.model_name,
            api_base=self.base_url,
            api_key=api_key,
            flatten_messages_as_text=True,
            temperature=0.2,
            max_tokens=2048,
        )
        # Reuse same HTTP client
        self.model.client = self.client

    def purge(self) -> None:
        self.history.clear()

    def set_system(self, content: str, purge_existing: bool = False) -> None:
        if purge_existing:
            self.purge()
        self.remember("system", content)

    def remember(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def completion(
        self,
        prompt: str,
        temperature: float = 0.2,
        top_p: float = 0.8,
        seed: int = 123,
    ) -> str:
        """Return a single chat completion for the given prompt."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                top_p=top_p,
                seed=seed,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"Empty content in response: {e}")

    def render_history(self, add_generation_prompt: bool = True) -> str:
        return self.tokenizer.apply_chat_template(
            self.history,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
        )
