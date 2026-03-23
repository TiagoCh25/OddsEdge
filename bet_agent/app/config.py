import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

"""Centralized configuration for the project."""


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        value = value[1:-1]
    return key, value


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}

    values: dict[str, str] = {}
    for raw_line in lines:
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        values[key] = value
    return values


def _apply_env_values(
    values: dict[str, str],
    protected_keys: set[str],
    force_override_keys: set[str] | None = None,
) -> None:
    force_override_keys = force_override_keys or set()
    for key, value in values.items():
        if key in protected_keys and key not in force_override_keys:
            continue
        # Allow profile file values to override values loaded from another file.
        os.environ[key] = value


def _load_dotenv_profiles() -> None:
    """
    Load configuration files with precedence:
    1) existing process environment
    2) .env
    3) .env.<APP_ENV> (ex.: .env.local / .env.prd)
    """
    protected_keys = set(os.environ.keys())
    # Keep API keys in .env.<APP_ENV> as source of truth for local runs.
    local_secret_keys = {
        "API_FOOTBALL_KEY",
        "API_FOOTBALL_FALLBACK_KEYS",
        "THE_ODDS_API_KEY",
    }

    base_values = _load_env_file(PROJECT_ROOT / ".env")
    _apply_env_values(base_values, protected_keys)

    app_env = (os.getenv("APP_ENV", "local") or "local").strip().lower()
    profile_values = _load_env_file(PROJECT_ROOT / f".env.{app_env}")
    _apply_env_values(profile_values, protected_keys, force_override_keys=local_secret_keys)


_load_dotenv_profiles()


DEFAULT_ODDS_SPORTS: List[str] = [
    "soccer_fifa_world_cup",
    "soccer_brazil_campeonato",
    "soccer_brazil_copa_do_brasil",
    "soccer_conmebol_libertadores",
    "soccer_uefa_champs_league",
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga",
    "soccer_france_ligue_one",
    "soccer_portugal_primeira_liga",
    "soccer_netherlands_eredivisie",
    "soccer_argentina_primera_division",
    "soccer_mexico_ligamx",
    "soccer_usa_mls",
    "soccer_uefa_europa_league",
    "soccer_uefa_europa_conference_league",
    "soccer_efl_champ",
    "soccer_spain_segunda_division",
    "soccer_germany_bundesliga2",
    "soccer_italy_serie_b",
    "soccer_france_ligue_two",
    "soccer_brazil_serie_b",
    "soccer_fa_cup",
    "soccer_england_efl_cup",
    "soccer_germany_dfb_pokal",
    "soccer_france_coupe_de_france",
    "soccer_spain_copa_del_rey",
    "soccer_belgium_first_div",
    "soccer_chile_campeonato",
    "soccer_turkey_super_league",
    "soccer_greece_super_league",
    "soccer_switzerland_superleague",
    "soccer_denmark_superliga",
    "soccer_norway_eliteserien",
    "soccer_sweden_allsvenskan",
    "soccer_poland_ekstraklasa",
    "soccer_russia_premier_league",
    "soccer_austria_bundesliga",
    "soccer_spl",
    "soccer_china_superleague",
    "soccer_japan_j_league",
    "soccer_korea_kleague1",
    "soccer_australia_aleague",
    "soccer_saudi_arabia_pro_league",
    "soccer_england_league1",
    "soccer_england_league2",
    "soccer_germany_liga3",
    "soccer_league_of_ireland",
    "soccer_germany_bundesliga_women",
]

DEFAULT_ODDS_PRIORITY_SPORTS: List[str] = [
    "soccer_fifa_world_cup",
    "soccer_brazil_campeonato",
    "soccer_brazil_copa_do_brasil",
    "soccer_conmebol_libertadores",
    "soccer_uefa_champs_league",
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga",
    "soccer_france_ligue_one",
    "soccer_portugal_primeira_liga",
    "soccer_netherlands_eredivisie",
    "soccer_argentina_primera_division",
    "soccer_mexico_ligamx",
    "soccer_usa_mls",
    "soccer_uefa_europa_league",
    "soccer_uefa_europa_conference_league",
    "soccer_efl_champ",
    "soccer_spain_segunda_division",
    "soccer_germany_bundesliga2",
    "soccer_italy_serie_b",
    "soccer_france_ligue_two",
    "soccer_brazil_serie_b",
    "soccer_fa_cup",
    "soccer_england_efl_cup",
    "soccer_germany_dfb_pokal",
    "soccer_france_coupe_de_france",
    "soccer_spain_copa_del_rey",
    "soccer_belgium_first_div",
    "soccer_chile_campeonato",
    "soccer_turkey_super_league",
    "soccer_greece_super_league",
    "soccer_switzerland_superleague",
    "soccer_denmark_superliga",
    "soccer_norway_eliteserien",
    "soccer_sweden_allsvenskan",
    "soccer_poland_ekstraklasa",
    "soccer_russia_premier_league",
    "soccer_austria_bundesliga",
    "soccer_spl",
    "soccer_china_superleague",
    "soccer_japan_j_league",
    "soccer_korea_kleague1",
    "soccer_australia_aleague",
    "soccer_saudi_arabia_pro_league",
    "soccer_england_league1",
    "soccer_england_league2",
    "soccer_germany_liga3",
    "soccer_league_of_ireland",
    "soccer_germany_bundesliga_women",
]

