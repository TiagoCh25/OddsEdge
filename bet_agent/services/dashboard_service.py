"""Regras de exibicao do dashboard por perfil e plano."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class DashboardService:
    """Aplica filtros de elegibilidade e limitacao por plano no payload do dashboard."""

    _STATUS_NAO_INICIADO = {"NS", "TBD", "PST"}
    _STATUS_AO_VIVO = {"1H", "HT", "2H", "ET", "BT", "LIVE", "INT"}
    _STATUS_ENCERRADO = {"FT", "AET", "PEN", "CANC", "ABD", "AWD", "WO"}
    _ODD_MINIMA_GRATIS = 1.30
    _MARGEM_MINIMA_GRATIS_SEGUNDOS = 3600

    @classmethod
    def preparar_payload_dashboard(
        cls,
        payload: dict[str, Any],
        usuario: dict[str, Any],
        *,
        agora: datetime | None = None,
    ) -> dict[str, Any]:
        agora = agora or datetime.now()
        novo_payload = dict(payload or {})
        bets = [dict(item) for item in (novo_payload.get("bets") or []) if isinstance(item, dict)]

        recomendacoes_validas = cls._ordenar_recomendacoes(
            [bet for bet in bets if cls._recomendacao_valida_para_exibicao_geral(bet, agora)]
        )
        recomendacoes_gratis = [
            bet for bet in recomendacoes_validas if cls._recomendacao_elegivel_gratis(bet, agora)
        ]

        perfil = str(usuario.get("perfil") or "usuario").strip().lower()
        plano = str(usuario.get("plano") or "gratis").strip().lower()
        visao_completa = perfil == "admin" or plano == "pro"

        if visao_completa:
            bets_visiveis = recomendacoes_validas
            estado = "vazio_global" if not recomendacoes_validas else "completo"
            mensagem = (
                "Nenhuma recomendacao disponivel no momento." if not recomendacoes_validas else ""
            )
            mensagem_auxiliar = (
                "Volte mais tarde para conferir novas oportunidades."
                if not recomendacoes_validas
                else ""
            )
            mostrar_upgrade = False
        elif recomendacoes_gratis:
            bets_visiveis = [recomendacoes_gratis[0]]
            estado = "gratis_com_recomendacao"
            mensagem = "Voce esta vendo 1 recomendacao do dia no plano Gratis."
            mensagem_auxiliar = "Desbloqueie todas as recomendacoes com o plano Pro."
            mostrar_upgrade = True
        elif recomendacoes_validas:
            bets_visiveis = []
            estado = "gratis_sem_elegivel"
            mensagem = "Nenhuma recomendacao gratuita disponivel no momento."
            mensagem_auxiliar = "Desbloqueie o plano Pro para acessar todas as recomendacoes validas do dia."
            mostrar_upgrade = True
        else:
            bets_visiveis = []
            estado = "vazio_global"
            mensagem = "Nenhuma recomendacao disponivel no momento."
            mensagem_auxiliar = "Volte mais tarde para conferir novas oportunidades."
            mostrar_upgrade = False

        novo_payload["bets"] = bets_visiveis
        novo_payload["total_bets"] = len(bets_visiveis)
        novo_payload["dashboard_estado"] = estado
        novo_payload["dashboard_mensagem"] = mensagem
        novo_payload["dashboard_mensagem_auxiliar"] = mensagem_auxiliar
        novo_payload["dashboard_mostrar_upgrade"] = mostrar_upgrade
        novo_payload["dashboard_cta_label"] = "Desbloquear plano Pro" if mostrar_upgrade else ""
        novo_payload["dashboard_plano"] = plano
        novo_payload["dashboard_perfil"] = perfil
        novo_payload["dashboard_total_validas"] = len(recomendacoes_validas)
        novo_payload["dashboard_total_gratis_elegiveis"] = len(recomendacoes_gratis)
        return novo_payload

    @classmethod
    def _ordenar_recomendacoes(cls, bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            bets,
            key=lambda bet: (
                -cls._probabilidade(bet),
                -cls._score_secundario(bet),
                -cls._to_float(bet.get("ev")),
            ),
        )

    @classmethod
    def _recomendacao_valida_para_exibicao_geral(cls, bet: dict[str, Any], agora: datetime) -> bool:
        status = str(bet.get("status_short") or "").strip().upper()
        if status:
            if status in cls._STATUS_ENCERRADO:
                return False
            if status in cls._STATUS_NAO_INICIADO or status in cls._STATUS_AO_VIVO:
                return True
            return False

        kickoff_ts = cls._kickoff_timestamp(bet.get("kickoff"))
        if kickoff_ts is None:
            return False
        return kickoff_ts > agora.timestamp()

    @classmethod
    def _recomendacao_nao_iniciada(cls, bet: dict[str, Any], agora: datetime) -> bool:
        kickoff_ts = cls._kickoff_timestamp(bet.get("kickoff"))
        if kickoff_ts is None:
            return False
        if kickoff_ts <= agora.timestamp():
            return False

        status = str(bet.get("status_short") or "").strip().upper()
        if status and status not in cls._STATUS_NAO_INICIADO:
            return False
        return True

    @classmethod
    def _recomendacao_elegivel_gratis(cls, bet: dict[str, Any], agora: datetime) -> bool:
        if not cls._recomendacao_nao_iniciada(bet, agora):
            return False
        if cls._to_float(bet.get("odd")) < cls._ODD_MINIMA_GRATIS:
            return False
        kickoff_ts = cls._kickoff_timestamp(bet.get("kickoff"))
        if kickoff_ts is None:
            return False
        return (kickoff_ts - agora.timestamp()) >= cls._MARGEM_MINIMA_GRATIS_SEGUNDOS

    @staticmethod
    def _to_float(value: object) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    @classmethod
    def _probabilidade(cls, bet: dict[str, Any]) -> float:
        probability = cls._to_float(bet.get("probability"))
        if probability > 1:
            return probability / 100.0
        if probability > 0:
            return probability

        probabilidade = cls._to_float(bet.get("probabilidade"))
        if probabilidade > 1:
            return probabilidade / 100.0
        return probabilidade

    @classmethod
    def _score_secundario(cls, bet: dict[str, Any]) -> float:
        for campo in ("score", "score_modelo", "ranking_score"):
            valor = cls._to_float(bet.get(campo))
            if valor:
                return valor
        return 0.0

    @staticmethod
    def _kickoff_timestamp(value: object) -> float | None:
        texto = str(value or "").strip()
        if not texto:
            return None
        try:
            kickoff = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except Exception:
            return None
        return kickoff.timestamp()
