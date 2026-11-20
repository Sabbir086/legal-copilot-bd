"""Centralized OpenRouter chat-model configuration."""

from langchain_openai import ChatOpenAI

from app.config.settings import settings


def get_chat_model(*, max_retries: int = 2, timeout: float = 90) -> ChatOpenAI:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured on the backend.")

    headers = {"X-Title": "MyLegal AI"}
    if settings.openrouter_site_url:
        headers["HTTP-Referer"] = settings.openrouter_site_url

    return ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        default_headers=headers,
        max_retries=max_retries,
        timeout=timeout,
    )
