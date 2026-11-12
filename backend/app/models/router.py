"""Builds the configured model providers and their prices."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import Settings
from app.models.auth import AzureTokenProvider
from app.models.base import ModelProvider
from app.models.messages_adapter import MessagesAdapter
from app.models.pricing import Price
from app.models.responses_adapter import ResponsesAdapter


@dataclass
class ModelRouter:
    providers: dict[str, ModelProvider] = field(default_factory=dict)
    prices: dict[str, Price] = field(default_factory=dict)

    def get(self, key: str) -> ModelProvider:
        return self.providers[key]

    def has(self, key: str) -> bool:
        return key in self.providers

    def display_name(self, key: str) -> str:
        p = self.providers.get(key)
        return p.display_name if p else key

    async def aclose(self) -> None:
        for p in self.providers.values():
            close = getattr(p, "aclose", None)
            if close:
                await close()


def build_router(settings: Settings, token_provider: AzureTokenProvider | None = None) -> ModelRouter:
    router = ModelRouter()
    tp = token_provider
    if settings.foundry_openai_base_url:
        key = settings.foundry_openai_api_key.get_secret_value() if settings.foundry_openai_api_key else None
        if not key and tp is None:
            tp = AzureTokenProvider(settings.foundry_token_scope)
        router.providers["workhorse"] = ResponsesAdapter(
            key="workhorse", display_name=settings.workhorse_display_name,
            base_url=settings.foundry_openai_base_url, deployment=settings.workhorse_deployment,
            token_fn=None if key else tp, api_key=key,
        )
        router.prices["workhorse"] = Price(settings.workhorse_price_input_per_mtok,
                                           settings.workhorse_price_output_per_mtok)
    if settings.foundry_anthropic_base_url:
        key = settings.foundry_anthropic_api_key.get_secret_value() if settings.foundry_anthropic_api_key else None
        if not key and tp is None:
            tp = AzureTokenProvider(settings.foundry_token_scope)
        router.providers["escalation"] = MessagesAdapter(
            key="escalation", display_name=settings.escalation_display_name,
            base_url=settings.foundry_anthropic_base_url, deployment=settings.escalation_deployment,
            token_fn=None if key else tp, api_key=key,
        )
        router.prices["escalation"] = Price(settings.escalation_price_input_per_mtok,
                                            settings.escalation_price_output_per_mtok)
    return router
