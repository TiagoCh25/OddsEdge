import sqlite3

from db.repositorio_historico import DadosPersistenciaExecucao, RepositorioHistoricoSQLite


def test_repository_persists_execution(tmp_path):
    db_path = tmp_path / "historico_apostas.db"
    repository = RepositorioHistoricoSQLite(db_path)

    repository.salvar_execucao_completa(
        DadosPersistenciaExecucao(
            execucao_id="exec-001",
            data_referencia="2026-03-14",
            ambiente="test",
            fonte_dados="sample",
            payload={
                "generated_at": "2026-03-14T10:00:00",
                "status": "ok",
                "error_message": None,
                "total_games_analyzed": 1,
                "total_games_with_odds": 1,
                "total_bets": 1,
                "combined_odd_top2": 1.8,
            },
            partidas=[
                {
                    "fixture_id": 123,
                    "chave_partida": "inter__milan",
                    "kickoff": "2026-03-14T18:00:00",
                    "league_id": 71,
                    "league": "Serie A",
                    "country": "Italy",
                    "season": 2026,
                    "home_team_id": 1,
                    "home_team": "Inter",
                    "away_team_id": 2,
                    "away_team": "Milan",
                }
            ],
            odds_por_partida={"inter__milan": {"over_1_5": 1.8}},
            apostas_recomendadas=[
                {
                    "fixture_id": 123,
                    "jogo": "Inter vs Milan",
                    "liga": "Serie A",
                    "home_team": "Inter",
                    "away_team": "Milan",
                    "tipo_aposta": "Over 1.5 gols",
                    "mercado_chave": "over_1_5",
                    "probability": 0.72,
                    "probabilidade": 72.0,
                    "odd": 1.8,
                    "ev": 0.296,
                    "kickoff": "2026-03-14T18:00:00",
                    "status_short": "NS",
                    "status_jogo": "Not Started",
                    "home_goals": None,
                    "away_goals": None,
                    "stats_basis": {},
                }
            ],
            stats_basis_por_partida=[{"fixture_id": 123, "stats_basis": {"label": "sample"}}],
            erros_processamento=[
                {
                    "fixture_id": 123,
                    "jogo": "Inter vs Milan",
                    "liga": "Serie A",
                    "time_nome": "Inter",
                    "time_id": 1,
                    "lado_time": "home",
                    "etapa": "estatisticas_time",
                    "mensagem_erro": "Falha ao buscar estatisticas do time Inter (id 1).",
                }
            ],
        )
    )

    with sqlite3.connect(db_path) as connection:
        execution_count = connection.execute("SELECT COUNT(*) FROM execucoes").fetchone()[0]
        recommended_count = connection.execute("SELECT COUNT(*) FROM apostas_recomendadas").fetchone()[0]
        error_count = connection.execute("SELECT COUNT(*) FROM erros_processamento").fetchone()[0]

    assert execution_count == 1
    assert recommended_count == 1
    assert error_count == 1
