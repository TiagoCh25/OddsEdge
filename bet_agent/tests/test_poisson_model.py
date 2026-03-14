from models.poisson_model import PoissonModel


def test_market_probabilities_stay_in_valid_range():
    model = PoissonModel(max_goals=7)

    probabilities = model.market_probabilities(lambda_home=1.4, lambda_away=0.9)

    assert 0.98 <= (
        probabilities["home_win"] + probabilities["draw"] + probabilities["away_win"]
    ) <= 1.01
    assert probabilities["over_1_5"] >= probabilities["over_2_5"]
    assert probabilities["under_3_5"] >= probabilities["under_2_5"]
    assert round(probabilities["btts_yes"] + probabilities["btts_no"], 6) == 1.0
