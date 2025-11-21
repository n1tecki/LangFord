from __future__ import annotations

import httpx
from openai import OpenAI
from transformers import AutoTokenizer
from smolagents import OpenAIModel


class llm_object:
    """Simple wrapper for an OpenAI-compatible chat endpoint."""

    base_url: str
    model: str
    client: OpenAI

    def __init__(self) -> None:
        """Set up the HTTP client and OpenAI client."""

        self.history = []

        self.base_url = "https://fastchat-api.k8s.sg.iaea.org/v1/"
        self.model = "Meta-Llama-3.1-70B-Instruct-AWQ-INT4"
        self.tokenizer = AutoTokenizer.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3", use_fast=True
        )

        httpx_client = httpx.Client(
            http2=True,
            verify=False,
            timeout=httpx.Timeout(timeout=360.0, connect=5.0),
        )

        self.client = OpenAI(
            base_url=self.base_url,
            api_key="x",
            http_client=httpx_client,
        )

        self.model = OpenAIModel(
            model_id="Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
            api_base="https://fastchat-api.k8s.sg.iaea.org/v1/",
            api_key="x",
            flatten_messages_as_text=True,
            temperature=0.2,
            max_tokens=2048,
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
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                top_p=top_p,
                seed=seed,
            )
            return response.choices[0].message.content
        except:
            raise RuntimeError("Empty content in response.")

    def render_history(self, add_generation_prompt: bool = True) -> str:
        # Use the tokenizer's built-in chat template to render the memory
        return self.tokenizer.apply_chat_template(
            self.history,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
        )
