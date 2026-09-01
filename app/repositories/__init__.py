"""データソース別のリポジトリ実装。

``store`` はここで公開されるリポジトリ経由で外部データにアクセスする。
バックエンド(JSON モック / Oracle ODBC 等)は環境変数で切り替える。
"""
from __future__ import annotations

from .cases import CaseRepository, get_case_repository
from .customers import CustomerRepository, get_customer_repository

__all__ = [
    "CustomerRepository",
    "get_customer_repository",
    "CaseRepository",
    "get_case_repository",
]
