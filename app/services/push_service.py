"""Push notifications do app mobile (via Expo Push Service).

Fluxo:
  1. O app mobile pede permissão, obtém um "ExponentPushToken[...]" e
     registra em POST /api/routes/notifications/devices.
  2. Quando algo acontece (fechamento concluído, conta vencendo, mensagem
     manual do escritório), o backend chama PushService.notify_users /
     notify_client: grava o aviso na tabela `notifications` (histórico
     que o app mostra na aba "Avisos") e dispara o push pra todos os
     aparelhos ativos daqueles usuários.

Envio é "best-effort": se a Expo estiver fora ou a rede falhar, o aviso
continua salvo no histórico e o erro só vai pro log — nunca derruba a
requisição que originou o evento.

Opcional: EXPO_ACCESS_TOKEN no .env, se "Enhanced Security for Push
Notifications" estiver ligado no projeto do Expo (expo.dev).
"""

import logging

from datetime import datetime, UTC

import httpx

from sqlalchemy.orm import Session

from app.core.config import settings

from app.models.notification import Notification
from app.models.push_device import PushDevice
from app.models.user import User


logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# Limite da Expo por requisição.
EXPO_BATCH_SIZE = 100


def _is_expo_token(token: str) -> bool:

    return token.startswith("ExponentPushToken[") or \
        token.startswith("ExpoPushToken[")


class PushService:

    # ------------------------------------------------------------------
    # APARELHOS
    # ------------------------------------------------------------------

    @staticmethod
    def register_device(
        db: Session,
        user: User,
        token: str,
        platform: str | None = None,
        device_name: str | None = None,
    ) -> PushDevice:

        device = db.query(PushDevice).filter(
            PushDevice.token == token
        ).first()

        agora = datetime.now(UTC)

        if device:
            # Mesmo celular, possivelmente outro login — o token passa a
            # ser do usuário atual (quem saiu não recebe mais os avisos).
            device.user_id = user.id
            device.platform = platform or device.platform
            device.device_name = device_name or device.device_name
            device.ativo = True
            device.last_seen_at = agora

        else:
            device = PushDevice(
                user_id=user.id,
                token=token,
                platform=platform,
                device_name=device_name,
                ativo=True,
                last_seen_at=agora,
            )

            db.add(device)

        db.commit()
        db.refresh(device)

        return device

    @staticmethod
    def unregister_device(db: Session, user: User, token: str) -> None:

        (
            db.query(PushDevice)
            .filter(
                PushDevice.token == token,
                PushDevice.user_id == user.id
            )
            .delete()
        )

        db.commit()

    # ------------------------------------------------------------------
    # ENVIO
    # ------------------------------------------------------------------

    @staticmethod
    def notify_users(
        db: Session,
        user_ids: list,
        titulo: str,
        mensagem: str,
        tipo: str = "MENSAGEM",
        data: dict | None = None,
    ) -> int:
        """Grava o aviso no histórico de cada usuário e manda push pros
        aparelhos ativos. Retorna quantos pushes foram enviados."""

        user_ids = list({uid for uid in user_ids if uid})

        if not user_ids:
            return 0

        payload_data = dict(data or {})
        payload_data.setdefault("tipo", tipo)

        for uid in user_ids:
            db.add(Notification(
                user_id=uid,
                tipo=tipo,
                titulo=titulo,
                mensagem=mensagem,
                data=payload_data,
            ))

        db.commit()

        devices = db.query(PushDevice).filter(
            PushDevice.user_id.in_(user_ids),
            PushDevice.ativo.is_(True)
        ).all()

        tokens = [d.token for d in devices if _is_expo_token(d.token)]

        if not tokens:
            return 0

        mensagens = [
            {
                "to": token,
                "title": titulo,
                "body": mensagem,
                "data": payload_data,
                "sound": "default",
                "channelId": "default",
                "priority": "high",
            }
            for token in tokens
        ]

        invalidos = PushService._send_to_expo(mensagens)

        if invalidos:
            (
                db.query(PushDevice)
                .filter(PushDevice.token.in_(invalidos))
                .update({PushDevice.ativo: False}, synchronize_session=False)
            )

            db.commit()

        return len(tokens) - len(invalidos)

    @staticmethod
    def notify_client(
        db: Session,
        client_id,
        titulo: str,
        mensagem: str,
        tipo: str = "MENSAGEM",
        data: dict | None = None,
    ) -> int:
        """Avisa todos os logins CLIENTE ativos ligados a um client."""

        user_ids = [
            u.id for u in db.query(User).filter(
                User.client_id == client_id,
                User.role == "CLIENTE",
                User.ativo.is_(True)
            ).all()
        ]

        return PushService.notify_users(
            db, user_ids, titulo, mensagem, tipo, data
        )

    @staticmethod
    def _send_to_expo(mensagens: list[dict]) -> list[str]:
        """Manda em lotes pra Expo. Devolve os tokens que a Expo disse
        não existirem mais (DeviceNotRegistered), pra desativar."""

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        access_token = getattr(settings, "EXPO_ACCESS_TOKEN", "")

        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        invalidos: list[str] = []

        for i in range(0, len(mensagens), EXPO_BATCH_SIZE):

            lote = mensagens[i:i + EXPO_BATCH_SIZE]

            try:
                resp = httpx.post(
                    EXPO_PUSH_URL,
                    json=lote,
                    headers=headers,
                    timeout=10
                )

                resp.raise_for_status()

                tickets = resp.json().get("data", [])

                for msg, ticket in zip(lote, tickets):

                    if ticket.get("status") == "error":

                        detalhe = (ticket.get("details") or {}).get("error")

                        if detalhe == "DeviceNotRegistered":
                            invalidos.append(msg["to"])

                        else:
                            logger.warning(
                                "Push recusado pela Expo: %s",
                                ticket.get("message")
                            )

            except Exception:
                logger.exception("Falha ao enviar push pela Expo")

        return invalidos


def notify_client_background(
    client_id,
    titulo: str,
    mensagem: str,
    tipo: str = "MENSAGEM",
    data: dict | None = None,
) -> None:
    """Versão pra FastAPI BackgroundTasks: abre a própria sessão de banco
    (a da requisição já foi fechada quando a task roda)."""

    from app.core.database import SessionLocal

    db = SessionLocal()

    try:
        PushService.notify_client(db, client_id, titulo, mensagem, tipo, data)

    except Exception:
        logger.exception("Falha ao gerar notificação do cliente %s", client_id)

    finally:
        db.close()
