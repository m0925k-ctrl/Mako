"""メール送信(SMTP)。

既定では **送信せず下書きのみ**（安全側）。環境変数で有効化した場合のみ実送信する。
本番の実運用では、送信の確定操作を人が行う運用（下書き→確認→送信）を推奨。

環境変数:
  MAKO_SMTP_ENABLED = 1 で送信有効(未設定/0 は下書きのみ)
  MAKO_SMTP_HOST, MAKO_SMTP_PORT(既定 587)
  MAKO_SMTP_USER, MAKO_SMTP_PASSWORD
  MAKO_SMTP_FROM (送信元。未設定なら USER)
  MAKO_SMTP_TLS = 1 で STARTTLS(既定 1)
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def smtp_enabled() -> bool:
    return os.getenv("MAKO_SMTP_ENABLED", "0") == "1"


def send_mail(to: str, subject: str, body: str, cc: str | None = None) -> dict:
    """メールを送る。SMTP 無効時は下書き扱いで返す。"""
    if not smtp_enabled():
        return {"sent": False, "reason": "SMTP未設定のため下書きのみ（送信は未実行）", "to": to}
    if not to:
        return {"sent": False, "reason": "宛先が未解決（CEのメールアドレスが特定できません）", "to": to}

    host = os.getenv("MAKO_SMTP_HOST")
    if not host:
        return {"sent": False, "reason": "MAKO_SMTP_HOST 未設定", "to": to}
    port = int(os.getenv("MAKO_SMTP_PORT", "587"))
    user = os.getenv("MAKO_SMTP_USER", "")
    pwd = os.getenv("MAKO_SMTP_PASSWORD", "")
    sender = os.getenv("MAKO_SMTP_FROM") or user
    use_tls = os.getenv("MAKO_SMTP_TLS", "1") == "1"

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls()
        if user:
            server.login(user, pwd)
        server.send_message(msg)

    return {"sent": True, "reason": "送信しました", "to": to}
