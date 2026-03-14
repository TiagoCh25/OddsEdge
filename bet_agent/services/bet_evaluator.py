"""Evaluate betting candidates from probabilities and market odds."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from app.config import settings


class BetEvaluator:
    MARKET_MAP = [
        ("Over 0.5 gols", "over_0_5"),
        ("Over 1.5 gols", "over_1_5"),
        ("Over 2.5 gols", "over_2_5"),
        ("Over 3.5 gols", "over_3_5"),
        ("Under 2.5 gols", "under_2_5"),
        ("Under 3.5 gols", "under_3_5"),
        ("Ambos marcam (BTTS)", "btts_yes"),
        ("Ambos NAO marcam", "btts_no"),
        ("Vitoria Casa", "home_win"),
        ("Empate", "draw"),
        ("Vitoria Visitante", "away_win"),
        ("Dupla chance 1X", "double_chance_1x"),
        ("Dupla chance X2", "double_chance_x2"),
        ("Dupla chance 12", "double_chance_12"),
    ]

    @staticmethod
    def _ev(probability: float, odd: float) -> float:
        return (probability * odd) - 1

    def evaluate_match(
        self,
        match: Dict[str, object],
        probabilities: Dict[str, float],
        odds: Dict[str, float],
    ) -> List[Dict[str, object]]:
        recommendations: List[Dict[str, object]] = []
        game_name = f"{match['home_team']} vs {match['away_team']}"

        for market_label, market_key in self.MARKET_MAP:
            probability = float(probabilities.get(market_key, 0))
            odd = float(odds.get(market_key, 0))

            if odd <= 1:
                continue

            ev = self._ev(probability, odd)
            if probability >= settings.min_probability and ev > settings.min_ev:
                recommendations.append(
                    {
                        "fixture_id": match["fixture_id"],
                        "jogo": game_name,
                        "liga": match["league"],
                        "league_logo": match.get("league_logo", ""),
                        "home_team": match.get("home_team", ""),
                        "away_team": match.get("away_team", ""),
                        "home_team_logo": match.get("home_team_logo", ""),
                        "away_team_logo": match.get("away_team_logo", ""),
                        "tipo_aposta": market_label,
                        "mercado_chave": market_key,
                        "probability": round(probability, 4),
                        "probabilidade": round(probability * 100, 2),
                        "odd": round(odd, 3),
                        "ev": round(ev, 4),
                        "kickoff": match["kickoff"],
                        "status_short": match.get("status_short"),
                        "status_jogo": match.get("status_jogo"),
                        "home_goals": match.get("home_goals"),
                        "away_goals": match.get("away_goals"),
                    }
                )

        recommendations.sort(key=lambda item: (item["probability"], item["ev"]), reverse=True)
        return recommendations

    @staticmethod
    def build_payload(
        recommended_bets: List[Dict[str, object]],
        *,
        data_source: str = "live",
        status: str = "ok",
        error_message: str | None = None,
    ) -> Dict[str, object]:
        sorted_bets = sorted(
            recommended_bets,
            key=lambda item: (float(item.get("probability", 0)), float(item.get("ev", 0))),
            reverse=True,
        )

        combined_odd = 1.0
        for bet in sorted_bets[:2]:
            combined_odd *= float(bet["odd"])

        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_bets": len(sorted_bets),
            "combined_odd_top2": round(combined_odd, 3) if sorted_bets else None,
            "bets": sorted_bets,
            "data_source": data_source,
            "status": status,
            "error_message": error_message,
        }
