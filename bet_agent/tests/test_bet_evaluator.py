from types import SimpleNamespace

import services.bet_evaluator as bet_evaluator_module
from services.bet_evaluator import BetEvaluator


def test_evaluate_match_filters_and_sorts(monkeypatch):
    monkeypatch.setattr(
        bet_evaluator_module,
        "settings",
        SimpleNamespace(min_probability=0.6, min_ev=0.0),
    )
    evaluator = BetEvaluator()

    match = {
        "fixture_id": 10,
        "home_team": "Inter",
        "away_team": "Milan",
        "league": "Serie A",
        "kickoff": "2026-03-14T18:00:00",
    }
    probabilities = {"over_1_5": 0.72, "draw": 0.2, "home_win": 0.61}
    odds = {"over_1_5": 1.6, "draw": 3.0, "home_win": 1.8}

    recommendations = evaluator.evaluate_match(match, probabilities, odds)

    assert [item["mercado_chave"] for item in recommendations] == ["over_1_5", "home_win"]
    assert recommendations[0]["probability"] >= recommendations[1]["probability"]


def test_build_payload_combines_top_two_odds():
    payload = BetEvaluator.build_payload(
        [
            {"mercado_chave": "over_1_5", "probability": 0.82, "odd": 1.6, "ev": 0.31},
            {"mercado_chave": "home_win", "probability": 0.7, "odd": 1.9, "ev": 0.12},
        ],
        data_source="sample",
    )

    assert payload["total_bets"] == 2
    assert payload["combined_odd_top2"] == 3.04
    assert payload["data_source"] == "sample"
