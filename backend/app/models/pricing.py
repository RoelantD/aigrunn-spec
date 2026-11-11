"""Cost estimation from configured prices (FR-037). Prices are configuration, never hardcoded."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.base import Usage


@dataclass(frozen=True)
class Price:
    input_per_mtok: float = 0.0
    output_per_mtok: float = 0.0

    @property
    def configured(self) -> bool:
        return self.input_per_mtok > 0 or self.output_per_mtok > 0


def estimate_cost(usage: Usage, price: Price) -> float:
    # Reasoning tokens are billed as output tokens and are already included in output_tokens.
    return round(usage.input_tokens / 1e6 * price.input_per_mtok + usage.output_tokens / 1e6 * price.output_per_mtok, 6)
