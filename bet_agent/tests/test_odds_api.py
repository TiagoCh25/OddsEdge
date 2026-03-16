from types import SimpleNamespace

import api.odds_api as odds_api_module
from api.odds_api import OddsAPI


def test_select_top_bookmakers_returns_top_three_by_odd_then_tiebreakers(monkeypatch):
    monkeypatch.setattr(
        odds_api_module,
        "settings",
        SimpleNamespace(
            the_odds_base_url="https://example.com/v4",
            requests_trust_env=False,
            odds_preferred_bookmakers=["pinnacle", "betfair_ex_eu", "betway"],
            odds_relevant_bookmakers=["betfair", "bet365", "betnacional", "sportingbet"],
        ),
    )
    api = OddsAPI()
    api._bookmaker_run_presence = {
        "Sportingbet": 2,
        "Betnacional": 4,
        "Novibet": 1,
        "SeuBet": 3,
    }

    selected = api._select_top_bookmakers(
        [
            {"name": "Sportingbet", "odd": 6.5, "coverage": 6},
            {"name": "Betfair", "odd": 6.69, "coverage": 4},
            {"name": "Bet365", "odd": 6.5, "coverage": 8},
            {"name": "Betnacional", "odd": 6.5, "coverage": 6},
        ]
    )

    assert [item["name"] for item in selected] == [
        "Betfair",
        "Bet365",
        "Betnacional",
    ]
    assert selected[0]["url"] == "https://www.betfair.com/"


def test_display_name_for_bookmaker_normalizes_supported_aliases():
    assert OddsAPI._display_name_for_bookmaker("betfair_ex_eu") == "Betfair"
    assert OddsAPI._display_name_for_bookmaker("onexbet") == "1xBet"


def test_select_top_bookmakers_filters_to_relevant_group_when_available(monkeypatch):
    monkeypatch.setattr(
        odds_api_module,
        "settings",
        SimpleNamespace(
            the_odds_base_url="https://example.com/v4",
            requests_trust_env=False,
            odds_preferred_bookmakers=["pinnacle", "betfair_ex_eu", "betway"],
            odds_relevant_bookmakers=["betfair", "bet365", "betnacional"],
        ),
    )
    api = OddsAPI()
    api._bookmaker_run_presence = {
        "Betfair": 3,
        "Bet365": 2,
        "Betnacional": 1,
        "Casa Estranha": 5,
    }

    selected = api._select_top_bookmakers(
        [
            {"name": "Casa Estranha", "odd": 7.10, "coverage": 7},
            {"name": "Betfair", "odd": 6.90, "coverage": 6},
            {"name": "Bet365", "odd": 6.80, "coverage": 5},
            {"name": "Betnacional", "odd": 6.70, "coverage": 4},
        ]
    )

    assert [item["name"] for item in selected] == [
        "Betfair",
        "Bet365",
        "Betnacional",
    ]
