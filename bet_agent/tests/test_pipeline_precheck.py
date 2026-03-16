from pathlib import Path
from types import SimpleNamespace

import app.main as main_module


def test_run_daily_pipeline_fails_fast_when_odds_precheck_fails(monkeypatch, tmp_path: Path):
    probability_calls = []
    odds_calls = []

    class FakeFootballAPI:
        def get_todays_matches(self, _today):
            return [
                {
                    "fixture_id": 1,
                    "home_team": "Sassuolo",
                    "away_team": "Bologna",
                    "home_team_id": 488,
                    "away_team_id": 500,
                    "league_id": 135,
                    "league": "Serie A",
                    "season": 2025,
                }
            ]

    class FakeOddsAPI:
        def ensure_service_available(self):
            raise RuntimeError("The Odds API indisponivel no pre-check.")

        def get_odds_for_matches(self, _matches):
            odds_calls.append("called")
            raise AssertionError("Nao deveria consultar odds apos falha no pre-check.")

    class FakePoissonModel:
        def __init__(self, max_goals):
            self.max_goals = max_goals

    class FakeProbabilityService:
        def __init__(self, football_api, poisson_model):
            self.football_api = football_api
            self.poisson_model = poisson_model

        def estimate_match_probabilities(self, match):
            probability_calls.append(match)
            raise AssertionError("Nao deveria calcular probabilidades apos falha no pre-check.")

    class FakeBetEvaluator:
        def evaluate_match(self, match, probabilities, odds):
            raise AssertionError("Nao deveria avaliar apostas apos falha no pre-check.")

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

    assert payload["status"] == "error"
    assert "The Odds API indisponivel no pre-check." in str(payload["error_message"])
    assert payload["total_games_analyzed"] == 1
    assert payload["total_games_with_odds"] == 0
    assert probability_calls == []
    assert odds_calls == []
