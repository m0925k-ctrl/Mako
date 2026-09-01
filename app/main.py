"""FastAPI アプリ本体。API と静的フロントを提供する。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__, console
from app.aggregator import search as run_search
from app.models import (
    MailRenderRequest,
    MailRenderResponse,
    NoteCreate,
    SearchResponse,
    SourceInfo,
)
from app.sources import ALL_SOURCES
from app.store import store

app = FastAPI(
    title="Mako 集約検索コンソール",
    description="CSC(カスタマーソリューションセンター) 医療機器修理受付の業務効率化ツール",
    version=__version__,
)

STATIC_DIR = Path(__file__).parent.parent / "static"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/sources", response_model=list[SourceInfo])
def list_sources() -> list[SourceInfo]:
    return [
        SourceInfo(key=s.key, label=s.label, category=s.category, description=s.description)
        for s in ALL_SOURCES
    ]


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="検索キーワード(スペース区切りで AND)"),
    sources: str | None = Query(None, description="カンマ区切りのソースキー。未指定で全ソース"),
    limit: int = Query(50, ge=1, le=200),
) -> SearchResponse:
    source_keys = [s for s in sources.split(",") if s] if sources else None
    return run_search(q, source_keys=source_keys, limit=limit)


@app.get("/api/console/case/{case_id}")
def console_case(case_id: str) -> dict:
    data = console.build_console(case_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"ケースが見つかりません: {case_id}")
    return data


@app.get("/api/console/error/{code}")
def console_error(code: str) -> dict:
    consoles = console.build_console_by_error(code)
    if not consoles:
        raise HTTPException(status_code=404, detail=f"該当ケースがありません: {code}")
    return {"code": code, "count": len(consoles), "consoles": consoles}


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str) -> dict:
    c = store.get_customer(customer_id)
    if c is None:
        raise HTTPException(status_code=404, detail=f"得意先が見つかりません: {customer_id}")
    return c


@app.post("/api/customers/{customer_id}/notes")
def add_customer_note(customer_id: str, payload: NoteCreate) -> dict:
    try:
        note = store.add_customer_note(customer_id, payload.text, payload.author)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"得意先が見つかりません: {customer_id}")
    return note


@app.post("/api/console/case/{case_id}/mail", response_model=MailRenderResponse)
def render_mail(case_id: str, payload: MailRenderRequest) -> MailRenderResponse:
    try:
        rendered = console.render_mail(case_id, payload.template, payload.parts)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"不明なテンプレート: {payload.template}")
    if rendered is None:
        raise HTTPException(status_code=404, detail=f"ケースが見つかりません: {case_id}")
    return MailRenderResponse(**rendered)


# --- 静的フロント ---------------------------------------------------------
@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