DEFAULT_ODDS_PREFERRED_BOOKMAKERS: List[str] = [
    "pinnacle",
    "bet365_au",
    "betfair_ex_eu",
    "betfair_sb_uk",
    "betway",
    "onexbet",
]

DEFAULT_ODDS_RELEVANT_BOOKMAKERS: List[str] = [
    "pinnacle",
    "bet365",
    "betfair",
    "betano",
    "sportingbet",
    "betway",
    "novibet",
    "1xbet",
    "onexbet",
    "parimatch",
    "kto",
    "pixbet",
    "estrelabet",
    "betnacional",
    "aposta ganha",
    "apostaganha",
    "bodog",
    "galera.bet",
    "galerabet",
    "esportivabet",
]


def _parse_csv_env(name: str, fallback: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        return list(fallback)
    # Deduplicate while preserving order.
    deduped: List[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _parse_bool_env(name: str, fallback: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_api_football_keys() -> List[str]:
    primary = (os.getenv("API_FOOTBALL_KEY", "") or "").strip()
    fallback_raw = os.getenv("API_FOOTBALL_FALLBACK_KEYS", "")
    fallback_keys = [item.strip() for item in fallback_raw.split(",") if item.strip()]

    keys: List[str] = []
    if primary:
        keys.append(primary)
    for key in fallback_keys:
        if key not in keys:
            keys.append(key)
    return keys


def _app_env() -> str:
    return (os.getenv("APP_ENV", "local") or "local").strip().lower()


def _is_production_env() -> bool:
    return _app_env() in {"prd", "prod", "production"}


def _default_data_dir() -> str:
    temp_dir = (os.getenv("TEMP", "") or "").strip()
    if temp_dir:
        return str(Path(temp_dir) / "OddsEdge" / "dados")
    localappdata = (os.getenv("LOCALAPPDATA", "") or "").strip()
    if localappdata:
        return str(Path(localappdata) / "OddsEdge" / "dados")
    return str(PROJECT_ROOT / "data")


def _default_diretorio_banco() -> str:
    data_dir = (os.getenv("DATA_DIR", "") or "").strip()
    if data_dir:
        return data_dir
    return _default_data_dir()


def _default_admin_nome_inicial() -> str:
    return "Admin" if _app_env() == "local" else ""


def _default_admin_email_inicial() -> str:
    return "tiagoch25@gmail.com" if _app_env() == "local" else ""


def _default_admin_senha_inicial() -> str:
    return "admin123" if _app_env() == "local" else ""


def _default_auth_cookie_secure() -> bool:
    return _is_production_env()


def _default_app_base_url() -> str:
    porta = int(os.getenv("SERVER_PORT") or os.getenv("PORT", "8000"))
    return f"http://localhost:{porta}" if _app_env() == "local" else ""


def _default_email_modo() -> str:
    return "smtp" if _is_production_env() else "arquivo"


def _default_email_remetente() -> str:
    return "no-reply@oddsedge.local" if _app_env() == "local" else ""


@dataclass(frozen=True)
class Settings:
    app_env: str = _app_env()
    api_football_key: str = os.getenv("API_FOOTBALL_KEY", "")
    api_football_keys: List[str] = field(default_factory=_parse_api_football_keys)
    api_football_auth_mode: str = os.getenv(
        "API_FOOTBALL_AUTH_MODE", "apisports").lower()
    api_football_host: str = os.getenv(
        "API_FOOTBALL_HOST", "v3.football.api-sports.io")
    api_football_base_url: str = os.getenv(
        "API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
    api_football_free_plan_max_season: int = int(
        os.getenv("API_FOOTBALL_FREE_PLAN_MAX_SEASON", "2024"))

    the_odds_api_key: str = os.getenv("THE_ODDS_API_KEY", "")
    the_odds_base_url: str = os.getenv(
        "THE_ODDS_BASE_URL", "https://api.the-odds-api.com/v4")
    the_odds_regions: str = os.getenv("THE_ODDS_REGIONS", "eu")
    the_odds_markets: str = os.getenv("THE_ODDS_MARKETS", "h2h,totals")
    odds_sports: List[str] = field(
        default_factory=lambda: _parse_csv_env("ODDS_SPORTS", DEFAULT_ODDS_SPORTS))
    odds_only_active_sports: bool = _parse_bool_env(
        "ODDS_ONLY_ACTIVE_SPORTS", True)
    odds_dynamic_top_n: int = int(os.getenv("ODDS_DYNAMIC_TOP_N", "8"))
    odds_priority_sports: List[str] = field(
        default_factory=lambda: _parse_csv_env("ODDS_PRIORITY_SPORTS", DEFAULT_ODDS_PRIORITY_SPORTS))
    odds_max_sports_per_run: int = int(
        os.getenv("ODDS_MAX_SPORTS_PER_RUN", "0"))
    odds_preferred_bookmakers: List[str] = field(
        default_factory=lambda: _parse_csv_env("ODDS_PREFERRED_BOOKMAKERS", DEFAULT_ODDS_PREFERRED_BOOKMAKERS))
    odds_relevant_bookmakers: List[str] = field(
        default_factory=lambda: _parse_csv_env("ODDS_RELEVANT_BOOKMAKERS", DEFAULT_ODDS_RELEVANT_BOOKMAKERS))

    timezone: str = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
    league_goal_avg: float = float(os.getenv("LEAGUE_GOAL_AVG", "1.35"))
    min_probability: float = float(os.getenv("MIN_PROBABILITY", "0.65"))
    min_ev: float = float(os.getenv("MIN_EV", "0.0"))
    max_poisson_goals: int = int(os.getenv("MAX_POISSON_GOALS", "7"))
    request_timeout_seconds: int = int(
        os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    requests_trust_env: bool = os.getenv(
        "REQUESTS_TRUST_ENV", "false").lower() == "true"
    use_sample_data: bool = os.getenv(
        "USE_SAMPLE_DATA", "false").lower() == "true"
    skip_pipeline_on_start: bool = _parse_bool_env("SKIP_PIPELINE_ON_START", False)
    idle_shutdown_seconds: int = int(os.getenv("IDLE_SHUTDOWN_SECONDS", "25"))
    enable_idle_shutdown: bool = _parse_bool_env(
        "ENABLE_IDLE_SHUTDOWN", not _is_production_env())
    health_api_cache_seconds: int = int(os.getenv("HEALTH_API_CACHE_SECONDS", "300"))
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT")
                           or os.getenv("PORT", "8000"))
    data_dir: str = os.getenv("DATA_DIR", _default_data_dir())
    persistir_em_banco: bool = _parse_bool_env("PERSISTIR_EM_BANCO", True)
    nome_arquivo_banco: str = os.getenv("NOME_ARQUIVO_BANCO", "historico_apostas.db")
    diretorio_banco: str = os.getenv("DIRETORIO_BANCO", _default_diretorio_banco())
    admin_nome_inicial: str = os.getenv("ADMIN_NOME_INICIAL", _default_admin_nome_inicial())
    admin_email_inicial: str = os.getenv("ADMIN_EMAIL_INICIAL", _default_admin_email_inicial())
    admin_senha_inicial: str = os.getenv("ADMIN_SENHA_INICIAL", _default_admin_senha_inicial())
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "oddsedge_auth")
    auth_session_duration_hours: int = int(os.getenv("AUTH_SESSION_DURATION_HOURS", "168"))
    auth_cookie_secure: bool = _parse_bool_env("AUTH_COOKIE_SECURE", _default_auth_cookie_secure())
    app_base_url: str = os.getenv("APP_BASE_URL", _default_app_base_url())
    reset_senha_expiracao_minutos: int = int(os.getenv("RESET_SENHA_EXPIRACAO_MINUTOS", "60"))
    email_modo: str = os.getenv("EMAIL_MODO", _default_email_modo())
    email_remetente: str = os.getenv("EMAIL_REMETENTE", _default_email_remetente())
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_usuario: str = os.getenv("SMTP_USUARIO", "")
    smtp_senha: str = os.getenv("SMTP_SENHA", "")
    smtp_tls: bool = _parse_bool_env("SMTP_TLS", True)

    project_root: Path = PROJECT_ROOT

    @property
    def runtime_data_dir(self) -> Path:
        return Path(self.data_dir)

    @property
    def data_file(self) -> Path:
        return self.runtime_data_dir / "cache_matches.json"

    @property
    def history_dir(self) -> Path:
        return self.runtime_data_dir / "history"

    @property
    def caminho_banco(self) -> Path:
        arquivo = Path(self.nome_arquivo_banco)
        if arquivo.is_absolute():
            return arquivo
        return Path(self.diretorio_banco) / arquivo


settings = Settings()
