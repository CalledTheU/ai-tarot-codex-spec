# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

from typing import Protocol


class ModelAdapter(Protocol):
    """Provider-independent boundary; concrete model calls begin in Phase 4."""

    async def generate(self, prompt: str) -> str: ...
