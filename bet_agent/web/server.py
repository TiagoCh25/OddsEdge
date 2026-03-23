"""FastAPI server exposing web UI and JSON endpoint for recommended bets."""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.football_api import FootballAPI
from api.odds_api import OddsAPI
from app.bootstrap_acesso import inicializar_base_acesso
from app.config import settings
from db.repositorio_historico import RepositorioHistoricoSQLite
from services.dashboard_service import DashboardService
from web.admin_routes import router as admin_router
from web.auth_routes import router as auth_router
from web.dependencies import (
    exigir_usuario_logado,
    obter_usuario_logado_opcional,
    redirecionar_para_login,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    inicializar_base_acesso()
    yield


app = FastAPI(title="Bet Agent", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(admin_router)


def _build_ui_version() -> str:
    """Builds a UI version tag from runtime date and optional build id."""
    timestamp = datetime.now().strftime("%Y.%m.%d.%H%M")
    build_id = os.getenv("BET_AGENT_BUILD_ID", "").strip()
    if build_id:
        return f"{timestamp}+{build_id}"
    return timestamp


UI_VERSION = _build_ui_version()
_API_HEALTH_CACHE: Dict[str, Any] = {"checked_at": 0.0, "value": None}
_API_HEALTH_LOCK = threading.Lock()

base_dir = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(base_dir / "web" / "templates"))
app.mount("/static", StaticFiles(directory=str(base_dir / "web" / "static")), name="static")


@app.middleware("http")
async def disable_static_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


class SessionManager:
    """Tracks active browser tabs and requests server shutdown when all tabs close."""

    def __init__(self, idle_shutdown_seconds: int, enabled: bool = True) -> None:
        self.idle_shutdown_seconds = max(idle_shutdown_seconds, 5)
        self.enabled = enabled
        self._sessions: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._had_session = False
        self._server: Optional[uvicorn.Server] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def attach_server(self, server: uvicorn.Server) -> None:
        self._server = server

    def start_watchdog(self) -> None:
        if not self.enabled:
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._thread.start()

    def stop_watchdog(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def start_session(self) -> str:
        session_id = uuid4().hex
        now = time.time()
        with self._lock:
            self._sessions[session_id] = now
            self._had_session = True
        return session_id

    def heartbeat(self, session_id: str) -> bool:
        if not session_id:
            return False
        with self._lock:
            if session_id not in self._sessions:
                return False
            self._sessions[session_id] = time.time()
        return True

    def end_session(self, session_id: str) -> None:
        if not self.enabled:
            return
        if not session_id:
            return
        with self._lock:
            self._sessions.pop(session_id, None)
            should_shutdown = self._had_session and not self._sessions
        if should_shutdown:
            self._request_shutdown()

    def _watchdog_loop(self) -> None:
        if not self.enabled:
            return
        while self._running:
            time.sleep(3)
            now = time.time()
            with self._lock:
                expired_ids = [
                    session_id
                    for session_id, last_seen in self._sessions.items()
                    if (now - last_seen) > self.idle_shutdown_seconds
                ]
                for session_id in expired_ids:
                    self._sessions.pop(session_id, None)

                should_shutdown = self._had_session and not self._sessions
            if should_shutdown:
                self._request_shutdown()
                return

    def _request_shutdown(self) -> None:
        if not self.enabled:
            return
        server = self._server
        if server is not None and not server.should_exit:
            server.should_exit = True


session_manager = SessionManager(
    idle_shutdown_seconds=settings.idle_shutdown_seconds,
    enabled=settings.enable_idle_shutdown,
)
_SCORE_REFRESH_COOLDOWN_SECONDS = 60
_score_refresh_lock = threading.Lock()
_last_score_refresh_ts = 0.0


def _empty_payload() -> Dict[str, Any]:
    return {
        "generated_at": None,
        "scores_updated_at": None,
        "total_games_analyzed": 0,
        "total_bets": 0,
        "combined_odd_top2": None,
        "bets": [],
        "data_source": "live" if not settings.use_sample_data else "sample",
        "status": "ok",
        "error_message": None,
        "warning_message": None,
        "warning_details": None,
    }


def _looks_like_legacy_sample_payload(payload: Dict[str, Any]) -> bool:
    bets = payload.get("bets")
    if not isinstance(bets, list) or not bets:
        return False

    sample_games = {"Inter vs Lecce", "Real Madrid vs Getafe"}
    sample_fixture_ids = {900001, 900002}
    game_names = {
        str(bet.get("jogo", ""))
        for bet in bets
        if isinstance(bet, dict)
    }
    fixture_ids = {
        bet.get("fixture_id")
        for bet in bets
        if isinstance(bet, dict)
    }
    return bool(game_names) and game_names.issubset(sample_games) and fixture_ids.issubset(sample_fixture_ids)


def _safe_fixture_id(value: object) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _refresh_scores(payload: Dict[str, Any]) -> Dict[str, Any]:
    global _last_score_refresh_ts

    if settings.use_sample_data or payload.get("status") == "error":
        return payload

    bets = payload.get("bets")
    if not isinstance(bets, list) or not bets:
        return payload

    now = time.time()
    if (now - _last_score_refresh_ts) < _SCORE_REFRESH_COOLDOWN_SECONDS:
        return payload

    with _score_refresh_lock:
        now = time.time()
        if (now - _last_score_refresh_ts) < _SCORE_REFRESH_COOLDOWN_SECONDS:
            return payload

        fixture_ids = [
            fixture_id
            for fixture_id in (_safe_fixture_id(bet.get("fixture_id")) for bet in bets if isinstance(bet, dict))
            if fixture_id is not None
        ]
        if not fixture_ids:
            _last_score_refresh_ts = now
            return payload

        latest = FootballAPI().get_fixtures_status(fixture_ids)
        changed = False

        for bet in bets:
            if not isinstance(bet, dict):
                continue
            fixture_id = _safe_fixture_id(bet.get("fixture_id"))
            if fixture_id is None:
                continue
            updated = latest.get(fixture_id)
            if not isinstance(updated, dict):
                continue

            for field in ("status_short", "status_jogo", "home_goals", "away_goals"):
                new_value = updated.get(field)
                if bet.get(field) != new_value:
                    bet[field] = new_value
                    changed = True

        if changed:
            payload["scores_updated_at"] = datetime.now().isoformat(timespec="seconds")
            settings.data_file.parent.mkdir(parents=True, exist_ok=True)
            settings.data_file.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            if settings.persistir_em_banco:
                try:
                    repositorio = RepositorioHistoricoSQLite(settings.caminho_banco)
                    repositorio.atualizar_resultados_por_apostas(bets)
                except Exception:
                    pass

        _last_score_refresh_ts = time.time()

    return payload


def load_payload() -> Dict[str, Any]:
    if not settings.data_file.exists():
        return _empty_payload()

    try:
        payload = json.loads(settings.data_file.read_text(encoding="utf-8"))
    except Exception:
        return _empty_payload()

    if not isinstance(payload, dict):
        return _empty_payload()

    payload.setdefault("generated_at", None)
    payload.setdefault("scores_updated_at", None)
    payload.setdefault("total_games_analyzed", 0)
    payload.setdefault("total_bets", 0)
    payload.setdefault("combined_odd_top2", None)
    payload.setdefault("bets", [])
    payload.setdefault("data_source", "unknown")
    payload.setdefault("status", "ok")
    payload.setdefault("error_message", None)
    payload.setdefault("warning_message", None)
    payload.setdefault("warning_details", None)

    if not settings.use_sample_data and (
        payload.get("data_source") == "sample" or _looks_like_legacy_sample_payload(payload)
    ):
        filtered = _empty_payload()
        filtered["status"] = "error"
        filtered["error_message"] = (
            "Cache com dados ficticios detectado. "
            "Rode o pipeline novamente com USE_SAMPLE_DATA=false para gerar dados reais."
        )
        return filtered

    try:
        return _refresh_scores(payload)
    except Exception:
        return payload


def _probe_api_health() -> Dict[str, Any]:
    dependencies: Dict[str, Any] = {}
    overall_status = "ok"

    try:
        football_meta = FootballAPI().ensure_service_available()
        dependencies["api_football"] = {
            "status": str(football_meta.get("status", "ok")),
            "detail": "API-Football acessivel.",
        }
    except Exception as exc:
        overall_status = "degraded"
        dependencies["api_football"] = {
            "status": "error",
            "detail": str(exc),
        }

    try:
        available_sports = OddsAPI().ensure_service_available()
        dependencies["the_odds_api"] = {
            "status": "sample" if settings.use_sample_data else "ok",
            "detail": (
                "Modo sample ativo; sem consumo da The Odds API."
                if settings.use_sample_data
                else "The Odds API acessivel."
            ),
            "available_sports_count": len(available_sports),
        }
    except Exception as exc:
        overall_status = "degraded"
        dependencies["the_odds_api"] = {
            "status": "error",
            "detail": str(exc),
            "available_sports_count": 0,
        }

    return {
        "status": overall_status,
        "checked_at": datetime.now().isoformat(),
        "cache_seconds": settings.health_api_cache_seconds,
        "dependencies": dependencies,
    }


def _get_cached_api_health() -> Dict[str, Any]:
    now = time.time()
    ttl = max(0, int(settings.health_api_cache_seconds))

    with _API_HEALTH_LOCK:
        cached_value = _API_HEALTH_CACHE.get("value")
        cached_at = float(_API_HEALTH_CACHE.get("checked_at", 0.0) or 0.0)
        if cached_value is not None and ttl > 0 and (now - cached_at) < ttl:
            return dict(cached_value)

        snapshot = _probe_api_health()
        _API_HEALTH_CACHE["checked_at"] = now
        _API_HEALTH_CACHE["value"] = dict(snapshot)
        return snapshot


def _render_landing_page(request: Request, *, usuario_autenticado: bool) -> HTMLResponse:
    response = templates.TemplateResponse(
        request,
        "landing.html",
        {
            "request": request,
            "static_version": str(int(time.time())),
            "ui_version": UI_VERSION,
            "usuario_autenticado": usuario_autenticado,
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> Any:
    usuario_atual = obter_usuario_logado_opcional(request)
    if usuario_atual:
        return RedirectResponse(url="/dashboard", status_code=303)
    return _render_landing_page(request, usuario_autenticado=False)


@app.get("/planos", response_class=HTMLResponse)
def planos_page(request: Request) -> HTMLResponse:
    return _render_landing_page(
        request,
        usuario_autenticado=bool(obter_usuario_logado_opcional(request)),
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request) -> Any:
    try:
        usuario_atual = exigir_usuario_logado(request)
    except HTTPException:
        return redirecionar_para_login("Sua sessao expirou. Entre novamente.")

    response = templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "static_version": str(int(time.time())),
            "ui_version": UI_VERSION,
            "usuario_nome": str(usuario_atual.get("nome") or ""),
            "usuario_perfil": str(usuario_atual.get("perfil") or ""),
            "usuario_plano": str(usuario_atual.get("plano") or ""),
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/bets")
def bets(request: Request, response: Response) -> Dict[str, Any]:
    usuario_atual = exigir_usuario_logado(request)
    response.headers["Cache-Control"] = "no-store"
    return DashboardService.preparar_payload_dashboard(load_payload(), usuario_atual)


@app.get("/health")
def health() -> Dict[str, Any]:
    api_health = _get_cached_api_health()
    return {
        "status": api_health["status"],
        "app_env": settings.app_env,
        "data_file": str(settings.data_file),
        "data_file_exists": settings.data_file.exists(),
        "ui_version": UI_VERSION,
        "api_health": api_health,
    }


@app.post("/session/start")
def start_session(request: Request) -> Dict[str, str]:
    exigir_usuario_logado(request)
    return {"session_id": session_manager.start_session()}


@app.post("/session/heartbeat")
def session_heartbeat(request: Request, session_id: str) -> Dict[str, bool]:
    exigir_usuario_logado(request)
    return {"ok": session_manager.heartbeat(session_id)}


@app.post("/session/end")
def end_session(request: Request, session_id: str) -> Dict[str, bool]:
    exigir_usuario_logado(request)
    session_manager.end_session(session_id)
    return {"ok": True}


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    config = uvicorn.Config(app=app, host=host, port=port, reload=False)
    server = uvicorn.Server(config=config)
    session_manager.attach_server(server)
    session_manager.start_watchdog()
    try:
        server.run()
    finally:
        session_manager.stop_watchdog()
