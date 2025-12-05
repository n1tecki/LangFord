from __future__ import annotations

import os

import httpx
from openai import OpenAI
from transformers import AutoTokenizer
from smolagents import OpenAIModel, LiteLLMModel


class llm_object:
    def __init__(self) -> None:
        self.history = []

        provider = os.getenv("LLM_PROVIDER", "groq").lower()

        # Shared tokenizer (unchanged)
        self.tokenizer = AutoTokenizer.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3", use_fast=True
        )

        if provider == "groq":
            base_url = "https://api.groq.com/openai/v1/"
            api_key = os.getenv("GROQ_API_KEY", "x")
            model_name = os.getenv("GROQ_MODEL_ID", "llama-3.1-70b-versatile")

            self.model_name = model_name

            self.model = LiteLLMModel(
                model_id=f"groq/{model_name}",
                api_key=api_key,
                temperature=0.2,
                max_tokens=2048,
                tool_choice="auto",
                flatten_messages_as_text=True,
            )

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

            httpx_client = httpx.Client(
                http2=True,
                verify=False,
                timeout=httpx.Timeout(timeout=360.0, connect=5.0),
            )

            self.base_url = base_url
            self.model_name = model_name

            self.client = OpenAI(
                base_url=self.base_url,
                api_key=api_key,
                http_client=httpx_client,
            )

            self.model = OpenAIModel(
                model_id=self.model_name,
                api_base=self.base_url,
                api_key=api_key,
                temperature=0.2,
                max_tokens=2048,
                flatten_messages_as_text=True,
            )
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
