"""Service that transforms team stats into Poisson market probabilities."""

from __future__ import annotations

from typing import Dict

from api.football_api import FootballAPI
from app.config import settings
from models.poisson_model import PoissonModel


class ProbabilityService:
    def __init__(self, football_api: FootballAPI, poisson_model: PoissonModel) -> None:
        self.football_api = football_api
        self.poisson_model = poisson_model

    def estimate_match_probabilities(self, match: Dict[str, object]) -> Dict[str, object]:
        league_goal_avg = settings.league_goal_avg

        home_stats = self.football_api.get_team_recent_stats(
            team_id=int(match["home_team_id"]),
            league_id=int(match["league_id"]),
            season=int(match["season"]),
        )
        away_stats = self.football_api.get_team_recent_stats(
            team_id=int(match["away_team_id"]),
            league_id=int(match["league_id"]),
            season=int(match["season"]),
        )

        home_attack_strength = max(
            home_stats["avg_goals_for"] / league_goal_avg, 0.2)
        home_defense_strength = max(
            home_stats["avg_goals_against"] / league_goal_avg, 0.2)
        away_attack_strength = max(
            away_stats["avg_goals_for"] / league_goal_avg, 0.2)
        away_defense_strength = max(
            away_stats["avg_goals_against"] / league_goal_avg, 0.2)

        lambda_home = league_goal_avg * home_attack_strength * away_defense_strength * 1.10
        lambda_away = league_goal_avg * away_attack_strength * home_defense_strength * 0.95

        lambda_home = min(max(lambda_home, 0.15), 4.0)
        lambda_away = min(max(lambda_away, 0.15), 4.0)

        probabilities = self.poisson_model.market_probabilities(
            lambda_home, lambda_away)

        home_source_season = home_stats.get("stats_source_season")
        away_source_season = away_stats.get("stats_source_season")
        if home_source_season == away_source_season and home_source_season is not None:
            stats_source_label = f"season_{home_source_season}"
        else:
            stats_source_label = f"home_{home_source_season}_away_{away_source_season}"

        return {
            "lambda_home": lambda_home,
            "lambda_away": lambda_away,
            "home_stats": home_stats,
            "away_stats": away_stats,
            "probabilities": probabilities,
            "stats_basis": {
                "label": stats_source_label,
                "home": {
                    "season": home_source_season,
                    "scope": home_stats.get("stats_source_scope"),
                    "query": home_stats.get("stats_source_query"),
                    "note": home_stats.get("stats_source_note"),
                },
                "away": {
                    "season": away_source_season,
                    "scope": away_stats.get("stats_source_scope"),
                    "query": away_stats.get("stats_source_query"),
                    "note": away_stats.get("stats_source_note"),
                },
            },
        }
