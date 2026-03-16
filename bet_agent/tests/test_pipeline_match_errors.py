from pathlib import Path
from types import SimpleNamespace

import app.main as main_module
from services.probability_service import TeamStatsUnavailableError


def test_run_daily_pipeline_skips_match_with_stats_error(monkeypatch, tmp_path: Path):
    class FakeFootballAPI:
        def get_todays_matches(self, _today):
            return [
                {
                    "fixture_id": 1,
                    "home_team": "Palmeiras",
                    "away_team": "Mirassol",
                    "home_team_id": 121,
                    "away_team_id": 7848,
                    "league_id": 71,
                    "league": "Serie A",
                    "season": 2026,
                    "kickoff": "2026-03-15T18:00:00",
                },
                {
                    "fixture_id": 2,
                    "home_team": "Inter",
                    "away_team": "Milan",
                    "home_team_id": 1,
                    "away_team_id": 2,
                    "league_id": 135,
                    "league": "Serie A",
                    "season": 2024,
                    "kickoff": "2026-03-15T20:00:00",
                },
            ]

    class FakeOddsAPI:
        def ensure_service_available(self):
            return {"soccer_italy_serie_a", "soccer_brazil_campeonato"}

        def get_odds_for_matches(self, _matches):
            return {
                "palmeiras__mirassol": {"over_1_5": 1.8},
                "inter__milan": {"over_1_5": 1.9},
            }

        def get_best_bookmakers_for_match(self, match_key, market_key):
            if match_key == "inter__milan" and market_key == "over_1_5":
                return [
                    {"name": "Betfair", "odd": 6.69, "url": "https://www.betfair.com/"},
                    {"name": "Bet365", "odd": 6.5, "url": "https://www.bet365.com/"},
                    {"name": "Sportingbet", "odd": 6.5, "url": "https://www.sportingbet.com/"},
                ]
            return []

    class FakePoissonModel:
        def __init__(self, max_goals):
            self.max_goals = max_goals

    class FakeProbabilityService:
        def __init__(self, football_api, poisson_model):
            self.football_api = football_api
            self.poisson_model = poisson_model

        def estimate_match_probabilities(self, match):
            if int(match["fixture_id"]) == 1:
                raise TeamStatsUnavailableError(
                    team_id=7848,
                    team_name="Mirassol",
                    side="away",
                    message="Falha ao buscar estatisticas do time Mirassol (id 7848) na API-Football.",
                )
            return {
                "probabilities": {"over_1_5": 0.74},
                "stats_basis": {
                    "label": "season_2024",
                    "home": {"season": 2024, "scope": "league", "query": "season_full", "note": "ok"},
                    "away": {"season": 2024, "scope": "league", "query": "season_full", "note": "ok"},
                },
            }

    class FakeBetEvaluator:
        def evaluate_match(self, match, probabilities, odds):
            return [
                {
                    "fixture_id": match["fixture_id"],
                    "jogo": f"{match['home_team']} vs {match['away_team']}",
                    "liga": match["league"],
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "tipo_aposta": "Over 1.5 gols",
                    "mercado_chave": "over_1_5",
                    "probability": probabilities["over_1_5"],
                    "probabilidade": 74.0,
                    "odd": odds["over_1_5"],
                    "ev": 0.406,
                    "kickoff": match["kickoff"],
                }
            ]

        @staticmethod
        def build_payload(bets, data_source, status="ok", error_message=None):
            return {
                "generated_at": "2026-03-15T10:00:00",
                "bets": bets,
                "status": status,
                "error_message": error_message,
                "data_source": data_source,
                "total_bets": len(bets),
                "combined_odd_top2": None,
            }

    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            use_sample_data=False,
            data_file=tmp_path / "cache_matches.json",
            history_dir=tmp_path / "history",
            persistir_em_banco=False,
            max_poisson_goals=7,
        ),
    )
    monkeypatch.setattr(main_module, "FootballAPI", FakeFootballAPI)
    monkeypatch.setattr(main_module, "OddsAPI", FakeOddsAPI)
    monkeypatch.setattr(main_module, "PoissonModel", FakePoissonModel)
    monkeypatch.setattr(main_module, "ProbabilityService", FakeProbabilityService)
    monkeypatch.setattr(main_module, "BetEvaluator", FakeBetEvaluator)

    payload = main_module.run_daily_pipeline()

    assert payload["status"] == "ok"
    assert payload["total_games_analyzed"] == 2
    assert payload["total_games_with_odds"] == 2
    assert payload["total_bets"] == 1
    assert payload["skipped_matches_count"] == 1
    assert payload["bets"][0]["fixture_id"] == 2
    assert payload.get("warning_message") in {None, ""}
    assert len(payload["bets"][0]["best_bookmakers"]) == 3
    assert payload["bets"][0]["best_bookmakers"][0]["name"] == "Betfair"
    assert payload["processing_errors"][0]["time_nome"] == "Mirassol"
    assert payload["processing_errors"][0]["fixture_id"] == 1
