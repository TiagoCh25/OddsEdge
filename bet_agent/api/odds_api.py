"""Client for The Odds API and market normalization."""

from __future__ import annotations

import time
import unicodedata
from typing import Dict, List, Optional

import requests
from requests.exceptions import ProxyError

from app.config import settings


def normalize_team_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.lower())
    return "".join(char for char in normalized if char.isalnum())


def build_match_key(home_team: str, away_team: str) -> str:
    return f"{normalize_team_name(home_team)}__{normalize_team_name(away_team)}"


class OddsAPI:
    _RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    _MAX_RETRIES = 2
    _LEAGUE_ID_TO_SPORT_KEY = {
        39: "soccer_epl",
        140: "soccer_spain_la_liga",
        135: "soccer_italy_serie_a",
        78: "soccer_germany_bundesliga",
        61: "soccer_france_ligue_one",
        71: "soccer_brazil_campeonato",
    }

    def __init__(self) -> None:
        self.base_url = settings.the_odds_base_url.rstrip("/")
        self.session = requests.Session()
        self.session.trust_env = settings.requests_trust_env
        self._available_sports_cache: Optional[set[str]] = None

    @staticmethod
    def _response_detail(response: requests.Response) -> str:
        body = (response.text or "").strip().replace("\n", " ")
        if len(body) > 220:
            body = body[:220] + "..."
        return body or "no response body"

    @staticmethod
    def _normalize_markets(markets: str) -> str:
        tokens = [token.strip().lower() for token in (markets or "").split(",") if token.strip()]
        deduped: List[str] = []
        for token in tokens:
            if token not in deduped:
                deduped.append(token)
        return ",".join(deduped)

    @staticmethod
    def _retry_wait_seconds(response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.5, float(retry_after))
            except ValueError:
                pass
        return 1.4 * (attempt + 1)

    def _request_sport_odds(self, sport_key: str, markets: str) -> List[Dict[str, object]]:
        url = f"{self.base_url}/sports/{sport_key}/odds"
        params = {
            "apiKey": settings.the_odds_api_key,
            "regions": settings.the_odds_regions,
            "markets": markets,
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }

        response: Optional[requests.Response] = None
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                response = self.session.get(url, params=params, timeout=settings.request_timeout_seconds)
            except ProxyError as exc:
                raise RuntimeError(
                    f"{sport_key} proxy error: defina REQUESTS_TRUST_ENV=false "
                    "ou corrija HTTP_PROXY/HTTPS_PROXY."
                ) from exc
            except requests.RequestException as exc:
                if attempt < self._MAX_RETRIES:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                raise RuntimeError(f"{sport_key} request error: {exc}") from exc

            if response.status_code in self._RETRIABLE_STATUS_CODES and attempt < self._MAX_RETRIES:
                time.sleep(self._retry_wait_seconds(response, attempt))
                continue
            break

        if response is None:
            raise RuntimeError(f"{sport_key} request error: no response")

        if response.status_code >= 400:
            detail = self._response_detail(response)
            raise RuntimeError(f"{sport_key} HTTP {response.status_code} (markets={markets}): {detail}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(f"{sport_key} returned invalid JSON") from exc

        if not isinstance(payload, list):
            raise RuntimeError(f"{sport_key} returned unexpected payload type: {type(payload).__name__}")

        return payload

    @staticmethod
    def _is_out_of_credits_error(message: str) -> bool:
        text = str(message or "").upper()
        return ("OUT_OF_USAGE_CREDITS" in text) or ("USAGE QUOTA HAS BEEN REACHED" in text)

    @staticmethod
    def _normalize_text(value: object) -> str:
        return str(value or "").strip().lower()

    def _available_sports(self) -> set[str]:
        if self._available_sports_cache is not None:
            return self._available_sports_cache

        url = f"{self.base_url}/sports"
        params = {"apiKey": settings.the_odds_api_key}
        try:
            response = self.session.get(url, params=params, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                keys = {str(item.get("key", "")).strip() for item in payload if isinstance(item, dict)}
                self._available_sports_cache = {key for key in keys if key}
                return self._available_sports_cache
        except Exception:
            pass

        self._available_sports_cache = set()
        return self._available_sports_cache

    def _guess_sport_key(self, match: Dict[str, object]) -> str | None:
        league_id = match.get("league_id")
        try:
            league_id_int = int(league_id) if league_id is not None else None
        except Exception:
            league_id_int = None

        if league_id_int in self._LEAGUE_ID_TO_SPORT_KEY:
            return self._LEAGUE_ID_TO_SPORT_KEY[league_id_int]

        country = self._normalize_text(match.get("country"))
        league = self._normalize_text(match.get("league"))

        if country == "england" and "premier" in league:
            return "soccer_epl"
        if country == "england" and "fa cup" in league:
            return "soccer_fa_cup"
        if country == "spain" and "liga" in league:
            return "soccer_spain_la_liga"
        if country == "italy" and "serie a" in league:
            return "soccer_italy_serie_a"
        if country == "germany" and "bundesliga" in league:
            return "soccer_germany_bundesliga"
        if country == "france" and "ligue 1" in league:
            return "soccer_france_ligue_one"
        if country == "portugal" and ("primeira liga" in league or "liga portugal" in league):
            return "soccer_portugal_primeira_liga"
        if country == "argentina" and ("primera division" in league or "liga profesional" in league):
            return "soccer_argentina_primera_division"
        if country == "mexico" and ("liga mx" in league or "ligamx" in league):
            return "soccer_mexico_ligamx"
        if country == "chile" and "campeonato" in league:
            return "soccer_chile_campeonato"
        if country in {"turkey", "turkiye"} and ("super lig" in league or "süper lig" in league):
            return "soccer_turkey_super_league"
        if country in {"netherlands", "holland"} and "eredivisie" in league:
            return "soccer_netherlands_eredivisie"
        if country == "brazil" and ("serie a" in league or "campeonato" in league):
            return "soccer_brazil_campeonato"
        if country == "brazil" and "copa do brasil" in league:
            return "soccer_brazil_copa_do_brasil"
        if "libertadores" in league:
            return "soccer_conmebol_libertadores"
        if "sudamericana" in league:
            return "soccer_conmebol_sudamericana"
        if "champions league" in league:
            return "soccer_uefa_champs_league"
        if "europa league" in league:
            return "soccer_uefa_europa_league"
        if "europa conference" in league:
            return "soccer_uefa_europa_conference_league"
        if "world cup" in league:
            return "soccer_fifa_world_cup"
        return None

    def _select_sports_for_run(self, matches: List[Dict[str, object]]) -> List[str]:
        configured_sports = [item for item in settings.odds_sports if item]
        available = self._available_sports()
        if available:
            configured_sports = [item for item in configured_sports if item in available]
        if not configured_sports:
            return []

        selected = list(configured_sports)
        ranked_counts: Dict[str, int] = {}

        if settings.odds_only_active_sports:
            for match in matches:
                key = self._guess_sport_key(match)
                if key and key in configured_sports:
                    ranked_counts[key] = ranked_counts.get(key, 0) + 1
            if ranked_counts:
                selected = self._prioritize_active_sports(ranked_counts, configured_sports)
            else:
                selected = self._prioritize_configured_sports(configured_sports)

            dynamic_top_n = max(0, int(settings.odds_dynamic_top_n))
            if dynamic_top_n > 0 and len(selected) > dynamic_top_n:
                selected = selected[:dynamic_top_n]

        max_sports = max(0, int(settings.odds_max_sports_per_run))
        if max_sports > 0:
            selected = selected[:max_sports]

        # Final dedupe safety.
        unique: List[str] = []
        for sport in selected:
            if sport not in unique:
                unique.append(sport)
        return unique

    def _prioritize_active_sports(
        self,
        ranked_counts: Dict[str, int],
        configured_sports: List[str],
    ) -> List[str]:
        selected: List[str] = []
        allowed = set(configured_sports)

        for sport in settings.odds_priority_sports:
            if sport in ranked_counts and sport in allowed and sport not in selected:
                selected.append(sport)

        remaining = [sport for sport in ranked_counts.keys() if sport not in selected and sport in allowed]
        remaining.sort(key=lambda sport: (ranked_counts[sport], sport), reverse=True)
        selected.extend(remaining)
        return selected

    def _prioritize_configured_sports(self, configured_sports: List[str]) -> List[str]:
        selected: List[str] = []
        allowed = set(configured_sports)

        for sport in settings.odds_priority_sports:
            if sport in allowed and sport not in selected:
                selected.append(sport)

        for sport in configured_sports:
            if sport not in selected:
                selected.append(sport)
        return selected

    def get_odds_for_matches(self, matches: List[Dict[str, object]]) -> Dict[str, Dict[str, float]]:
        if settings.use_sample_data:
            return self._sample_odds(matches)
        if not matches:
            return {}
        if not settings.the_odds_api_key:
            raise RuntimeError(
                "THE_ODDS_API_KEY nao configurada. "
                "Defina a variavel de ambiente ou use USE_SAMPLE_DATA=true."
            )

        requested_keys = {build_match_key(m["home_team"], m["away_team"]) for m in matches}
        consolidated: Dict[str, Dict[str, float]] = {}

        configured_markets = self._normalize_markets(settings.the_odds_markets)
        if not configured_markets:
            configured_markets = "h2h,totals"
        fallback_markets = "h2h,totals"
        errors: List[str] = []
        has_success_response = False

        sport_keys = self._select_sports_for_run(matches)
        if not sport_keys:
            raise RuntimeError(
                "Nenhuma liga configurada para buscar odds. Defina ODDS_SPORTS no ambiente."
            )

        for sport_key in sport_keys:
            events: Optional[List[Dict[str, object]]] = None
            market_attempts = [configured_markets]
            if "btts" in configured_markets.split(","):
                no_btts = ",".join(item for item in configured_markets.split(",") if item != "btts")
                if no_btts and no_btts not in market_attempts:
                    market_attempts.append(no_btts)
            if configured_markets != fallback_markets:
                market_attempts.append(fallback_markets)

            for markets in market_attempts:
                try:
                    events = self._request_sport_odds(sport_key, markets)
                    has_success_response = True
                    break
                except RuntimeError as exc:
                    error_text = str(exc)
                    errors.append(error_text)
                    # Quota exhausted is non-recoverable for current key; stop early.
                    if self._is_out_of_credits_error(error_text):
                        raise RuntimeError(
                            "The Odds API sem creditos (OUT_OF_USAGE_CREDITS). "
                            "Atualize a chave/plano ou aguarde renovacao da cota."
                        ) from exc
                    continue

            if events is None:
                continue

            for event in events:
                home_team = str(event.get("home_team", ""))
                away_team = str(event.get("away_team", ""))
                key = build_match_key(home_team, away_team)
                if key not in requested_keys:
                    continue

                extracted = self._extract_best_markets(event)
                if key not in consolidated:
                    consolidated[key] = extracted
                    continue

                existing = consolidated[key]
                for market_key, market_odd in extracted.items():
                    existing[market_key] = max(float(existing.get(market_key, 0)), float(market_odd))

        if not has_success_response:
            error_block = " | ".join(errors[:4]) if errors else "unknown error"
            raise RuntimeError(
                "Falha ao buscar odds na The Odds API. "
                f"Detalhes: {error_block}"
            )

        for match in matches:
            key = build_match_key(match["home_team"], match["away_team"])
            consolidated.setdefault(key, {})

        return consolidated

    def _extract_best_markets(self, event: Dict[str, object]) -> Dict[str, float]:
        odds: Dict[str, float] = {}
        home_team = str(event.get("home_team", ""))
        away_team = str(event.get("away_team", ""))

        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                outcomes = market.get("outcomes", [])

                if market_key == "totals":
                    for outcome in outcomes:
                        point = outcome.get("point")
                        name = str(outcome.get("name", "")).lower()
                        price = float(outcome.get("price", 0))
                        if point == 1.5 and name == "over":
                            odds["over_1_5"] = max(odds.get("over_1_5", 0), price)
                        if point == 2.5 and name == "over":
                            odds["over_2_5"] = max(odds.get("over_2_5", 0), price)
                        if point == 3.5 and name == "under":
                            odds["under_3_5"] = max(odds.get("under_3_5", 0), price)

                if market_key == "btts":
                    for outcome in outcomes:
                        name = str(outcome.get("name", "")).lower()
                        price = float(outcome.get("price", 0))
                        if "yes" in name:
                            odds["btts_yes"] = max(odds.get("btts_yes", 0), price)

                if market_key == "h2h":
                    for outcome in outcomes:
                        name = str(outcome.get("name", ""))
                        price = float(outcome.get("price", 0))
                        if name == home_team:
                            odds["home_win"] = max(odds.get("home_win", 0), price)
                        elif name == away_team:
                            odds["away_win"] = max(odds.get("away_win", 0), price)
                        elif name.lower() == "draw":
                            odds["draw"] = max(odds.get("draw", 0), price)

        self._append_double_chance_odds(odds)
        return odds

    @staticmethod
    def _append_double_chance_odds(odds: Dict[str, float]) -> None:
        home = odds.get("home_win")
        draw = odds.get("draw")
        away = odds.get("away_win")
        if not home or not draw or not away:
            return

        p_home = 1 / home
        p_draw = 1 / draw
        p_away = 1 / away

        odds["double_chance_1x"] = round(1 / max(p_home + p_draw, 1e-9), 3)
        odds["double_chance_x2"] = round(1 / max(p_draw + p_away, 1e-9), 3)
        odds["double_chance_12"] = round(1 / max(p_home + p_away, 1e-9), 3)

    def _sample_odds(self, matches: List[Dict[str, object]]) -> Dict[str, Dict[str, float]]:
        return {
            build_match_key(match["home_team"], match["away_team"]): self._sample_odds_for_match(match)
            for match in matches
        }

    @staticmethod
    def _sample_odds_for_match(match: Dict[str, object]) -> Dict[str, float]:
        team_factor = ((int(match["home_team_id"]) + int(match["away_team_id"])) % 5) / 100
        base = {
            "over_1_5": 1.32 + team_factor,
            "over_2_5": 1.70 + team_factor,
            "under_3_5": 1.42 + team_factor,
            "btts_yes": 1.86 + team_factor,
            "home_win": 1.75 + team_factor,
            "draw": 3.45 + team_factor,
            "away_win": 4.30 + team_factor,
        }
        OddsAPI._append_double_chance_odds(base)
        return base
