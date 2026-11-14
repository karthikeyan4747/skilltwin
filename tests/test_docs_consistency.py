"""Every file path the docs or the feature registry mention must exist."""

import re
from pathlib import Path

import pytest

from backend.registry import FEATURES

ROOT = Path(__file__).resolve().parent.parent
DOCS = ["README.md", "SECURITY.md", "docs/ARCHITECTURE.md"]
PATH_PATTERN = re.compile(r"`((?:backend|frontend|tests|docs|\.github)/[^`*\s]+)`")


@pytest.mark.parametrize("doc", DOCS)
def test_paths_referenced_in_docs_exist(doc: str) -> None:
    referenced = PATH_PATTERN.findall((ROOT / doc).read_text(encoding="utf-8"))
    assert referenced, f"{doc} references no files"
    missing = [p for p in referenced if not (ROOT / p.rstrip("/")).exists()]
    assert not missing, f"{doc} references missing paths: {missing}"


def test_registry_paths_exist() -> None:
    paths = [p for f in FEATURES for p in (*f.modules, *f.tests)]
    missing = [p for p in paths if not (ROOT / p).exists()]
    assert not missing, missing


def test_readme_alignment_table_covers_every_required_feature() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for feature in (f for f in FEATURES if f.required):
        assert feature.title in readme and feature.ui_route in readme
