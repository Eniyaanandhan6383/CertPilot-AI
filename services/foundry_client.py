"""
CertPilot AI — Azure AI Foundry Client
Wraps the Azure OpenAI SDK for all agent LLM calls.
Set env vars before running:
    AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
    AZURE_OPENAI_API_KEY=<your-key>
    AZURE_OPENAI_DEPLOYMENT=gpt-4o
"""
import os
import json
from openai import AzureOpenAI

_client: AzureOpenAI | None = None


def get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version="2024-02-01",
        )
    return _client


def call_agent(
    system_prompt: str,
    user_message: str,
    deployment: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    response_format: str = "json_object",  # "json_object" | "text"
) -> dict | str:
    """
    Single agent LLM call.
    Returns parsed dict if response_format="json_object", else raw string.
    """
    client = get_client()
    dep = deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]

    kwargs = dict(
        model=dep,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if response_format == "json_object":
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content

    if response_format == "json_object":
        return json.loads(content)
    return content


def call_agent_with_history(
    system_prompt: str,
    conversation: list[dict],
    deployment: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """Multi-turn conversation call. conversation = [{"role": ..., "content": ...}]"""
    client = get_client()
    dep = deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    messages = [{"role": "system", "content": system_prompt}] + conversation

    response = client.chat.completions.create(
        model=dep,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
