"""Server replay agrees with the shared Grid Game cases the frontend tests also use."""

import json
from pathlib import Path

import pytest

from backend.core.grid import replay

CASES = json.loads((Path(__file__).parent / "fixtures" / "grid_cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['level']}-{len(c['moves'])}")
def test_shared_grid_cases(catalog, case) -> None:
    assert replay(catalog.grid_levels[case["level"]], case["moves"]) is case["solved"]
