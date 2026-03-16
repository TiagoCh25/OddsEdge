"""Pipeline runner: fetch data, evaluate bets, save results and start the web server."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from typing import Dict, List
from uuid import uuid4

from api.football_api import FootballAPI
from api.odds_api import OddsAPI, build_match_key
from app.config import settings
from db.repositorio_historico import (
    DadosPersistenciaExecucao,
    RepositorioHistoricoSQLite,
)
from models.poisson_model import PoissonModel
from services.bet_evaluator import BetEvaluator
from services.probability_service import ProbabilityService, TeamStatsUnavailableError


def _data_source() -> str:
    return "sample" if settings.use_sample_data else "live"


def _write_payload(payload: Dict[str, object]) -> None:
    settings.data_file.parent.mkdir(parents=True, exist_ok=True)
    settings.data_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_history_snapshot(
    payload: Dict[str, object],
    *,
    execucao_id: str,
    reference_date: date,
) -> None:
    snapshot_dir = (
        settings.history_dir
        / reference_date.strftime("%Y")
        / reference_date.strftime("%m")
        / reference_date.strftime("%d")
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshot_dir / f"{execucao_id}.json"
    snapshot_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_cached_payload() -> Dict[str, object] | None:
    if not settings.data_file.exists():
        return None
    try:
        raw = json.loads(settings.data_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def _load_cached_recommendations_for_today(
    reference_date: datetime.date,
    fixtures_today: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    cached_payload = _load_cached_payload()
    if not cached_payload:
        return []

    generated_at = cached_payload.get("generated_at")
    if not generated_at:
        return []

    try:
        generated_date = datetime.fromisoformat(str(generated_at)).date()
    except Exception:
        return []

    if generated_date != reference_date:
        return []

    cached_bets = cached_payload.get("bets")
    if not isinstance(cached_bets, list) or not cached_bets:
        return []

    today_fixture_ids = {
        int(item.get("fixture_id"))
        for item in fixtures_today
        if item.get("fixture_id") is not None
    }
    filtered_bets: List[Dict[str, object]] = []
    for bet in cached_bets:
        if not isinstance(bet, dict):
            continue
        try:
            fixture_id = int(bet.get("fixture_id"))
        except Exception:
            continue
        if fixture_id in today_fixture_ids:
            filtered_bets.append(bet)

    return filtered_bets


def _enrich_recommendations_with_match_metadata(
    recommendations: List[Dict[str, object]],
    matches: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    match_by_fixture: Dict[int, Dict[str, object]] = {}
    for match in matches:
        fixture_id = match.get("fixture_id")
        try:
            if fixture_id is None:
                continue
            match_by_fixture[int(fixture_id)] = match
        except Exception:
            continue

    enriched: List[Dict[str, object]] = []
    for bet in recommendations:
        if not isinstance(bet, dict):
            continue

        item = dict(bet)
        fixture_id = item.get("fixture_id")
        try:
            fixture_id_int = int(fixture_id) if fixture_id is not None else None
        except Exception:
            fixture_id_int = None

        match = match_by_fixture.get(fixture_id_int) if fixture_id_int is not None else None
        if isinstance(match, dict):
            home_team = str(match.get("home_team") or "")
            away_team = str(match.get("away_team") or "")
            if not item.get("jogo") and home_team and away_team:
                item["jogo"] = f"{home_team} vs {away_team}"
            item["liga"] = item.get("liga") or match.get("league", "")
            item["home_team"] = item.get("home_team") or home_team
            item["away_team"] = item.get("away_team") or away_team
            item["league_logo"] = item.get("league_logo") or match.get("league_logo", "")
            item["home_team_logo"] = item.get("home_team_logo") or match.get("home_team_logo", "")
            item["away_team_logo"] = item.get("away_team_logo") or match.get("away_team_logo", "")

        enriched.append(item)

    return enriched


def _append_warning_message(payload: Dict[str, object], message: str) -> None:
    current = str(payload.get("warning_message") or "").strip()
    if not current:
        payload["warning_message"] = message
        return
    if message in current:
        return
    payload["warning_message"] = f"{current} {message}"


def _attach_best_bookmakers(
    bets: List[Dict[str, object]],
    *,
    odds_api: OddsAPI,
    match_key: str,
) -> None:
    for bet in bets:
        market_key = str(bet.get("mercado_chave") or "").strip()
        bet["best_bookmakers"] = odds_api.get_best_bookmakers_for_match(match_key, market_key)


def _build_match_processing_error(match: Dict[str, object], exc: Exception) -> Dict[str, object]:
    base_error = {
        "fixture_id": match.get("fixture_id"),
        "jogo": f"{match.get('home_team')} vs {match.get('away_team')}",
        "liga": match.get("league"),
        "time_nome": "",
        "time_id": None,
        "lado_time": "",
        "etapa": "processamento_partida",
        "mensagem_erro": str(exc),
    }

    if isinstance(exc, TeamStatsUnavailableError):
        base_error["time_nome"] = exc.team_name
        base_error["time_id"] = exc.team_id
        base_error["lado_time"] = exc.side
        base_error["etapa"] = "estatisticas_time"

    return base_error


def run_daily_pipeline() -> Dict[str, object]:
    football_api = FootballAPI()
    odds_api = OddsAPI()
    poisson_model = PoissonModel(max_goals=settings.max_poisson_goals)
    probability_service = ProbabilityService(football_api=football_api, poisson_model=poisson_model)
    evaluator = BetEvaluator()
    execucao_id = uuid4().hex
    total_games_analyzed = 0
    total_games_with_odds = 0
    stats_basis_by_match: List[Dict[str, object]] = []
    matches: List[Dict[str, object]] = []
    odds_by_match: Dict[str, Dict[str, float]] = {}
    recommendations: List[Dict[str, object]] = []
    processing_errors: List[Dict[str, object]] = []
    today = datetime.now().date()
    cached_today_recommendations: List[Dict[str, object]] = []

    try:
        matches = football_api.get_todays_matches(today)
        total_games_analyzed = len(matches)
        cached_today_recommendations = _load_cached_recommendations_for_today(today, matches)
        cached_today_recommendations = _enrich_recommendations_with_match_metadata(
            cached_today_recommendations,
            matches,
        )
        if matches:
            odds_api.ensure_service_available()
        odds_by_match = odds_api.get_odds_for_matches(matches)

        recommendations = []
        for match in matches:
            match_key = build_match_key(match["home_team"], match["away_team"])
            match["chave_partida"] = match_key
            odds = odds_by_match.get(match_key, {})
            if not odds:
                continue

            total_games_with_odds += 1
            try:
                probability_output = probability_service.estimate_match_probabilities(match)
                probabilities = probability_output["probabilities"]
                stats_basis = probability_output.get("stats_basis", {})
                stats_basis_by_match.append(
                    {
                        "fixture_id": match.get("fixture_id"),
                        "jogo": f"{match.get('home_team')} vs {match.get('away_team')}",
                        "liga": match.get("league"),
                        "stats_basis": stats_basis,
                    }
                )
                match_recommendations = evaluator.evaluate_match(match, probabilities, odds)
                _attach_best_bookmakers(match_recommendations, odds_api=odds_api, match_key=match_key)
                for bet in match_recommendations:
                    bet["stats_basis"] = stats_basis
                recommendations.extend(match_recommendations)
            except Exception as exc:
                processing_errors.append(_build_match_processing_error(match, exc))
                continue

        recommendations = _enrich_recommendations_with_match_metadata(recommendations, matches)
        if not recommendations and cached_today_recommendations:
            payload = evaluator.build_payload(cached_today_recommendations, data_source=_data_source())
            payload["warning_message"] = (
                "Odds temporariamente limitadas. Exibindo as ultimas recomendacoes validas geradas hoje."
            )
        else:
            payload = evaluator.build_payload(recommendations, data_source=_data_source())
    except Exception as exc:
        exc_text = str(exc or "")
        is_quota_exhausted = ("OUT_OF_USAGE_CREDITS" in exc_text.upper()) or ("SEM CREDITOS" in exc_text.upper())
        if cached_today_recommendations:
            payload = evaluator.build_payload(cached_today_recommendations, data_source=_data_source())
            if is_quota_exhausted:
                payload["warning_message"] = (
                    "Cota da The Odds API esgotada. Exibindo as ultimas recomendacoes validas de hoje."
                )
            else:
                payload["warning_message"] = (
                    "Falha temporaria ao atualizar as odds. Exibindo as ultimas recomendacoes validas de hoje."
                )
            payload["warning_details"] = str(exc)
        else:
            payload = evaluator.build_payload(
                [],
                data_source=_data_source(),
                status="error",
                error_message=str(exc),
            )

    payload["total_games_analyzed"] = total_games_analyzed
    payload["total_games_with_odds"] = total_games_with_odds
    payload["stats_basis_by_match"] = stats_basis_by_match
    payload["processing_errors"] = processing_errors
    payload["skipped_matches_count"] = len(processing_errors)
    payload["execucao_id"] = execucao_id
    _write_payload(payload)
    _write_history_snapshot(payload, execucao_id=execucao_id, reference_date=today)

    if settings.persistir_em_banco:
        try:
            repositorio = RepositorioHistoricoSQLite(settings.caminho_banco)
            repositorio.salvar_execucao_completa(
                DadosPersistenciaExecucao(
                    execucao_id=execucao_id,
                    data_referencia=today.isoformat(),
                    ambiente=settings.app_env,
                    fonte_dados=_data_source(),
                    payload=payload,
                    partidas=matches,
                    odds_por_partida=odds_by_match,
                    apostas_recomendadas=payload.get("bets", []) if isinstance(payload.get("bets"), list) else [],
                    stats_basis_por_partida=stats_basis_by_match,
                    erros_processamento=processing_errors,
                )
            )
        except Exception as exc:
            # Persistencia em banco e complementar e nao deve quebrar a execucao principal.
            print(f"[aviso] Falha ao persistir historico no banco: {exc}")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Bet Agent application runner.")
    parser.add_argument(
        "mode",
        nargs="?",
        default="run-all",
        choices=("run-all", "serve", "pipeline"),
        help="run-all: pipeline + web, serve: web only, pipeline: pipeline only",
    )
    args = parser.parse_args()

    from web.server import start_server

    if args.mode == "pipeline":
        run_daily_pipeline()
        return

    if args.mode == "run-all" and not settings.skip_pipeline_on_start:
        run_daily_pipeline()

    start_server(host=settings.server_host, port=settings.server_port)


if __name__ == "__main__":
    main()
