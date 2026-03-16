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
    _BOOKMAKER_HOMEPAGES = {
        "bet365": "https://www.bet365.com/",
        "betfairexeu": "https://www.betfair.com/exchange/plus/pt/futebol-betting-1",
        "betfairsbuk": "https://www.betfair.com/sport/football",
        "betfair": "https://www.betfair.com/",
        "betnacional": "https://www.betnacional.com/",
        "betway": "https://betway.com/",
        "onexbet": "https://1xbet.com/",
        "novibet": "https://www.novibet.com/",
        "pinnacle": "https://www.pinnacle.com/",
        "sportingbet": "https://www.sportingbet.com/",
    }
    _BOOKMAKER_LOGOS = {
        "bet365": "https://www.google.com/s2/favicons?domain=bet365.com&sz=64",
        "betfair": "https://www.google.com/s2/favicons?domain=betfair.com&sz=64",
        "betfairexeu": "https://www.google.com/s2/favicons?domain=betfair.com&sz=64",
        "betfairsbuk": "https://www.google.com/s2/favicons?domain=betfair.com&sz=64",
        "betnacional": "https://www.google.com/s2/favicons?domain=betnacional.com&sz=64",
        "betway": "https://www.google.com/s2/favicons?domain=betway.com&sz=64",
        "bodog": "https://www.google.com/s2/favicons?domain=bodog.com&sz=64",
        "esportivabet": "https://www.google.com/s2/favicons?domain=esportivabet.com&sz=64",
        "estrelabet": "https://www.google.com/s2/favicons?domain=estrelabet.com&sz=64",
        "galerabet": "https://www.google.com/s2/favicons?domain=galera.bet&sz=64",
        "kto": "https://www.google.com/s2/favicons?domain=kto.bet.br&sz=64",
        "novibet": "https://www.google.com/s2/favicons?domain=novibet.com&sz=64",
        "onexbet": "https://www.google.com/s2/favicons?domain=1xbet.com&sz=64",
        "parimatch": "https://www.google.com/s2/favicons?domain=parimatch.com&sz=64",
        "pinnacle": "https://www.google.com/s2/favicons?domain=pinnacle.com&sz=64",
        "pixbet": "https://www.google.com/s2/favicons?domain=pixbet.com&sz=64",
        "sportingbet": "https://www.google.com/s2/favicons?domain=sportingbet.com&sz=64",
    }
    _BOOKMAKER_DISPLAY_BY_KEY = {
        "1xbet": "1xBet",
        "apostaganha": "Aposta Ganha",
        "aposta_ganha": "Aposta Ganha",
        "bet365": "Bet365",
        "bet365au": "Bet365",
        "betano": "Betano",
        "betfair": "Betfair",
        "betfairexeu": "Betfair",
        "betfairsbuk": "Betfair",
        "betnacional": "Betnacional",
        "betway": "Betway",
        "bodog": "Bodog",
        "esportivabet": "EsportivaBet",
        "estrelabet": "EstrelaBet",
        "galera": "Galera.bet",
        "galerabet": "Galera.bet",
        "kto": "KTO",
        "novibet": "Novibet",
        "onexbet": "1xBet",
        "parimatch": "Parimatch",
        "pinnacle": "Pinnacle",
        "pixbet": "Pixbet",
        "sportingbet": "Sportingbet",
    }
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
        self._market_sources_by_match: Dict[str, Dict[str, List[Dict[str, object]]]] = {}
        self._bookmaker_run_presence: Dict[str, int] = {}

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

    def _request_sport_odds(
        self,
        sport_key: str,
        markets: str,
        bookmakers: str = "",
    ) -> List[Dict[str, object]]:
        url = f"{self.base_url}/sports/{sport_key}/odds"
        params = {
            "apiKey": settings.the_odds_api_key,
            "regions": settings.the_odds_regions,
            "markets": markets,
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        if bookmakers:
            params["bookmakers"] = bookmakers

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
            scope = f"markets={markets}"
            if bookmakers:
                scope += f", bookmakers={bookmakers}"
            raise RuntimeError(f"{sport_key} HTTP {response.status_code} ({scope}): {detail}")

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

    @staticmethod
    def _normalize_bookmaker_name(value: object) -> str:
        return str(value or "").strip() or "Casa desconhecida"

    @classmethod
    def _normalize_bookmaker_key(cls, value: object) -> str:
        return "".join(char for char in str(value or "").strip().lower() if char.isalnum())

    @classmethod
    def _display_name_for_bookmaker(cls, raw_name: object) -> str:
        normalized_key = cls._normalize_bookmaker_key(raw_name)
        return cls._BOOKMAKER_DISPLAY_BY_KEY.get(normalized_key, cls._normalize_bookmaker_name(raw_name))

    @staticmethod
    def _preferred_bookmakers() -> List[str]:
        preferred: List[str] = []
        for item in getattr(settings, "odds_preferred_bookmakers", []) or []:
            value = str(item or "").strip()
            if value and value not in preferred:
                preferred.append(value)
        return preferred

    @classmethod
    def _relevant_bookmaker_keys(cls) -> set[str]:
        relevant: set[str] = set()
        for item in getattr(settings, "odds_relevant_bookmakers", []) or []:
            normalized = cls._normalize_bookmaker_key(item)
            if normalized:
                relevant.add(normalized)
        return relevant

    @staticmethod
    def _safe_float(value: object) -> float | None:
        try:
            result = float(value)
        except Exception:
            return None
        return result if result > 0 else None

    def _merge_market_sources(
        self,
        match_key: str,
        market_sources: Dict[str, List[Dict[str, object]]],
    ) -> None:
        target = self._market_sources_by_match.setdefault(match_key, {})
        for market_key, entries in market_sources.items():
            if not isinstance(entries, list) or not entries:
                continue
            bucket = target.setdefault(market_key, [])
            for entry in entries:
                if isinstance(entry, dict):
                    bucket.append(dict(entry))

    def _finalize_market_sources(self) -> None:
        finalized: Dict[str, Dict[str, List[Dict[str, object]]]] = {}
        for match_key, market_map in self._market_sources_by_match.items():
            finalized[match_key] = {}
            for market_key, entries in market_map.items():
                ranked = self._select_top_bookmakers(entries)
                if ranked:
                    finalized[match_key][market_key] = ranked
        self._market_sources_by_match = finalized

    def _select_top_bookmakers(
        self,
        entries: List[Dict[str, object]],
    ) -> List[Dict[str, object]]:
        relevant_keys = self._relevant_bookmaker_keys()
        best_by_name: Dict[str, Dict[str, object]] = {}
        for entry in entries:
            name = self._normalize_bookmaker_name(entry.get("name"))
            normalized_name = self._normalize_bookmaker_key(name)
            odd = self._safe_float(entry.get("odd"))
            if odd is None:
                continue
            coverage = int(entry.get("coverage") or 0)
            current = best_by_name.get(name)
            candidate = {
                "name": name,
                "odd": round(odd, 3),
                "coverage": coverage,
                "presence": self._bookmaker_run_presence.get(name, 0),
                "url": self._BOOKMAKER_HOMEPAGES.get(self._normalize_bookmaker_key(name)),
                "logo_url": self._BOOKMAKER_LOGOS.get(self._normalize_bookmaker_key(name)),
                "is_relevant": normalized_name in relevant_keys,
            }
            if current is None:
                best_by_name[name] = candidate
                continue
            if odd > float(current.get("odd") or 0):
                best_by_name[name] = candidate
                continue
            if abs(odd - float(current.get("odd") or 0)) < 1e-9 and coverage > int(current.get("coverage") or 0):
                best_by_name[name] = candidate

        if not best_by_name:
            return []

        ranked = list(best_by_name.values())
        if any(bool(item.get("is_relevant")) for item in ranked):
            ranked = [item for item in ranked if bool(item.get("is_relevant"))]
        ranked.sort(
            key=lambda item: (
                -float(item.get("odd") or 0),
                -int(item.get("coverage") or 0),
                -int(item.get("presence") or 0),
                str(item.get("name") or "").lower(),
            )
        )
        return [
            {
                "name": item["name"],
                "odd": item["odd"],
                "url": item.get("url"),
                "logo_url": item.get("logo_url"),
            }
            for item in ranked[:3]
        ]

    def get_best_bookmakers_for_match(
        self,
        match_key: str,
        market_key: str,
    ) -> List[Dict[str, object]]:
        return list(self._market_sources_by_match.get(match_key, {}).get(market_key, []))

    def _available_sports(self) -> set[str]:
        if self._available_sports_cache is not None:
            return self._available_sports_cache

        try:
            self._available_sports_cache = self.ensure_service_available()
            return self._available_sports_cache
        except Exception:
            self._available_sports_cache = set()
            return self._available_sports_cache

    def ensure_service_available(self) -> set[str]:
        if settings.use_sample_data:
            available = {item for item in settings.odds_sports if item}
            self._available_sports_cache = available
            return available
        if not settings.the_odds_api_key:
            raise RuntimeError(
                "THE_ODDS_API_KEY nao configurada. "
                "Defina a variavel de ambiente ou use USE_SAMPLE_DATA=true."
            )

        url = f"{self.base_url}/sports"
        params = {"apiKey": settings.the_odds_api_key}
        try:
            response = self.session.get(url, params=params, timeout=settings.request_timeout_seconds)
        except ProxyError as exc:
            raise RuntimeError(
                "The Odds API indisponivel por proxy. "
                "Defina REQUESTS_TRUST_ENV=false ou corrija HTTP_PROXY/HTTPS_PROXY."
            ) from exc
        except requests.RequestException as exc:
            raise RuntimeError(
                f"The Odds API indisponivel no pre-check. Detalhes: {exc}"
            ) from exc

        if response.status_code >= 400:
            detail = self._response_detail(response)
            if self._is_out_of_credits_error(detail):
                raise RuntimeError(
                    "The Odds API sem creditos (OUT_OF_USAGE_CREDITS). "
                    "Atualize a chave/plano ou aguarde renovacao da cota."
                )
            raise RuntimeError(
                "The Odds API indisponivel no pre-check. "
                f"HTTP {response.status_code}: {detail}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("The Odds API retornou JSON invalido no pre-check.") from exc

        if not isinstance(payload, list):
            raise RuntimeError(
                f"The Odds API retornou payload inesperado no pre-check: {type(payload).__name__}"
            )

        keys = {str(item.get("key", "")).strip() for item in payload if isinstance(item, dict)}
        self._available_sports_cache = {key for key in keys if key}
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
        self._market_sources_by_match = {}
        self._bookmaker_run_presence = {}
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
        preferred_bookmakers = ",".join(self._preferred_bookmakers())
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
                request_variants = [preferred_bookmakers] if preferred_bookmakers else [""]
                if preferred_bookmakers:
                    request_variants.append("")

                for bookmakers in request_variants:
                    try:
                        events = self._request_sport_odds(sport_key, markets, bookmakers=bookmakers)
                        has_success_response = True
                        break
                    except RuntimeError as exc:
                        error_text = str(exc)
                        errors.append(error_text)
                        if self._is_out_of_credits_error(error_text):
                            raise RuntimeError(
                                "The Odds API sem creditos (OUT_OF_USAGE_CREDITS). "
                                "Atualize a chave/plano ou aguarde renovacao da cota."
                            ) from exc
                        continue
                if events is not None:
                    break

            if events is None:
                continue

            for event in events:
                home_team = str(event.get("home_team", ""))
                away_team = str(event.get("away_team", ""))
                key = build_match_key(home_team, away_team)
                if key not in requested_keys:
                    continue

                extracted, market_sources = self._extract_best_markets(event)
                self._merge_market_sources(key, market_sources)
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
            self._market_sources_by_match.setdefault(key, {})

        self._finalize_market_sources()
        return consolidated

    def _extract_best_markets(
        self,
        event: Dict[str, object],
    ) -> tuple[Dict[str, float], Dict[str, List[Dict[str, object]]]]:
        odds: Dict[str, float] = {}
        market_sources: Dict[str, List[Dict[str, object]]] = {}
        home_team = str(event.get("home_team", ""))
        away_team = str(event.get("away_team", ""))
        event_presence: set[str] = set()

        for bookmaker in event.get("bookmakers", []):
            bookmaker_name = self._normalize_bookmaker_name(
                bookmaker.get("title") or bookmaker.get("key") or bookmaker.get("name")
            )
            bookmaker_name = self._display_name_for_bookmaker(bookmaker_name)
            bookmaker_odds: Dict[str, float] = {}
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                outcomes = market.get("outcomes", [])

                if market_key == "totals":
                    for outcome in outcomes:
                        point = outcome.get("point")
                        name = str(outcome.get("name", "")).lower()
                        price = self._safe_float(outcome.get("price"))
                        if price is None:
                            continue
                        if point == 1.5 and name == "over":
                            bookmaker_odds["over_1_5"] = max(bookmaker_odds.get("over_1_5", 0), price)
                        if point == 2.5 and name == "over":
                            bookmaker_odds["over_2_5"] = max(bookmaker_odds.get("over_2_5", 0), price)
                        if point == 3.5 and name == "under":
                            bookmaker_odds["under_3_5"] = max(bookmaker_odds.get("under_3_5", 0), price)

                if market_key == "btts":
                    for outcome in outcomes:
                        name = str(outcome.get("name", "")).lower()
                        price = self._safe_float(outcome.get("price"))
                        if price is None:
                            continue
                        if "yes" in name:
                            bookmaker_odds["btts_yes"] = max(bookmaker_odds.get("btts_yes", 0), price)

                if market_key == "h2h":
                    for outcome in outcomes:
                        name = str(outcome.get("name", ""))
                        price = self._safe_float(outcome.get("price"))
                        if price is None:
                            continue
                        if name == home_team:
                            bookmaker_odds["home_win"] = max(bookmaker_odds.get("home_win", 0), price)
                        elif name == away_team:
                            bookmaker_odds["away_win"] = max(bookmaker_odds.get("away_win", 0), price)
                        elif name.lower() == "draw":
                            bookmaker_odds["draw"] = max(bookmaker_odds.get("draw", 0), price)

            self._append_double_chance_odds(bookmaker_odds)
            if not bookmaker_odds:
                continue

            event_presence.add(bookmaker_name)
            coverage = len(bookmaker_odds)
            for normalized_market, price in bookmaker_odds.items():
                odds[normalized_market] = max(odds.get(normalized_market, 0), price)
                market_sources.setdefault(normalized_market, []).append(
                    {
                        "name": bookmaker_name,
                        "odd": round(price, 3),
                        "coverage": coverage,
                    }
                )

        for bookmaker_name in event_presence:
            self._bookmaker_run_presence[bookmaker_name] = self._bookmaker_run_presence.get(bookmaker_name, 0) + 1

        return odds, market_sources

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
        consolidated: Dict[str, Dict[str, float]] = {}
        self._market_sources_by_match = {}
        self._bookmaker_run_presence = {}
        for match in matches:
            match_key = build_match_key(match["home_team"], match["away_team"])
            odds, sources = self._sample_odds_for_match(match)
            consolidated[match_key] = odds
            self._merge_market_sources(match_key, sources)
            bookmaker_names = {
                self._normalize_bookmaker_name(entry.get("name"))
                for entries in sources.values()
                for entry in entries
                if isinstance(entry, dict)
            }
            for bookmaker_name in bookmaker_names:
                self._bookmaker_run_presence[bookmaker_name] = self._bookmaker_run_presence.get(bookmaker_name, 0) + 1

        self._finalize_market_sources()
        return consolidated

    @staticmethod
    def _sample_odds_for_match(
        match: Dict[str, object],
    ) -> tuple[Dict[str, float], Dict[str, List[Dict[str, object]]]]:
        team_factor = ((int(match["home_team_id"]) + int(match["away_team_id"])) % 5) / 100
        sample_bookmakers = {
            "Pinnacle": {
                "over_1_5": 1.32 + team_factor,
                "over_2_5": 1.71 + team_factor,
                "under_3_5": 1.42 + team_factor,
                "btts_yes": 1.88 + team_factor,
                "home_win": 1.76 + team_factor,
                "draw": 3.45 + team_factor,
                "away_win": 4.30 + team_factor,
            },
            "Betfair": {
                "over_1_5": 1.31 + team_factor,
                "over_2_5": 1.70 + team_factor,
                "under_3_5": 1.41 + team_factor,
                "btts_yes": 1.87 + team_factor,
                "home_win": 1.75 + team_factor,
                "draw": 3.44 + team_factor,
                "away_win": 4.28 + team_factor,
            },
            "Betway": {
                "over_1_5": 1.32 + team_factor,
                "over_2_5": 1.68 + team_factor,
                "under_3_5": 1.40 + team_factor,
                "btts_yes": 1.84 + team_factor,
                "home_win": 1.74 + team_factor,
                "draw": 3.40 + team_factor,
                "away_win": 4.25 + team_factor,
            },
            "1xBet": {
                "over_1_5": 1.32 + team_factor,
                "over_2_5": 1.70 + team_factor,
                "under_3_5": 1.39 + team_factor,
                "btts_yes": 1.85 + team_factor,
                "home_win": 1.73 + team_factor,
                "draw": 3.39 + team_factor,
                "away_win": 4.22 + team_factor,
            },
            "Betnacional": {
                "over_1_5": 1.30 + team_factor,
                "over_2_5": 1.67 + team_factor,
                "under_3_5": 1.38 + team_factor,
                "btts_yes": 1.82 + team_factor,
                "home_win": 1.72 + team_factor,
                "draw": 3.31 + team_factor,
                "away_win": 4.12 + team_factor,
            },
        }
        odds: Dict[str, float] = {}
        market_sources: Dict[str, List[Dict[str, object]]] = {}

        for bookmaker_name, bookmaker_odds in sample_bookmakers.items():
            normalized = dict(bookmaker_odds)
            OddsAPI._append_double_chance_odds(normalized)
            coverage = len(normalized)
            for market_key, price in normalized.items():
                odds[market_key] = max(odds.get(market_key, 0), price)
                market_sources.setdefault(market_key, []).append(
                    {
                        "name": bookmaker_name,
                        "odd": round(float(price), 3),
                        "coverage": coverage,
                    }
                )

        return odds, market_sources
