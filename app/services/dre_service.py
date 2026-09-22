from collections import defaultdict

from decimal import Decimal

from fastapi import HTTPException

from app.repositories.client_repository import ClientRepository

from app.repositories.dre_template_repository import (
    DreTemplateRepository
)

from app.models.accounts_payable import AccountsPayable
from app.models.accounts_receivable import AccountsReceivable
from app.models.expense_category import ExpenseCategory
from app.models.expense_subcategory import ExpenseSubcategory
from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.models.bank_reconciliation import BankReconciliation


MESES = [
    "Jan", "Fev", "Mar", "Abr",
    "Mai", "Jun", "Jul", "Ago",
    "Set", "Out", "Nov", "Dez",
]


class DreService:

    # ------------------------------------------------------------
    # MODELOS (TEMPLATES)
    # ------------------------------------------------------------

    @staticmethod
    def _resolve_client_id(current_user, requested_client_id):
        """CLIENTE sempre usa o próprio client_id, ignorando qualquer
        valor enviado; ADMIN precisa informar de qual cliente da
        carteira é o relatório (igual ao resto do sistema — só o
        ClientSwitcher escolhe, aqui é o mesmo id repassado)."""

        if current_user.role == "CLIENTE":
            return current_user.client_id

        if not requested_client_id:
            raise HTTPException(
                status_code=400,
                detail="Informe o cliente para gerar o relatório"
            )

        return requested_client_id

    @staticmethod
    def _validar_cliente(db, current_user, client_id):

        client = ClientRepository.get_by_id(
            db,
            current_user.tenant_id,
            client_id
        )

        if not client:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        return client

    @staticmethod
    def create_template(db, current_user, data):

        client_id = data.client_id

        # CLIENTE só pode salvar modelo pro próprio client — nunca um
        # modelo "padrão da carteira" (client_id nulo é reservado pro
        # ADMIN organizar modelos reutilizáveis entre clientes).
        if current_user.role == "CLIENTE":
            client_id = current_user.client_id
        elif client_id:
            DreService._validar_cliente(db, current_user, client_id)

        payload = {
            "tenant_id": current_user.tenant_id,
            "client_id": client_id,
            "nome": data.nome,
            "modo": data.modo,
            "cor_destaque": data.cor_destaque,
            "config": {
                "blocos": [
                    bloco.model_dump(mode="json")
                    for bloco in data.blocos
                ]
            },
        }

        return DreTemplateRepository.create(db, payload)

    @staticmethod
    def list_templates(db, current_user, client_id=None):

        if current_user.role == "CLIENTE":
            return DreTemplateRepository.get_all_for_client(
                db,
                current_user.tenant_id,
                current_user.client_id
            )

        if client_id:
            return DreTemplateRepository.get_all_for_client(
                db,
                current_user.tenant_id,
                client_id
            )

        return DreTemplateRepository.get_all_for_admin(
            db,
            current_user.tenant_id
        )

    @staticmethod
    def get_template(db, current_user, template_id):

        template = DreTemplateRepository.get_by_id(
            db,
            current_user.tenant_id,
            template_id
        )

        if not template:
            raise HTTPException(
                status_code=404,
                detail="Modelo de DRE não encontrado"
            )

        if (
            current_user.role == "CLIENTE"
            and template.client_id is not None
            and template.client_id != current_user.client_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Modelo de DRE não encontrado"
            )

        return template

    @staticmethod
    def update_template(db, current_user, template_id, data):

        template = DreService.get_template(
            db, current_user, template_id
        )

        # mode="json" é essencial aqui: "blocos" tem category_ids
        # tipado como uuid.UUID no schema, e sem mode="json" o dump do
        # Pydantic mantém esses valores como objetos UUID de verdade
        # (não string). O destino (config, coluna JSONB) precisa de
        # tipos serializáveis em JSON puro — sem essa conversão, o
        # commit falhava com "Object of type UUID is not JSON
        # serializable", sem nenhum handler pra capturar, e virava um
        # 500 cru pro navegador. create_template já fazia essa mesma
        # conversão por bloco (bloco.model_dump(mode="json")); aqui
        # faltava.
        payload = data.model_dump(
            exclude_unset=True,
            mode="json"
        )

        if "blocos" in payload:
            blocos = payload.pop("blocos")
            payload["config"] = {"blocos": blocos}

        return DreTemplateRepository.update(db, template, payload)

    @staticmethod
    def delete_template(db, current_user, template_id):

        template = DreService.get_template(
            db, current_user, template_id
        )

        DreTemplateRepository.delete(db, template)

        return {"message": "Modelo removido"}

    # ------------------------------------------------------------
    # GERAÇÃO DO DRE
    # ------------------------------------------------------------

    @staticmethod
    def _data_efetiva(item, campo_pagamento):

        return getattr(item, campo_pagamento) or item.vencimento

    @staticmethod
    def _mapa_banco_por_lancamento(db, tenant_id, ids, campo_fk):
        """Devolve {lancamento_id: bank_account_id} pros ids informados,
        via o vínculo de conciliação — só lançamentos já conciliados com
        uma transação bancária têm banco associado; os demais caem no
        grupo "Sem conta vinculada" (ver nome_linha em `gerar`)."""

        if not ids:
            return {}

        campo = getattr(BankReconciliation, campo_fk)

        linhas = (
            db.query(
                campo,
                BankTransaction.bank_account_id,
            )
            .join(
                BankTransaction,
                BankTransaction.id
                == BankReconciliation.bank_transaction_id
            )
            .filter(
                BankReconciliation.tenant_id == tenant_id,
                campo.in_(ids),
            )
            .all()
        )

        return {
            lancamento_id: bank_account_id
            for lancamento_id, bank_account_id in linhas
        }

    @staticmethod
    def gerar(db, current_user, params):

        client_id = DreService._resolve_client_id(
            current_user, params.client_id
        )

        client = DreService._validar_cliente(
            db, current_user, client_id
        )

        template = None

        if params.template_id:
            template = DreService.get_template(
                db, current_user, params.template_id
            )

        payables = (
            db.query(AccountsPayable)
            .filter(
                AccountsPayable.tenant_id == current_user.tenant_id,
                AccountsPayable.client_id == client_id,
                AccountsPayable.status == "PAGO",
            )
            .all()
        )

        receivables = (
            db.query(AccountsReceivable)
            .filter(
                AccountsReceivable.tenant_id == current_user.tenant_id,
                AccountsReceivable.client_id == client_id,
                AccountsReceivable.status == "RECEBIDO",
            )
            .all()
        )

        payables = [
            p for p in payables
            if DreService._data_efetiva(
                p, "data_pagamento"
            ).year == params.ano
        ]

        receivables = [
            r for r in receivables
            if DreService._data_efetiva(
                r, "data_recebimento"
            ).year == params.ano
        ]

        banco_por_payable = {}
        banco_por_receivable = {}

        precisa_banco = (
            params.modo in ("BANCO", "BANCO_CATEGORIA")
            or params.bank_account_id
        )

        if precisa_banco:

            banco_por_payable = DreService._mapa_banco_por_lancamento(
                db,
                current_user.tenant_id,
                [p.id for p in payables],
                "accounts_payable_id",
            )

            banco_por_receivable = DreService._mapa_banco_por_lancamento(
                db,
                current_user.tenant_id,
                [r.id for r in receivables],
                "accounts_receivable_id",
            )

        if params.bank_account_id:

            payables = [
                p for p in payables
                if banco_por_payable.get(p.id)
                == params.bank_account_id
            ]

            receivables = [
                r for r in receivables
                if banco_por_receivable.get(r.id)
                == params.bank_account_id
            ]

        # Nomes de categoria e conta bancária, resolvidos de uma vez só.
        category_ids = {p.category_id for p in payables} | {
            r.category_id for r in receivables
        }

        categorias = {
            c.id: c.nome
            for c in db.query(ExpenseCategory).filter(
                ExpenseCategory.id.in_(category_ids)
            ).all()
        } if category_ids else {}

        contas_ids = (
            set(banco_por_payable.values())
            | set(banco_por_receivable.values())
        )
        contas_ids.discard(None)

        contas = {
            c.id: f"{c.banco} • {c.conta}"
            for c in db.query(BankAccount).filter(
                BankAccount.id.in_(contas_ids)
            ).all()
        } if contas_ids else {}

        # Subcategoria é um detalhe OPCIONAL exibido abaixo da categoria
        # (pedido do usuário: "se a categoria tem subcategoria deve ser
        # uma escolha mostrar também abaixo das categorias") — só faz
        # sentido no modo CATEGORIA, então o backend sempre calcula (é
        # barato, já estamos iterando os lançamentos) e o frontend decide
        # se exibe ou não via um toggle, sem precisar de outro parâmetro.
        subcategory_ids = {
            p.subcategory_id for p in payables if p.subcategory_id
        } | {
            r.subcategory_id for r in receivables if r.subcategory_id
        }

        subcategorias_nomes = {
            s.id: s.nome
            for s in db.query(ExpenseSubcategory).filter(
                ExpenseSubcategory.id.in_(subcategory_ids)
            ).all()
        } if subcategory_ids else {}

        bloco_por_categoria = {}

        if template and params.modo == "CATEGORIA":

            for bloco in (template.config or {}).get("blocos", []):
                for cat_id in bloco.get("category_ids", []):
                    bloco_por_categoria[str(cat_id)] = bloco["nome"]

        def nome_linha(item, banco_id):

            categoria_nome = categorias.get(
                item.category_id, "Sem categoria"
            )

            if params.modo == "CATEGORIA":
                return bloco_por_categoria.get(
                    str(item.category_id), categoria_nome
                )

            banco_nome = contas.get(banco_id, "Sem conta vinculada")

            if params.modo == "BANCO":
                return banco_nome

            return f"{banco_nome} › {categoria_nome}"

        # Acumula valor por (tipo, nome_linha) num dict só — cada chave
        # vira uma linha do relatório, com 12 posições (uma por mês).
        acumulado = defaultdict(lambda: [Decimal("0")] * 12)

        # Mesma ideia, um nível abaixo: (tipo, nome_linha, nome_subcat)
        # — só populado no modo CATEGORIA e só para lançamentos que têm
        # subcategoria definida (ver comentário acima).
        acumulado_sub = defaultdict(lambda: [Decimal("0")] * 12)

        def acumula_subcategoria(item, tipo, nome):

            if params.modo != "CATEGORIA" or not item.subcategory_id:
                return

            sub_nome = subcategorias_nomes.get(item.subcategory_id)

            if not sub_nome:
                return

            mes = DreService._data_efetiva(
                item,
                "data_pagamento" if tipo == "DESPESA"
                else "data_recebimento"
            ).month - 1

            acumulado_sub[(tipo, nome, sub_nome)][mes] += item.valor

        for p in payables:

            banco_id = banco_por_payable.get(p.id)

            nome = nome_linha(p, banco_id)

            mes = DreService._data_efetiva(
                p, "data_pagamento"
            ).month - 1

            acumulado[("DESPESA", nome)][mes] += p.valor

            acumula_subcategoria(p, "DESPESA", nome)

        for r in receivables:

            banco_id = banco_por_receivable.get(r.id)

            nome = nome_linha(r, banco_id)

            mes = DreService._data_efetiva(
                r, "data_recebimento"
            ).month - 1

            acumulado[("RECEITA", nome)][mes] += r.valor

            acumula_subcategoria(r, "RECEITA", nome)

        linhas_receita = []
        linhas_despesa = []

        for (tipo, nome), valores in acumulado.items():

            subcategorias = [
                {
                    "nome": sub_nome,
                    "tipo": tipo,
                    "valores_mensais": sub_valores,
                    "total": sum(sub_valores),
                }
                for (sub_tipo, sub_linha, sub_nome), sub_valores
                in acumulado_sub.items()
                if sub_tipo == tipo and sub_linha == nome
            ]

            subcategorias.sort(key=lambda linha: -linha["total"])

            linha = {
                "nome": nome,
                "tipo": tipo,
                "valores_mensais": valores,
                "total": sum(valores),
                "subcategorias": subcategorias,
            }

            if tipo == "RECEITA":
                linhas_receita.append(linha)
            else:
                linhas_despesa.append(linha)

        linhas_receita.sort(key=lambda linha: -linha["total"])
        linhas_despesa.sort(key=lambda linha: -linha["total"])

        totais_receita = [
            sum(linha["valores_mensais"][m] for linha in linhas_receita)
            for m in range(12)
        ]

        totais_despesa = [
            sum(linha["valores_mensais"][m] for linha in linhas_despesa)
            for m in range(12)
        ]

        totais_resultado = [
            totais_receita[m] - totais_despesa[m] for m in range(12)
        ]

        return {
            "cliente_nome": client.nome_fantasia or client.razao_social,
            "ano": params.ano,
            "modo": params.modo,
            "meses": MESES,
            "linhas_receita": linhas_receita,
            "linhas_despesa": linhas_despesa,
            "totais_receita": totais_receita,
            "totais_despesa": totais_despesa,
            "totais_resultado": totais_resultado,
            "receita_anual": sum(totais_receita),
            "despesa_anual": sum(totais_despesa),
            "resultado_anual": sum(totais_resultado),
            "cor_destaque": template.cor_destaque if template else None,
        }
