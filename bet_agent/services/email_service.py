"""Entrega simples de emails transacionais com fallback local em arquivo."""

from __future__ import annotations

import json
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from app.config import settings


@dataclass(frozen=True)
class EmailTransacional:
    destinatario: str
    assunto: str
    html: str
    texto: str


class EmailService:
    """Envia emails por SMTP ou salva uma copia local em arquivo."""

    @staticmethod
    def _outbox_dir() -> Path:
        diretorio = Path(settings.data_dir) / "emails_saida"
        diretorio.mkdir(parents=True, exist_ok=True)
        return diretorio

    @classmethod
    def _salvar_email_em_arquivo(cls, email: EmailTransacional) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        caminho = cls._outbox_dir() / f"email_{timestamp}.json"
        payload = {
            "destinatario": email.destinatario,
            "assunto": email.assunto,
            "texto": email.texto,
            "html": email.html,
            "criado_em": datetime.now().isoformat(timespec="seconds"),
        }
        caminho.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return caminho

    @staticmethod
    def _enviar_smtp(email: EmailTransacional) -> None:
        if not settings.smtp_host:
            raise RuntimeError("SMTP_HOST nao configurado.")

        mensagem = EmailMessage()
        mensagem["Subject"] = email.assunto
        mensagem["From"] = settings.email_remetente
        mensagem["To"] = email.destinatario
        mensagem.set_content(email.texto)
        mensagem.add_alternative(email.html, subtype="html")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as servidor:
            if settings.smtp_tls:
                servidor.starttls()
            if settings.smtp_usuario:
                servidor.login(settings.smtp_usuario, settings.smtp_senha)
            servidor.send_message(mensagem)

    @classmethod
    def enviar_email(cls, email: EmailTransacional) -> Path | None:
        modo = str(settings.email_modo or "").strip().lower()
        if modo == "smtp":
            cls._enviar_smtp(email)
            return None
        return cls._salvar_email_em_arquivo(email)
