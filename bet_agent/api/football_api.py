"""Client for API-Football endpoints used by the pipeline."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Tuple

import requests
from requests.exceptions import ProxyError

from app.config import settings


class FootballAPI:
    def __init__(self) -> None:
        self.base_url = settings.api_football_base_url.rstrip("/")
        self.session = requests.Session()
        self.session.trust_env = settings.requests_trust_env
        self._api_keys = list(settings.api_football_keys)
        self._stats_cache: Dict[Tuple[int, int, int], Dict[str, object]] = {}

    def _headers(self, api_key: str) -> Dict[str, str]:
        if settings.api_football_auth_mode == "rapidapi":
            return {
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": settings.api_football_host,
            }
        return {"x-apisports-key": api_key}

    @staticmethod
    def _is_daily_limit_error(error_text: str) -> bool:
        text = str(error_text or "").strip().lower()
        if not text:
            return False
        markers = (
            "request limit for the day",
            "reached the request limit",
            "quota",
            "too many requests",
        )
        return any(marker in text for marker in markers)

    def _request(self, endpoint: str, params: Dict[str, object]) -> Dict[str, object]:
        if not self._api_keys:
            raise RuntimeError(
                "API_FOOTBALL_KEY nao configurada. "
                "Defina API_FOOTBALL_KEY ou use USE_SAMPLE_DATA=true."
            )

        url = f"{self.base_url}{endpoint}"
        last_error: str | None = None

        for index, api_key in enumerate(self._api_keys):
            has_next_key = index < (len(self._api_keys) - 1)

            response = self.session.get(
                url,
                headers=self._headers(api_key),
                params=params,
                timeout=settings.request_timeout_seconds,
            )
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                is_quota_http = response.status_code == 429
                if has_next_key and is_quota_http:
                    last_error = f"HTTP {response.status_code}"
                    continue
                raise exc

            payload = response.json()
            api_error = self._payload_error_text(payload)
            if not api_error:
                return payload

            last_error = api_error
            if has_next_key and self._is_daily_limit_error(api_error):
                continue
            raise RuntimeError(api_error)

        raise RuntimeError(last_error or "Falha ao consultar API-Football.")

    @staticmethod
    def _extract_status_and_score(fixture: Dict[str, object]) -> Dict[str, object]:
        status_info = fixture.get("fixture", {}).get("status", {})
        score = fixture.get("score", {})
        fulltime = score.get("fulltime", {})
        goals = fixture.get("goals", {})

        home_goals = fulltime.get("home")
        away_goals = fulltime.get("away")
        if home_goals is None:
            home_goals = goals.get("home")
        if away_goals is None:
            away_goals = goals.get("away")

        return {
            "status_short": status_info.get("short"),
            "status_jogo": status_info.get("long"),
            "home_goals": int(home_goals) if home_goals is not None else None,
            "away_goals": int(away_goals) if away_goals is not None else None,
        }

    def get_todays_matches(self, match_date: date) -> List[Dict[str, object]]:
        if settings.use_sample_data:
            return self._sample_matches(match_date)
        if not settings.api_football_keys:
            raise RuntimeError(
                "API_FOOTBALL_KEY nao configurada. "
                "Defina a variavel de ambiente ou use USE_SAMPLE_DATA=true."
            )

        try:
            payload = self._request(
                "/fixtures",
                {"date": match_date.isoformat(), "timezone": settings.timezone},
            )
            api_error = self._payload_error_text(payload)
            if api_error:
                raise RuntimeError(api_error)
            fixtures = payload.get("response", [])
        except ProxyError as exc:
            raise RuntimeError(
                "Falha de proxy ao acessar API-Football. "
                "Defina REQUESTS_TRUST_ENV=false para ignorar proxies do sistema "
                "ou corrija HTTP_PROXY/HTTPS_PROXY."
            ) from exc
        except RuntimeError as exc:
            raise RuntimeError(
                "Falha ao buscar jogos na API-Football. "
                f"Detalhes: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                "Falha ao buscar jogos na API-Football. "
                "Verifique API_FOOTBALL_KEY e API_FOOTBALL_AUTH_MODE "
                "('apisports' para API-Sports, 'rapidapi' para RapidAPI)."
            ) from exc

        matches: List[Dict[str, object]] = []
        for fixture in fixtures:
            status = fixture.get("fixture", {}).get("status", {}).get("short", "")
            if status in {"CANC", "PST", "ABD"}:
                continue

            fixture_info = fixture.get("fixture", {})
            league = fixture.get("league", {})
            teams = fixture.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})
            status_and_score = self._extract_status_and_score(fixture)

            matches.append(
                {
                    "fixture_id": fixture_info.get("id"),
                    "kickoff": fixture_info.get("date"),
                    "league_id": league.get("id"),
                    "league": league.get("name", "Unknown League"),
                    "league_logo": league.get("logo") or "",
                    "country": league.get("country", ""),
                    "season": int(league.get("season") or match_date.year),
                    "home_team_id": home.get("id"),
                    "home_team": home.get("name", "Home"),
                    "home_team_logo": home.get("logo") or "",
                    "away_team_id": away.get("id"),
                    "away_team": away.get("name", "Away"),
                    "away_team_logo": away.get("logo") or "",
                    "status_short": status_and_score["status_short"],
                    "status_jogo": status_and_score["status_jogo"],
                    "home_goals": status_and_score["home_goals"],
                    "away_goals": status_and_score["away_goals"],
                }
            )

        return matches

    def get_team_recent_stats(self, team_id: int, league_id: int, season: int) -> Dict[str, object]:
        cache_key = (team_id, league_id, season)
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]

        if settings.use_sample_data:
            stats = self._sample_team_stats(team_id)
            self._stats_cache[cache_key] = stats
            return stats
        if not settings.api_football_keys:
            raise RuntimeError(
                "API_FOOTBALL_KEY nao configurada. "
                "Defina a variavel de ambiente ou use USE_SAMPLE_DATA=true."
            )

        fixtures, stats_meta = self._fetch_recent_team_fixtures(
            team_id=team_id,
            league_id=league_id,
            season=season,
        )

        goals_for: List[int] = []
        goals_against: List[int] = []
        for fixture in fixtures:
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            home_team_id = teams.get("home", {}).get("id")

            if home_team_id == team_id:
                scored = goals.get("home")
                conceded = goals.get("away")
            else:
                scored = goals.get("away")
                conceded = goals.get("home")

            if scored is None or conceded is None:
                continue

            goals_for.append(int(scored))
            goals_against.append(int(conceded))

        if not goals_for:
            stats = self._sample_team_stats(team_id)
            stats.update(stats_meta)
            stats["stats_source_note"] = f"{stats.get('stats_source_note')}_fallback_sample_stats"
        else:
            stats = {
                "avg_goals_for": sum(goals_for) / len(goals_for),
                "avg_goals_against": sum(goals_against) / len(goals_against),
                "matches_count": float(len(goals_for)),
            }
            stats.update(stats_meta)

        self._stats_cache[cache_key] = stats
        return stats

    def _fetch_recent_team_fixtures(
        self,
        team_id: int,
        league_id: int,
        season: int,
    ) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
        attempts: List[Tuple[Dict[str, object], Dict[str, object]]] = []
        attempts.append(
            (
                {
                    "team": team_id,
                    "league": league_id,
                    "season": season,
                    "status": "FT",
                    "last": 10,
                },
                {
                    "stats_source_season": season,
                    "stats_source_scope": "league",
                    "stats_source_query": "last",
                    "stats_source_note": "temporada_atual_last10",
                },
            )
        )

        seen = {season}
        for candidate_season in self._season_candidates(season):
            if candidate_season in seen:
                continue
            seen.add(candidate_season)
            note = "temporada_atual_completa" if candidate_season == season else "fallback_temporada_anterior"
            attempts.append(
                (
                    {
                        "team": team_id,
                        "league": league_id,
                        "season": candidate_season,
                        "status": "FT",
                    },
                    {
                        "stats_source_season": candidate_season,
                        "stats_source_scope": "league",
                        "stats_source_query": "season_full",
                        "stats_source_note": note,
                    },
                )
            )

        # Last-resort fallback when league filters are unavailable in a free plan.
        for candidate_season in self._season_candidates(season):
            attempts.append(
                (
                    {
                        "team": team_id,
                        "season": candidate_season,
                        "status": "FT",
                    },
                    {
                        "stats_source_season": candidate_season,
                        "stats_source_scope": "team_all_competitions",
                        "stats_source_query": "season_full",
                        "stats_source_note": "fallback_sem_filtro_de_liga",
                    },
                )
            )

        first_exception: Exception | None = None
        first_api_error: str | None = None

        for params, meta in attempts:
            try:
                payload = self._request("/fixtures", params)
            except ProxyError as exc:
                raise RuntimeError(
                    "Falha de proxy ao acessar API-Football. "
                    "Defina REQUESTS_TRUST_ENV=false para ignorar proxies do sistema "
                    "ou corrija HTTP_PROXY/HTTPS_PROXY."
                ) from exc
            except Exception as exc:
                if first_exception is None:
                    first_exception = exc
                continue

            api_error = self._payload_error_text(payload)
            if api_error:
                if first_api_error is None:
                    first_api_error = api_error
                continue

            fixtures = payload.get("response", [])
            if not isinstance(fixtures, list) or not fixtures:
                continue

            fixtures_sorted = sorted(
                fixtures,
                key=lambda item: str(item.get("fixture", {}).get("date", "")),
                reverse=True,
            )
            return fixtures_sorted[:10], meta

        if first_exception is not None:
            raise RuntimeError(
                f"Falha ao buscar estatisticas do time {team_id} na API-Football."
            ) from first_exception

        if first_api_error:
            return [], {
                "stats_source_season": None,
                "stats_source_scope": "unavailable",
                "stats_source_query": "none",
                "stats_source_note": "sem_acesso_plano_api",
                "stats_source_error": first_api_error,
            }

        return [], {
            "stats_source_season": None,
            "stats_source_scope": "unknown",
            "stats_source_query": "none",
            "stats_source_note": "sem_dados",
        }

    def _season_candidates(self, season: int) -> List[int]:
        current_year = datetime.now().year
        start = min(season, current_year)
        hard_cap = max(2018, settings.api_football_free_plan_max_season - 3)

        candidates: List[int] = []
        for value in range(start, hard_cap - 1, -1):
            if value not in candidates:
                candidates.append(value)

        preferred_free = settings.api_football_free_plan_max_season
        if preferred_free not in candidates:
            candidates.append(preferred_free)

        return candidates

    @staticmethod
    def _payload_error_text(payload: Dict[str, object]) -> str:
        errors = payload.get("errors", {})
        if isinstance(errors, dict):
            parts = [str(value).strip() for value in errors.values() if str(value).strip()]
            return " | ".join(parts)
        if isinstance(errors, list):
            parts = [str(value).strip() for value in errors if str(value).strip()]
            return " | ".join(parts)
        if isinstance(errors, str):
            return errors.strip()
        return ""

    def get_fixtures_status(
        self,
        fixture_ids: List[int],
    ) -> Dict[int, Dict[str, object]]:
        """Fetch latest status and score for given fixture ids."""
        if settings.use_sample_data or not settings.api_football_keys:
            return {}

        status_by_fixture: Dict[int, Dict[str, object]] = {}
        for fixture_id in sorted({int(item) for item in fixture_ids if item is not None}):
            try:
                payload = self._request("/fixtures", {"id": fixture_id, "timezone": settings.timezone})
                fixtures = payload.get("response", [])
                if not fixtures:
                    continue
                status_by_fixture[fixture_id] = self._extract_status_and_score(fixtures[0])
            except Exception:
                continue

        return status_by_fixture

    @staticmethod
    def _sample_matches(match_date: date) -> List[Dict[str, object]]:
        kickoff = datetime.combine(match_date, datetime.min.time()).isoformat()
        return [
            {
                "fixture_id": 900001,
                "kickoff": kickoff,
                "league_id": 71,
                "league": "Serie A",
                "league_logo": "",
                "country": "Italy",
                "season": match_date.year,
                "home_team_id": 505,
                "home_team": "Inter",
                "home_team_logo": "",
                "away_team_id": 867,
                "away_team": "Lecce",
                "away_team_logo": "",
                "status_short": "NS",
                "status_jogo": "Not Started",
                "home_goals": None,
                "away_goals": None,
            },
            {
                "fixture_id": 900002,
                "kickoff": kickoff,
                "league_id": 140,
                "league": "La Liga",
                "league_logo": "",
                "country": "Spain",
                "season": match_date.year,
                "home_team_id": 541,
                "home_team": "Real Madrid",
                "home_team_logo": "",
                "away_team_id": 546,
                "away_team": "Getafe",
                "away_team_logo": "",
                "status_short": "NS",
                "status_jogo": "Not Started",
                "home_goals": None,
                "away_goals": None,
            },
        ]

    @staticmethod
    def _sample_team_stats(team_id: int) -> Dict[str, object]:
        pseudo = (team_id % 10) / 100
        return {
            "avg_goals_for": 1.35 + pseudo,
            "avg_goals_against": 1.10 - (pseudo / 2),
            "matches_count": 10.0,
            "stats_source_season": None,
            "stats_source_scope": "sample",
            "stats_source_query": "sample",
            "stats_source_note": "dados_exemplo",
        }
