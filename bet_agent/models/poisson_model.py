from __future__ import annotations

import math
from typing import Dict


class PoissonModel:

    def __init__(self, max_goals: int = 6, rho: float = -0.1):
        """
        max_goals: limite de gols considerados na matriz
        rho: parâmetro de correção Dixon-Coles
        """
        self.MAX_GOALS = max_goals
        self.rho = rho

    @staticmethod
    def _poisson_probability(k: int, lam: float) -> float:
        """Probability of scoring k goals with Poisson distribution."""
        return (lam ** k * math.exp(-lam)) / math.factorial(k)

    def _tau(self, h: int, a: int, lambda_home: float, lambda_away: float) -> float:
        """
        Dixon-Coles adjustment factor.
        Corrige probabilidades de placares baixos.
        """
        if h == 0 and a == 0:
            return 1 - (lambda_home * lambda_away * self.rho)

        if h == 0 and a == 1:
            return 1 + (lambda_home * self.rho)

        if h == 1 and a == 0:
            return 1 + (lambda_away * self.rho)

        if h == 1 and a == 1:
            return 1 - self.rho

        return 1.0

    def _goal_matrix(self, lambda_home: float, lambda_away: float):
        """Build probability matrix for scorelines."""
        matrix = []

        for h in range(self.MAX_GOALS + 1):
            row = []
            for a in range(self.MAX_GOALS + 1):

                p_home = self._poisson_probability(h, lambda_home)
                p_away = self._poisson_probability(a, lambda_away)

                base_prob = p_home * p_away
                tau = self._tau(h, a, lambda_home, lambda_away)

                row.append(base_prob * tau)

            matrix.append(row)

        return matrix

    def market_probabilities(self, lambda_home: float, lambda_away: float) -> Dict[str, float]:

        matrix = self._goal_matrix(lambda_home, lambda_away)

        home_win = 0.0
        draw = 0.0
        away_win = 0.0

        over_0_5 = 0.0
        over_1_5 = 0.0
        over_2_5 = 0.0
        over_3_5 = 0.0

        under_2_5 = 0.0
        under_3_5 = 0.0

        btts_yes = 0.0

        for h in range(self.MAX_GOALS + 1):
            for a in range(self.MAX_GOALS + 1):

                p = matrix[h][a]
                total_goals = h + a

                # Resultado
                if h > a:
                    home_win += p
                elif h == a:
                    draw += p
                else:
                    away_win += p

                # Overs
                if total_goals > 0:
                    over_0_5 += p

                if total_goals > 1:
                    over_1_5 += p

                if total_goals > 2:
                    over_2_5 += p

                if total_goals > 3:
                    over_3_5 += p

                # Unders
                if total_goals <= 2:
                    under_2_5 += p

                if total_goals <= 3:
                    under_3_5 += p

                # BTTS
                if h > 0 and a > 0:
                    btts_yes += p

        btts_no = 1 - btts_yes

        double_chance_1x = home_win + draw
        double_chance_x2 = draw + away_win
        double_chance_12 = home_win + away_win

        return {
            "home_win": home_win,
            "draw": draw,
            "away_win": away_win,

            "over_0_5": over_0_5,
            "over_1_5": over_1_5,
            "over_2_5": over_2_5,
            "over_3_5": over_3_5,

            "under_2_5": under_2_5,
            "under_3_5": under_3_5,

            "btts_yes": btts_yes,
            "btts_no": btts_no,

            "double_chance_1x": double_chance_1x,
            "double_chance_x2": double_chance_x2,
            "double_chance_12": double_chance_12,
        }
