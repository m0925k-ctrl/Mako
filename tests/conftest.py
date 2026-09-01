"""テストの副作用(得意先メモの書き込み)を元に戻すフィクスチャ。"""
import shutil
from pathlib import Path

import pytest

CUSTOMERS = Path(__file__).parent.parent / "app" / "data" / "customers.json"


@pytest.fixture(autouse=True)
def restore_customers():
    backup = CUSTOMERS.read_bytes()
    yield
    CUSTOMERS.write_bytes(backup)
    # メモリ上のストアも元に戻す
    from app.store import store
    store.reload()
