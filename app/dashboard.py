"""Mako 現場作業ダッシュボード（試作）

現場から集めた作業報告と、顧客からの頼まれごと・残務を
PC上で一覧・検索できるビューア。

起動:
    streamlit run app/dashboard.py
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import data as d
from photos import placeholder_png

st.set_page_config(page_title="Mako 現場作業ダッシュボード", page_icon="🛠️", layout="wide")

reports = d.load_reports()
tasks = d.load_tasks()
all_customers = d.customers(reports, tasks)


# ----------------------------------------------------------------------------
# サイドバー
# ----------------------------------------------------------------------------
st.sidebar.title("🛠️ Mako")
st.sidebar.caption("現場作業ダッシュボード（試作）")
view = st.sidebar.radio(
    "表示",
    ["📊 サマリー", "📋 作業報告", "🗂️ 残務ボード", "🏢 顧客別"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption(
    "データは `app/sample_data/` のダミーです。\n"
    "実運用では Forms → SharePoint の回答に差し替えます。"
)


def status_badge(status: str) -> str:
    color = d.STATUS_COLORS.get(status, "#888")
    return (
        f"<span style='background:{color};color:#fff;padding:2px 10px;"
        f"border-radius:12px;font-size:0.8em;white-space:nowrap'>{status}</span>"
    )


def priority_mark(p: str) -> str:
    return {"高": "🔴 高", "中": "🟡 中", "低": "⚪ 低"}.get(p, p)


def render_report_card(row: pd.Series) -> None:
    when = row["submitted_at"].strftime("%Y-%m-%d %H:%M")
    with st.expander(f"**{row['customer']}** ／ {row['equipment']}　— {when}　({row['id']})"):
        top = st.columns(3)
        top[0].markdown(f"**現場**\n\n{row['site']}")
        top[1].markdown(f"**担当者**\n\n{row['engineer']}")
        top[2].markdown(f"**受付日時**\n\n{when}")

        st.markdown("---")
        for key, label in d.REPORT_FIELDS:
            if key in ("customer", "site", "engineer", "equipment"):
                continue
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


# ----------------------------------------------------------------------------
# 📊 サマリー
# ----------------------------------------------------------------------------
if view == "📊 サマリー":
    st.title("📊 サマリー")

    open_tasks = tasks[tasks["status"] != "完了"]
    now = pd.Timestamp(datetime.now().date())
    overdue = open_tasks[open_tasks["due"] < now]

    m = st.columns(4)
    m[0].metric("作業報告 (累計)", len(reports))
    m[1].metric("未完了の残務", len(open_tasks))
    m[2].metric("期限超過", len(overdue), delta=None)
    m[3].metric("顧客数", len(all_customers))

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
                f"**{t['customer']}**{overdue_mark}",
                unsafe_allow_html=True,
            )
            st.markdown(f"{t['content']}")
            st.caption(f"期限 {t['due'].strftime('%m/%d')}　担当 {t['assignee']}　({t['id']})")
            st.markdown("")


# ----------------------------------------------------------------------------
# 📋 作業報告
# ----------------------------------------------------------------------------
elif view == "📋 作業報告":
    st.title("📋 作業報告")

    f = st.columns([2, 2, 3])
    cust = f[0].selectbox("顧客", ["すべて"] + all_customers)
    engineers = ["すべて"] + sorted(reports["engineer"].unique())
    eng = f[1].selectbox("担当者", engineers)
    kw = f[2].text_input("キーワード検索", placeholder="機器・不具合・部品名など")

    view_df = reports
    if cust != "すべて":
        view_df = view_df[view_df["customer"] == cust]
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

    cust = st.selectbox("顧客で絞り込み", ["すべて"] + all_customers)
    board = tasks if cust == "すべて" else tasks[tasks["customer"] == cust]

    now = pd.Timestamp(datetime.now().date())
    cols = st.columns(len(d.TASK_STATUSES))
    for col, status in zip(cols, d.TASK_STATUSES):
        subset = board[board["status"] == status]
        col.markdown(f"### {status}　({len(subset)})")
        for _, t in subset.iterrows():
            overdue = t["due"] < now and status != "完了"
            border = "#e5484d" if overdue else "#d0d0d0"
            with col.container(border=True):
                st.markdown(
                    f"{priority_mark(t['priority'])}　**{t['customer']}**",
                )
                st.write(t["content"])
                due_txt = t["due"].strftime("%Y-%m-%d")
                if overdue:
                    st.markdown(f":red[⏰ 期限 {due_txt}（超過）]")
                else:
                    st.caption(f"期限 {due_txt}")
                st.caption(f"担当 {t['assignee']}　関連 {t['related_report']}　({t['id']})")
                if t["note"]:
                    st.caption(f"📝 {t['note']}")


# ----------------------------------------------------------------------------
# 🏢 顧客別
# ----------------------------------------------------------------------------
elif view == "🏢 顧客別":
    st.title("🏢 顧客別ビュー")

    cust = st.selectbox("顧客", all_customers)
    c_reports = reports[reports["customer"] == cust]
    c_tasks = tasks[tasks["customer"] == cust]
    open_c = c_tasks[c_tasks["status"] != "完了"]

    m = st.columns(3)
    m[0].metric("作業報告", len(c_reports))
    m[1].metric("未完了の残務", len(open_c))
    m[2].metric("完了した残務", len(c_tasks) - len(open_c))

    st.divider()
    tab1, tab2 = st.tabs(["作業履歴", "残務・頼まれごと"])

    with tab1:
        if c_reports.empty:
            st.info("作業報告はありません。")
        for _, row in c_reports.iterrows():
            render_report_card(row)

    with tab2:
        if c_tasks.empty:
            st.info("残務はありません。")
        for _, t in c_tasks.iterrows():
            st.markdown(
                f"{status_badge(t['status'])}　{priority_mark(t['priority'])}　"
                f"期限 {t['due'].strftime('%Y-%m-%d')}",
                unsafe_allow_html=True,
            )
            st.markdown(f"**{t['content']}**")
            st.caption(f"担当 {t['assignee']}　関連 {t['related_report']}　({t['id']})")
            if t["note"]:
                st.caption(f"📝 {t['note']}")
            st.divider()
