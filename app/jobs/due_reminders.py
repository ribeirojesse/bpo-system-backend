"""Job diário: lembra o cliente (push no app) das contas a pagar que
vencem hoje / nos próximos dias e das que ficaram em atraso.

Não há agendador dentro da API — rode isso uma vez por dia pelo cron da
EC2 (ver mobile/README.md, seção "Push notifications"):

    docker compose -f docker-compose.prod.yml exec -T api \
        python -m app.jobs.due_reminders

Uma notificação por cliente (resumo), não uma por conta, pra não virar
spam no celular.
"""

import logging

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.core.config import settings
from app.core.database import SessionLocal

# Importa os models relacionados pra o SQLAlchemy conseguir resolver as
# relationships declaradas por nome (ex.: AccountsPayable.client).
from app.models.tenant import Tenant  # noqa: F401
from app.models.client import Client  # noqa: F401
from app.models.financial_contact import FinancialContact  # noqa: F401
from app.models.expense_category import ExpenseCategory  # noqa: F401
from app.models.expense_subcategory import ExpenseSubcategory  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.accounts_payable import AccountsPayable
from app.models.user import User

from app.services.push_service import PushService


logger = logging.getLogger("due_reminders")


def _brl(valor: Decimal) -> str:

    texto = f"{valor:,.2f}"

    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def run() -> int:

    hoje = date.today()

    limite = hoje + timedelta(days=max(settings.PUSH_DIAS_AVISO_VENCIMENTO, 0))

    db = SessionLocal()

    enviados = 0

    try:
        # Só clientes que têm login CLIENTE ativo (quem não usa o portal
        # não tem pra quem avisar).
        client_ids = {
            u.client_id for u in db.query(User).filter(
                User.role == "CLIENTE",
                User.ativo.is_(True),
                User.client_id.isnot(None)
            ).all()
        }

        if not client_ids:
            return 0

        pendentes = db.query(AccountsPayable).filter(
            AccountsPayable.client_id.in_(client_ids),
            AccountsPayable.status == "PENDENTE",
            AccountsPayable.vencimento <= limite
        ).all()

        por_cliente = defaultdict(lambda: {
            "hoje": [], "proximos": [], "atrasadas": []
        })

        for conta in pendentes:

            grupo = por_cliente[conta.client_id]

            if conta.vencimento < hoje:
                grupo["atrasadas"].append(conta)

            elif conta.vencimento == hoje:
                grupo["hoje"].append(conta)

            else:
                grupo["proximos"].append(conta)

        for client_id, grupo in por_cliente.items():

            partes = []

            if grupo["hoje"]:
                total = sum((c.valor for c in grupo["hoje"]), Decimal("0"))
                partes.append(
                    f"{len(grupo['hoje'])} conta(s) vencem hoje ({_brl(total)})"
                )

            if grupo["proximos"]:
                total = sum((c.valor for c in grupo["proximos"]), Decimal("0"))
                partes.append(
                    f"{len(grupo['proximos'])} vencem em breve ({_brl(total)})"
                )

            if grupo["atrasadas"]:
                total = sum((c.valor for c in grupo["atrasadas"]), Decimal("0"))
                partes.append(
                    f"{len(grupo['atrasadas'])} em atraso ({_brl(total)})"
                )

            if not partes:
                continue

            titulo = (
                "Contas vencendo hoje 📅"
                if grupo["hoje"] else "Lembrete de contas a pagar"
            )

            enviados += PushService.notify_client(
                db,
                client_id,
                titulo,
                "; ".join(partes) + ".",
                tipo="VENCIMENTO",
                data={"screen": "lancamentos", "filtro": "PENDENTE"}
            )

    finally:
        db.close()

    return enviados


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    total = run()

    logger.info("Lembretes de vencimento: %s push(es) enviados", total)
