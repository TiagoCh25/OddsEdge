"""Repositorio SQLite para armazenar historico de execucoes e apostas."""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class DadosPersistenciaExecucao:
    execucao_id: str
    data_referencia: str
    ambiente: str
    fonte_dados: str
    payload: Dict[str, object]
    partidas: List[Dict[str, object]]
    odds_por_partida: Dict[str, Dict[str, float]]
    apostas_recomendadas: List[Dict[str, object]]
    stats_basis_por_partida: List[Dict[str, object]]


class RepositorioHistoricoSQLite:
    """Persistencia historica em SQLite com nomes de tabelas/colunas em portugues."""

    _STATUS_FINALIZADO = {"FT", "AET", "PEN", "AWD", "WO"}
    _MERCADOS_SUPORTADOS = {
        "over_0_5",
        "over_1_5",
        "over_2_5",
        "over_3_5",
        "under_2_5",
        "under_3_5",
        "btts_yes",
        "btts_no",
        "home_win",
        "draw",
        "away_win",
        "double_chance_1x",
        "double_chance_x2",
        "double_chance_12",
    }

    def __init__(self, caminho_banco: Path) -> None:
        self._caminho_banco = Path(caminho_banco)
        self._caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_schema()

    def _conexao(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._caminho_banco), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _inicializar_schema(self) -> None:
        with self._conexao() as conn:
            conn.execute("PRAGMA foreign_keys=ON;")

            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS execucoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execucao_id TEXT NOT NULL UNIQUE,
                    gerado_em TEXT,
                    data_referencia TEXT,
                    ambiente TEXT,
                    fonte_dados TEXT,
                    status_execucao TEXT,
                    mensagem_erro TEXT,
                    total_jogos_analisados INTEGER DEFAULT 0,
                    total_jogos_com_odds INTEGER DEFAULT 0,
                    total_apostas INTEGER DEFAULT 0,
                    odd_combinada_top2 REAL,
                    payload_json TEXT,
                    criado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS partidas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execucao_id TEXT NOT NULL,
                    fixture_id INTEGER,
                    chave_partida TEXT,
                    kickoff TEXT,
                    liga_id INTEGER,
                    liga_nome TEXT,
                    liga_logo TEXT,
                    pais TEXT,
                    temporada INTEGER,
                    time_casa_id INTEGER,
                    time_casa_nome TEXT,
                    time_casa_logo TEXT,
                    time_fora_id INTEGER,
                    time_fora_nome TEXT,
                    time_fora_logo TEXT,
                    status_curto TEXT,
                    status_jogo TEXT,
                    gols_casa INTEGER,
                    gols_fora INTEGER,
                    stats_basis_json TEXT,
                    criado_em TEXT NOT NULL,
                    UNIQUE(execucao_id, fixture_id)
                );

                CREATE TABLE IF NOT EXISTS odds_partidas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execucao_id TEXT NOT NULL,
                    fixture_id INTEGER,
                    chave_partida TEXT NOT NULL,
                    mercado_chave TEXT NOT NULL,
                    odd REAL NOT NULL,
                    criado_em TEXT NOT NULL,
                    UNIQUE(execucao_id, fixture_id, mercado_chave)
                );

                CREATE TABLE IF NOT EXISTS apostas_recomendadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execucao_id TEXT NOT NULL,
                    fixture_id INTEGER,
                    jogo TEXT,
                    liga TEXT,
                    liga_logo TEXT,
                    time_casa TEXT,
                    time_fora TEXT,
                    logo_time_casa TEXT,
                    logo_time_fora TEXT,
                    tipo_aposta TEXT NOT NULL,
                    mercado_chave TEXT,
                    probabilidade REAL,
                    probabilidade_percentual REAL,
                    odd REAL,
                    ev REAL,
                    kickoff TEXT,
                    status_curto TEXT,
                    status_jogo TEXT,
                    gols_casa INTEGER,
                    gols_fora INTEGER,
                    stats_basis_json TEXT,
                    resultado_aposta TEXT,
                    placar_final TEXT,
                    criado_em TEXT NOT NULL,
                    UNIQUE(execucao_id, fixture_id, tipo_aposta)
                );
                """
            )
            self._migrar_schema(conn)

    def _migrar_schema(self, conn: sqlite3.Connection) -> None:
        self._garantir_coluna(conn, "apostas_recomendadas", "mercado_chave", "TEXT")

    @staticmethod
    def _colunas_tabela(conn: sqlite3.Connection, tabela: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
        return {str(row[1]) for row in rows}

    def _garantir_coluna(self, conn: sqlite3.Connection, tabela: str, coluna: str, tipo: str) -> None:
        if coluna in self._colunas_tabela(conn, tabela):
            return
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")

    @staticmethod
    def _indexar_stats_basis_por_fixture(
        stats_basis_por_partida: List[Dict[str, object]],
    ) -> Dict[int, Dict[str, object]]:
        por_fixture: Dict[int, Dict[str, object]] = {}
        for item in stats_basis_por_partida:
            if not isinstance(item, dict):
                continue
            fixture_id = item.get("fixture_id")
            if fixture_id is None:
                continue
            try:
                stats_basis = item.get("stats_basis", {})
                por_fixture[int(fixture_id)] = stats_basis if isinstance(stats_basis, dict) else {}
            except Exception:
                continue
        return por_fixture

    @staticmethod
    def _normalizar_texto(valor: object) -> str:
        texto = str(valor or "").strip().lower()
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
        return " ".join(texto.split())

    @classmethod
    def _normalizar_mercado_chave(cls, aposta: Dict[str, object]) -> str | None:
        mercado_chave = cls._normalizar_texto(aposta.get("mercado_chave"))
        if mercado_chave in cls._MERCADOS_SUPORTADOS:
            return mercado_chave

        mercado = cls._normalizar_texto(aposta.get("tipo_aposta"))
        if mercado.startswith("over 0.5"):
            return "over_0_5"
        if mercado.startswith("over 1.5"):
            return "over_1_5"
        if mercado.startswith("over 2.5"):
            return "over_2_5"
        if mercado.startswith("over 3.5"):
            return "over_3_5"
        if mercado.startswith("under 2.5"):
            return "under_2_5"
        if mercado.startswith("under 3.5"):
            return "under_3_5"
        if "ambos" in mercado and "marcam" in mercado:
            if "nao" in mercado:
                return "btts_no"
            return "btts_yes"
        if mercado in {"vitoria casa", "vitria casa", "home_win"}:
            return "home_win"
        if mercado in {"empate", "draw"}:
            return "draw"
        if mercado in {"vitoria visitante", "vitria visitante", "away_win"}:
            return "away_win"
        if "dupla chance 1x" in mercado:
            return "double_chance_1x"
        if "dupla chance x2" in mercado:
            return "double_chance_x2"
        if "dupla chance 12" in mercado:
            return "double_chance_12"
        return None

    @classmethod
    def _jogo_finalizado(cls, status_curto: object) -> bool:
        status = str(status_curto or "").upper().strip()
        return status in cls._STATUS_FINALIZADO

    @staticmethod
    def _placar_final(gols_casa: object, gols_fora: object) -> str | None:
        if gols_casa is None or gols_fora is None:
            return None
        try:
            return f"{int(gols_casa)} x {int(gols_fora)}"
        except Exception:
            return None

    @classmethod
    def _mercado_ganhou(
        cls,
        mercado_chave: str | None,
        gols_casa: int,
        gols_fora: int,
    ) -> bool | None:
        if not mercado_chave:
            return None

        total = gols_casa + gols_fora
        if mercado_chave == "over_0_5":
            return total >= 1
        if mercado_chave == "over_1_5":
            return total >= 2
        if mercado_chave == "over_2_5":
            return total >= 3
        if mercado_chave == "over_3_5":
            return total >= 4
        if mercado_chave == "under_2_5":
            return total <= 2
        if mercado_chave == "under_3_5":
            return total <= 3
        if mercado_chave == "btts_yes":
            return gols_casa > 0 and gols_fora > 0
        if mercado_chave == "btts_no":
            return gols_casa == 0 or gols_fora == 0
        if mercado_chave == "home_win":
            return gols_casa > gols_fora
        if mercado_chave == "draw":
            return gols_casa == gols_fora
        if mercado_chave == "away_win":
            return gols_fora > gols_casa
        if mercado_chave == "double_chance_1x":
            return gols_casa >= gols_fora
        if mercado_chave == "double_chance_x2":
            return gols_fora >= gols_casa
        if mercado_chave == "double_chance_12":
            return gols_casa != gols_fora
        return None

    @classmethod
    def _resultado_aposta(
        cls,
        mercado_chave: str | None,
        status_curto: object,
        gols_casa: object,
        gols_fora: object,
    ) -> str:
        if not cls._jogo_finalizado(status_curto):
            return "pendente"
        if gols_casa is None or gols_fora is None:
            return "pendente"

        try:
            home = int(gols_casa)
            away = int(gols_fora)
        except Exception:
            return "pendente"

        ganhou = cls._mercado_ganhou(mercado_chave, home, away)
        if ganhou is True:
            return "ganhou"
        if ganhou is False:
            return "perdeu"
        return "indefinido"

    def salvar_execucao_completa(self, dados: DadosPersistenciaExecucao) -> None:
        agora = datetime.now().isoformat(timespec="seconds")
        payload = dados.payload
        stats_basis_por_fixture = self._indexar_stats_basis_por_fixture(dados.stats_basis_por_partida)

        # Identifica fixture_id por chave de partida para salvar odds com referencia da partida.
        fixture_por_chave: Dict[str, int] = {}
        for partida in dados.partidas:
            chave = str(partida.get("chave_partida", "")).strip()
            fixture_id = partida.get("fixture_id")
            if not chave or fixture_id is None:
                continue
            try:
                fixture_por_chave[chave] = int(fixture_id)
            except Exception:
                continue

        with self._conexao() as conn:
            conn.execute("BEGIN")
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO execucoes (
                        execucao_id,
                        gerado_em,
                        data_referencia,
                        ambiente,
                        fonte_dados,
                        status_execucao,
                        mensagem_erro,
                        total_jogos_analisados,
                        total_jogos_com_odds,
                        total_apostas,
                        odd_combinada_top2,
                        payload_json,
                        criado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dados.execucao_id,
                        str(payload.get("generated_at") or ""),
                        dados.data_referencia,
                        dados.ambiente,
                        dados.fonte_dados,
                        str(payload.get("status") or ""),
                        str(payload.get("error_message") or ""),
                        int(payload.get("total_games_analyzed") or 0),
                        int(payload.get("total_games_with_odds") or 0),
                        int(payload.get("total_bets") or 0),
                        float(payload.get("combined_odd_top2")) if payload.get("combined_odd_top2") is not None else None,
                        json.dumps(payload, ensure_ascii=False),
                        agora,
                    ),
                )

                for partida in dados.partidas:
                    fixture_id_raw = partida.get("fixture_id")
                    fixture_id = int(fixture_id_raw) if fixture_id_raw is not None else None
                    stats_basis = stats_basis_por_fixture.get(fixture_id or -1, {})
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO partidas (
                            execucao_id,
                            fixture_id,
                            chave_partida,
                            kickoff,
                            liga_id,
                            liga_nome,
                            liga_logo,
                            pais,
                            temporada,
                            time_casa_id,
                            time_casa_nome,
                            time_casa_logo,
                            time_fora_id,
                            time_fora_nome,
                            time_fora_logo,
                            status_curto,
                            status_jogo,
                            gols_casa,
                            gols_fora,
                            stats_basis_json,
                            criado_em
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            dados.execucao_id,
                            fixture_id,
                            str(partida.get("chave_partida") or ""),
                            str(partida.get("kickoff") or ""),
                            int(partida.get("league_id")) if partida.get("league_id") is not None else None,
                            str(partida.get("league") or ""),
                            str(partida.get("league_logo") or ""),
                            str(partida.get("country") or ""),
                            int(partida.get("season")) if partida.get("season") is not None else None,
                            int(partida.get("home_team_id")) if partida.get("home_team_id") is not None else None,
                            str(partida.get("home_team") or ""),
                            str(partida.get("home_team_logo") or ""),
                            int(partida.get("away_team_id")) if partida.get("away_team_id") is not None else None,
                            str(partida.get("away_team") or ""),
                            str(partida.get("away_team_logo") or ""),
                            str(partida.get("status_short") or ""),
                            str(partida.get("status_jogo") or ""),
                            int(partida.get("home_goals")) if partida.get("home_goals") is not None else None,
                            int(partida.get("away_goals")) if partida.get("away_goals") is not None else None,
                            json.dumps(stats_basis, ensure_ascii=False),
                            agora,
                        ),
                    )

                for chave_partida, mercados in dados.odds_por_partida.items():
                    if not isinstance(mercados, dict):
                        continue
                    fixture_id = fixture_por_chave.get(chave_partida)
                    for mercado_chave, odd in mercados.items():
                        try:
                            odd_float = float(odd)
                        except Exception:
                            continue
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO odds_partidas (
                                execucao_id,
                                fixture_id,
                                chave_partida,
                                mercado_chave,
                                odd,
                                criado_em
                            ) VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                dados.execucao_id,
                                fixture_id,
                                str(chave_partida or ""),
                                str(mercado_chave or ""),
                                odd_float,
                                agora,
                            ),
                        )

                for aposta in dados.apostas_recomendadas:
                    fixture_id_raw = aposta.get("fixture_id")
                    fixture_id = int(fixture_id_raw) if fixture_id_raw is not None else None
                    gols_casa = aposta.get("home_goals")
                    gols_fora = aposta.get("away_goals")
                    status_curto = aposta.get("status_short")
                    mercado_chave = self._normalizar_mercado_chave(aposta)
                    resultado_aposta = self._resultado_aposta(
                        mercado_chave=mercado_chave,
                        status_curto=status_curto,
                        gols_casa=gols_casa,
                        gols_fora=gols_fora,
                    )
                    placar_final = self._placar_final(gols_casa, gols_fora)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO apostas_recomendadas (
                            execucao_id,
                            fixture_id,
                            jogo,
                            liga,
                            liga_logo,
                            time_casa,
                            time_fora,
                            logo_time_casa,
                            logo_time_fora,
                            tipo_aposta,
                            mercado_chave,
                            probabilidade,
                            probabilidade_percentual,
                            odd,
                            ev,
                            kickoff,
                            status_curto,
                            status_jogo,
                            gols_casa,
                            gols_fora,
                            stats_basis_json,
                            resultado_aposta,
                            placar_final,
                            criado_em
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            dados.execucao_id,
                            fixture_id,
                            str(aposta.get("jogo") or ""),
                            str(aposta.get("liga") or ""),
                            str(aposta.get("league_logo") or ""),
                            str(aposta.get("home_team") or ""),
                            str(aposta.get("away_team") or ""),
                            str(aposta.get("home_team_logo") or ""),
                            str(aposta.get("away_team_logo") or ""),
                            str(aposta.get("tipo_aposta") or ""),
                            mercado_chave,
                            float(aposta.get("probability")) if aposta.get("probability") is not None else None,
                            float(aposta.get("probabilidade")) if aposta.get("probabilidade") is not None else None,
                            float(aposta.get("odd")) if aposta.get("odd") is not None else None,
                            float(aposta.get("ev")) if aposta.get("ev") is not None else None,
                            str(aposta.get("kickoff") or ""),
                            str(status_curto or ""),
                            str(aposta.get("status_jogo") or ""),
                            int(gols_casa) if gols_casa is not None else None,
                            int(gols_fora) if gols_fora is not None else None,
                            json.dumps(aposta.get("stats_basis", {}), ensure_ascii=False),
                            resultado_aposta,
                            placar_final,
                            agora,
                        ),
                    )

                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def atualizar_resultados_por_apostas(self, apostas: List[Dict[str, object]]) -> int:
        """Atualiza status/placar/resultado para apostas ja persistidas no banco."""
        if not apostas:
            return 0

        linhas_atualizadas = 0
        with self._conexao() as conn:
            conn.execute("BEGIN")
            try:
                for aposta in apostas:
                    if not isinstance(aposta, dict):
                        continue

                    fixture_id = aposta.get("fixture_id")
                    try:
                        fixture_id_int = int(fixture_id) if fixture_id is not None else None
                    except Exception:
                        fixture_id_int = None
                    if fixture_id_int is None:
                        continue

                    status_curto = str(aposta.get("status_short") or "")
                    status_jogo = str(aposta.get("status_jogo") or "")
                    gols_casa = aposta.get("home_goals")
                    gols_fora = aposta.get("away_goals")
                    mercado_chave = self._normalizar_mercado_chave(aposta)
                    tipo_aposta = str(aposta.get("tipo_aposta") or "")

                    resultado_aposta = self._resultado_aposta(
                        mercado_chave=mercado_chave,
                        status_curto=status_curto,
                        gols_casa=gols_casa,
                        gols_fora=gols_fora,
                    )
                    placar_final = self._placar_final(gols_casa, gols_fora)

                    conn.execute(
                        """
                        UPDATE partidas
                        SET
                            status_curto = ?,
                            status_jogo = ?,
                            gols_casa = ?,
                            gols_fora = ?
                        WHERE fixture_id = ?
                        """,
                        (
                            status_curto,
                            status_jogo,
                            int(gols_casa) if gols_casa is not None else None,
                            int(gols_fora) if gols_fora is not None else None,
                            fixture_id_int,
                        ),
                    )

                    cursor = conn.execute(
                        """
                        UPDATE apostas_recomendadas
                        SET
                            status_curto = ?,
                            status_jogo = ?,
                            gols_casa = ?,
                            gols_fora = ?,
                            resultado_aposta = ?,
                            placar_final = ?
                        WHERE
                            fixture_id = ?
                            AND (
                                (mercado_chave IS NOT NULL AND mercado_chave <> '' AND mercado_chave = ?)
                                OR ((mercado_chave IS NULL OR mercado_chave = '') AND tipo_aposta = ?)
                            )
                        """,
                        (
                            status_curto,
                            status_jogo,
                            int(gols_casa) if gols_casa is not None else None,
                            int(gols_fora) if gols_fora is not None else None,
                            resultado_aposta,
                            placar_final,
                            fixture_id_int,
                            str(mercado_chave or ""),
                            tipo_aposta,
                        ),
                    )
                    linhas_atualizadas += int(cursor.rowcount or 0)

                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return linhas_atualizadas
