"""Cost model: measured wall-clock seconds x an hourly VM list price (amortised, one request at a time).

All three tiers ran on the same 8-vCPU CPU box. We price that box as an Azure Standard_D8s_v5 Linux VM
in eastus2 at its pay-as-you-go list price, read from the Azure Retail Prices API on 2026-11-09.
This assumes the VM is fully used by the router (utilisation 1.0); idle time makes real cost higher,
so `utilisation` is a parameter.
"""

from __future__ import annotations

from dataclasses import dataclass

VM_SKU = "Standard_D8s_v5"
VM_REGION = "eastus2"
VM_USD_PER_HOUR = 0.384
PRICE_AS_OF = "2026-11-09"


@dataclass(frozen=True)
class CostModel:
    usd_per_hour: float = VM_USD_PER_HOUR
    utilisation: float = 1.0

    def __post_init__(self):
        if self.usd_per_hour <= 0:
            raise ValueError("price must be positive")
        if not 0 < self.utilisation <= 1:
            raise ValueError("utilisation must be in (0, 1]")

    def usd(self, seconds: float) -> float:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        return seconds * self.usd_per_hour / 3600 / self.utilisation

    def usd_per_1k(self, seconds: float) -> float:
        return 1000 * self.usd(seconds)
