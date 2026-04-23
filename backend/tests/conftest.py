from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: kaller eksterne API-er (Claude, Stortinget) — krever nettverkstilgang og ANTHROPIC_API_KEY",
    )
