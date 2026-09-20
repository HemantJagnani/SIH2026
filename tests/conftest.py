"""Shared pytest fixtures for the APIx test suite."""
from __future__ import annotations

from pathlib import Path

import pytest

from apix.db import get_connection, init_db


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Return a fresh in-memory-like SQLite DB path for each test."""
    path = tmp_path / "apix_test.db"
    init_db(path)
    return path


@pytest.fixture()
def db_con(db_path: Path):
    """Yield an open connection to the test DB (auto-committed)."""
    with get_connection(db_path) as con:
        yield con
