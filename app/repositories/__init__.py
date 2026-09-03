"""データソース別のリポジトリ実装。

``store`` はここで公開されるリポジトリ経由で外部データにアクセスする。
バックエンド(JSON モック / Oracle ODBC 等)は環境変数で切り替える。
"""
from __future__ import annotations

from .cases import CaseRepository, get_case_repository
from .configuration import ConfigurationRepository, get_configuration_repository
from .customers import CustomerRepository, get_customer_repository
from .engineers import EngineerRepository, get_engineer_repository
from .work_history import WorkHistoryRepository, get_work_history_repository

__all__ = [
    "CustomerRepository",
    "get_customer_repository",
    "CaseRepository",
    "get_case_repository",
    "EngineerRepository",
    "get_engineer_repository",
    "WorkHistoryRepository",
    "get_work_history_repository",
    "ConfigurationRepository",
    "get_configuration_repository",
]
