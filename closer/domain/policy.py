from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict


@dataclass(frozen=True)
class Policy:
    item_limit: Dict[str, Decimal] = field(default_factory=dict)
    cycle_cap: Dict[str, Decimal] = field(default_factory=dict)
    fx_tolerance_pct: Decimal = Decimal("1.0")
    rounding_tolerance: Decimal = Decimal("0.50")

    def limit_for(self, currency: str) -> Decimal:
        return self.item_limit.get(currency, Decimal("0"))

    def cap_for(self, currency: str) -> Decimal:
        return self.cycle_cap.get(currency, Decimal("0"))
