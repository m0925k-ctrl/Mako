"""Mako 装置カルテ・ダッシュボード（試作）

病院にある装置1台ごとの「カルテ」= 作業履歴・申し送り・残務を
PC上で時系列に閲覧できるビューア。地図・作業員の顔写真つき。

起動:
    streamlit run app/dashboard.py
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import data as d
from photos import placeholder_png, avatar_png

st.set_page_config(page_title="Mako 装置カルテ", page_icon="🩺", layout="wide")

hospitals = d.load_hospitals()
devices = d.load_devices()
engineers = d.load_engineers()
reports = d.load_reports()
tasks = d.load_tasks()


# ----------------------------------------------------------------------------
# 共通パーツ
# ----------------------------------------------------------------------------
def status_badge(status: str) -> str:
    color = d.STATUS_COLORS.get(status, "#888")
    return (
        f"<span style='background:{color};color:#fff;padding:2px 10px;"
        f"border-radius:12px;font-size:0.8em;white-space:nowrap'>{status}</span>"
    )


def priority_mark(p: str) -> str:
    return {"高": "🔴 高", "中": "🟡 中", "低": "⚪ 低"}.get(p, p)


def engineer_avatar(row: pd.Series):
    name = row.get("engineer") or "?"
    return avatar_png(str(row.get("engineer_photo") or name), initial=str(name)[:1])


def report_body(row: pd.Series) -> None:
    """報告の本文（対応区分〜申し送り＋写真）を描画。"""
    for key, label in d.REPORT_FIELDS:
        val = row.get(key, "")
        if val:
            st.markdown(f"**{label}**")
            st.write(val)
    photos = row.get("photos") or []
    if photos:
        st.markdown("**写真**")
        cols = st.columns(min(len(photos), 4))
        for i, name in enumerate(photos):
            cols[i % len(cols)].image(placeholder_png(name), caption=name)


def render_report_card(row: pd.Series, show_device: bool = True) -> None:
    when = row["submitted_at"].strftime("%Y-%m-%d %H:%M")
    head = f"{row['hospital']} ／ {row['device_name']}" if show_device else row["visit_type"]
    with st.expander(f"**{head}**　［{row['visit_type']}］　— {when}　({row['id']})"):
        c = st.columns([1, 5])
        c[0].image(engineer_avatar(row), width=64)
        c[1].markdown(
            f"**担当** {row['engineer']}　\n"
            f"**装置** {row['device_name']}（{row['device_model']} / SN:{row['device_serial']}）　\n"
            f"**設置場所** {row['device_location']}　\n"
            f"**受付** {when}"
        )
        st.markdown("---")
        report_body(row)


# ----------------------------------------------------------------------------
# サイドバー
# ----------------------------------------------------------------------------
st.sidebar.title("🩺 Mako")
st.sidebar.caption("装置カルテ・ダッシュボード（試作）")
view = st.sidebar.radio(
    "表示",
    ["📊 サマリー", "🏥 装置カルテ", "📋 作業報告", "🗂️ 残務ボード"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption(
    "データは `app/sample_data/` のダミーです。\n"
    "実運用では Forms → SharePoint の回答に差し替えます。"
)


# ----------------------------------------------------------------------------
# 📊 サマリー
# ----------------------------------------------------------------------------
if view == "📊 サマリー":
    st.title("📊 サマリー")

    open_tasks = tasks[tasks["status"] != "完了"]
    now = pd.Timestamp(datetime.now().date())
    overdue = open_tasks[open_tasks["due"] < now]
    pm_soon = devices[devices["next_pm"] <= now + pd.Timedelta(days=30)]

    m = st.columns(5)
    m[0].metric("病院数", len(hospitals))
    m[1].metric("管理装置数", len(devices))
    m[2].metric("作業報告 (累計)", len(reports))
    m[3].metric("未完了の残務", len(open_tasks))
    m[4].metric("点検30日以内", len(pm_soon))

    st.divider()
    left, right = st.columns([3, 2])

    with left:
        st.subheader("最近の作業報告")
        for _, row in reports.head(5).iterrows():
            render_report_card(row)

    with right:
        st.subheader("要対応の残務")
        if open_tasks.empty:
            st.success("未完了の残務はありません。")
        for _, t in open_tasks.iterrows():
            overdue_mark = "　⏰ **期限超過**" if t["due"] < now else ""
            st.markdown(
                f"{status_badge(t['status'])}　{priority_mark(t['priority'])}　"
                f"**{t['hospital']}**{overdue_mark}",
                unsafe_allow_html=True,
            )
            st.markdown(f"{t['device_name']}：{t['content']}")
            st.caption(f"期限 {t['due'].strftime('%m/%d')}　担当 {t['assignee']}　({t['id']})")
            st.markdown("")

        st.subheader("点検が近い装置")
        for _, dev in pm_soon.sort_values("next_pm").iterrows():
            st.markdown(f"**{dev['hospital']}** ／ {dev['name']}")
            st.caption(f"次回点検 {dev['next_pm'].strftime('%Y-%m-%d')}　({dev['id']})")


# ----------------------------------------------------------------------------
# 🏥 装置カルテ
# ----------------------------------------------------------------------------
elif view == "🏥 装置カルテ":
    st.title("🏥 装置カルテ")

    top = st.columns([2, 3])
    hosp_name = top[0].selectbox("病院", sorted(hospitals["name"]))
    hosp = hospitals[hospitals["name"] == hosp_name].iloc[0]
    dev_choices = devices[devices["hospital"] == hosp_name]
    dev_label = top[1].selectbox(
        "装置",
        dev_choices["id"],
        format_func=lambda i: f"{dev_choices.set_index('id').loc[i, 'name']}"
        f"（{dev_choices.set_index('id').loc[i, 'model']}）",
    )
    dev = devices[devices["id"] == dev_label].iloc[0]

    # 病院情報＋地図
    info, mapcol = st.columns([3, 2])
    with info:
        st.subheader(f"{dev['name']}　のカルテ")
        st.markdown(
            f"**型番** {dev['model']}　\n"
            f"**製造番号(SN)** {dev['serial']}　\n"
            f"**設置場所** {hosp['name']} ／ {dev['location']}　\n"
            f"**設置日** {dev['installed_at'].strftime('%Y-%m-%d')}　\n"
            f"**次回点検** {dev['next_pm'].strftime('%Y-%m-%d')}"
        )
        st.markdown(
            f"📍 {hosp['address']}　"
            f"[🗺️ Googleマップで開く]({d.maps_link(hosp['lat'], hosp['lng'])})"
        )
        st.caption(f"連絡先: {hosp['contact']}")
    with mapcol:
        _embed = d.maps_embed(hosp["lat"], hosp["lng"])
        if hasattr(st, "iframe"):
            st.iframe(_embed, height=220)
        else:  # 古い Streamlit 向けフォールバック
            import streamlit.components.v1 as components

            components.iframe(_embed, height=220)

    st.divider()

    dev_reports = reports[reports["device_id"] == dev["id"]]
    dev_tasks = tasks[tasks["device_id"] == dev["id"]]
    open_dev_tasks = dev_tasks[dev_tasks["status"] != "完了"]

    # この装置の残務
    if not open_dev_tasks.empty:
        st.subheader("🗂️ この装置の未完了の残務")
        for _, t in open_dev_tasks.iterrows():
            st.markdown(
                f"{status_badge(t['status'])}　{priority_mark(t['priority'])}　"
                f"期限 {t['due'].strftime('%Y-%m-%d')}　**{t['content']}**",
                unsafe_allow_html=True,
            )
            st.caption(f"担当 {t['assignee']}　関連 {t['related_report']}　({t['id']})")
        st.divider()

    # 作業履歴（時系列＝カルテ本体）
    st.subheader(f"🗓️ 作業履歴（{len(dev_reports)} 件）")
    if dev_reports.empty:
        st.info("この装置の作業履歴はまだありません。")
    for _, row in dev_reports.iterrows():
        when = row["submitted_at"].strftime("%Y-%m-%d")
        c = st.columns([1, 10])
        c[0].image(engineer_avatar(row), width=52)
        with c[1]:
            st.markdown(
                f"**{when}**　［{row['visit_type']}］　担当 {row['engineer']}　({row['id']})"
            )
            with st.expander("詳細を見る"):
                report_body(row)
        st.markdown("")


# ----------------------------------------------------------------------------
# 📋 作業報告
# ----------------------------------------------------------------------------
elif view == "📋 作業報告":
    st.title("📋 作業報告")

    f = st.columns([2, 2, 3])
    hosp = f[0].selectbox("病院", ["すべて"] + sorted(hospitals["name"]))
    eng = f[1].selectbox("担当者", ["すべて"] + sorted(reports["engineer"].dropna().unique()))
    kw = f[2].text_input("キーワード検索", placeholder="装置・不具合・部品名など")

    view_df = reports
    if hosp != "すべて":
        view_df = view_df[view_df["hospital"] == hosp]
    if eng != "すべて":
        view_df = view_df[view_df["engineer"] == eng]
    if kw:
        mask = view_df.apply(
            lambda r: kw.lower() in " ".join(str(v) for v in r.values).lower(), axis=1
        )
        view_df = view_df[mask]

    st.caption(f"{len(view_df)} 件")
    for _, row in view_df.iterrows():
        render_report_card(row)


# ----------------------------------------------------------------------------
# 🗂️ 残務ボード
# ----------------------------------------------------------------------------
elif view == "🗂️ 残務ボード":
    st.title("🗂️ 残務ボード（頼まれごと）")

    hosp = st.selectbox("病院で絞り込み", ["すべて"] + sorted(hospitals["name"]))
    board = tasks if hosp == "すべて" else tasks[tasks["hospital"] == hosp]

    now = pd.Timestamp(datetime.now().date())
    cols = st.columns(len(d.TASK_STATUSES))
    for col, status in zip(cols, d.TASK_STATUSES):
        subset = board[board["status"] == status]
        col.markdown(f"### {status}　({len(subset)})")
        for _, t in subset.iterrows():
            overdue = t["due"] < now and status != "完了"
            with col.container(border=True):
                st.markdown(f"{priority_mark(t['priority'])}　**{t['hospital']}**")
                st.caption(f"装置: {t['device_name']}")
                st.write(t["content"])
                due_txt = t["due"].strftime("%Y-%m-%d")
                if overdue:
                    st.markdown(f":red[⏰ 期限 {due_txt}（超過）]")
                else:
                    st.caption(f"期限 {due_txt}")
                st.caption(f"担当 {t['assignee']}　関連 {t['related_report']}　({t['id']})")
                if t["note"]:
                    st.caption(f"📝 {t['note']}")
