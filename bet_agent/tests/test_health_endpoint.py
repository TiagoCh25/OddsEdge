from pathlib import Path
from types import SimpleNamespace

import web.server as server_module


def test_health_exposes_api_status(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        server_module,
        "settings",
        SimpleNamespace(
            app_env="test",
            data_file=tmp_path / "cache_matches.json",
            health_api_cache_seconds=300,
            use_sample_data=False,
        ),
    )
    monkeypatch.setattr(
        server_module,
        "_get_cached_api_health",
        lambda: {
            "status": "degraded",
            "checked_at": "2026-03-15T11:00:00",
            "cache_seconds": 300,
            "dependencies": {
                "api_football": {"status": "ok", "detail": "API-Football acessivel."},
                "the_odds_api": {
                    "status": "error",
                    "detail": "The Odds API indisponivel.",
                    "available_sports_count": 0,
                },
            },
        },
    )

    payload = server_module.health()

    assert payload["status"] == "degraded"
    assert payload["app_env"] == "test"
    assert payload["data_file_exists"] is False
    assert payload["api_health"]["dependencies"]["api_football"]["status"] == "ok"
    assert payload["api_health"]["dependencies"]["the_odds_api"]["status"] == "error"
