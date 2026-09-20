from decimal import Decimal

from app.models.bank_account import BankAccount
from app.models.accounts_payable import AccountsPayable
from app.models.accounts_receivable import AccountsReceivable
from app.models.financial_contact import FinancialContact
from app.models.expense_category import ExpenseCategory
from app.models.expense_subcategory import ExpenseSubcategory


# Todas as consultas aqui são escopadas por current_user.client_id — NUNCA
# por tenant_id. O portal do CLIENTE só pode ver o que pertence ao único
# client ao qual aquele login está preso (ver ck_users_role_scope). Isso é
# diferente de todo o resto do sistema (rotas /clients, /accounts-*,
# /bank-*, etc.), que é escopado por tenant_id e restrito a ADMIN.

MESES_PT = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]

# Teto de séries coloridas do gráfico de categoria/subcategoria/fornecedor
# — mesma regra usada no Dashboard do ADMIN (paleta categórica validada
# pela dataviz skill). Acima disso, o resto vira "Outras"/"Outros".
BREAKDOWN_SERIES_CAP = 6


class PortalService:

    @staticmethod
    def get_dashboard(db, current_user):

        client_id = current_user.client_id

        payables_pagos = db.query(AccountsPayable).filter(
            AccountsPayable.client_id == client_id,
            AccountsPayable.status == "PAGO"
        ).all()

        receivables_recebidos = db.query(AccountsReceivable).filter(
            AccountsReceivable.client_id == client_id,
            AccountsReceivable.status == "RECEBIDO"
        ).all()

        total_pago = sum(
            (p.valor for p in payables_pagos), Decimal("0")
        )

        total_recebido = sum(
            (r.valor for r in receivables_recebidos), Decimal("0")
        )

        # Sem saldo em conta aqui de propósito (pedido do usuário: "não
        # monitoramos saldo em conta") — a lista de contas continua só
        # pra mostrar quais existem (banco/agência/conta), sem somar
        # nenhum valor de saldo.
        contas_bancarias = db.query(BankAccount).filter(
            BankAccount.client_id == client_id
        ).all()

        category_ids = (
            {p.category_id for p in payables_pagos} |
            {r.category_id for r in receivables_recebidos}
        )

        subcategory_ids = (
            {p.subcategory_id for p in payables_pagos if p.subcategory_id} |
            {r.subcategory_id for r in receivables_recebidos if r.subcategory_id}
        )

        contact_ids = {p.financial_contact_id for p in payables_pagos}

        categorias = {
            c.id: c.nome
            for c in db.query(ExpenseCategory).filter(
                ExpenseCategory.id.in_(category_ids)
            ).all()
        } if category_ids else {}

        subcategorias = {
            s.id: s.nome
            for s in db.query(ExpenseSubcategory).filter(
                ExpenseSubcategory.id.in_(subcategory_ids)
            ).all()
        } if subcategory_ids else {}

        fornecedores = {
            c.id: c.nome
            for c in db.query(FinancialContact).filter(
                FinancialContact.id.in_(contact_ids)
            ).all()
        } if contact_ids else {}

        def montar_breakdown(itens, campo, lookup, rotulo_vazio):

            totais = {}

            for item in itens:

                chave = getattr(item, campo)

                totais[chave] = (
                    totais.get(chave, Decimal("0")) + item.valor
                )

            linhas = sorted(
                (
                    {
                        "id": str(chave) if chave else "sem-valor",
                        "nome": (
                            lookup.get(chave, rotulo_vazio)
                            if chave else rotulo_vazio
                        ),
                        "valor": valor,
                        "outros": False,
                    }
                    for chave, valor in totais.items()
                ),
                key=lambda linha: linha["valor"],
                reverse=True
            )

            topo = linhas[:BREAKDOWN_SERIES_CAP]

            resto = linhas[BREAKDOWN_SERIES_CAP:]

            resto_total = sum(
                (linha["valor"] for linha in resto), Decimal("0")
            )

            if resto_total > 0:

                topo.append({
                    "id": "outras",
                    "nome": "Outras",
                    "valor": resto_total,
                    "outros": True,
                })

            return topo

        despesas_por_categoria = montar_breakdown(
            payables_pagos, "category_id", categorias, "Sem categoria"
        )

        despesas_por_subcategoria = montar_breakdown(
            payables_pagos, "subcategory_id", subcategorias, "Sem subcategoria"
        )

        receitas_por_categoria = montar_breakdown(
            receivables_recebidos, "category_id", categorias, "Sem categoria"
        )

        receitas_por_subcategoria = montar_breakdown(
            receivables_recebidos, "subcategory_id", subcategorias, "Sem subcategoria"
        )

        maiores_fornecedores = montar_breakdown(
            payables_pagos, "financial_contact_id", fornecedores, "Sem fornecedor"
        )

        evolucao_por_mes = {}

        def acumular_evolucao(itens, campo_data, chave_serie):

            for item in itens:

                data_efetiva = (
                    getattr(item, campo_data) or item.vencimento
                )

                if not data_efetiva:
                    continue

                chave = (data_efetiva.year, data_efetiva.month)

                entrada = evolucao_por_mes.setdefault(
                    chave,
                    {"pago": Decimal("0"), "recebido": Decimal("0")}
                )

                entrada[chave_serie] += item.valor

        acumular_evolucao(
            payables_pagos, "data_pagamento", "pago"
        )

        acumular_evolucao(
            receivables_recebidos, "data_recebimento", "recebido"
        )

        evolucao_ordenada = sorted(evolucao_por_mes.items())[-6:]

        evolucao_mensal = [
            {
                "mes": MESES_PT[mes - 1],
                "pago": valores["pago"],
                "recebido": valores["recebido"],
            }
            for (ano, mes), valores in evolucao_ordenada
        ]

        return {
            "total_pago": total_pago,
            "total_recebido": total_recebido,
            "saldo_periodo": total_recebido - total_pago,
            "contas_bancarias": contas_bancarias,
            "despesas_por_categoria": despesas_por_categoria,
            "despesas_por_subcategoria": despesas_por_subcategoria,
            "receitas_por_categoria": receitas_por_categoria,
            "receitas_por_subcategoria": receitas_por_subcategoria,
            "maiores_fornecedores": maiores_fornecedores,
            "evolucao_mensal": evolucao_mensal,
        }

    @staticmethod
    def get_lancamentos(
        db,
        current_user,
        skip: int = 0,
        limit: int = 100
    ):

        client_id = current_user.client_id

        payables = db.query(AccountsPayable).filter(
            AccountsPayable.client_id == client_id
        ).all()

        receivables = db.query(AccountsReceivable).filter(
            AccountsReceivable.client_id == client_id
        ).all()

        contact_ids = {p.financial_contact_id for p in payables} | {
            r.financial_contact_id for r in receivables
        }

        category_ids = {p.category_id for p in payables} | {
            r.category_id for r in receivables
        }

        contacts = {
            c.id: c.nome
            for c in db.query(FinancialContact).filter(
                FinancialContact.id.in_(contact_ids)
            ).all()
        } if contact_ids else {}

        categories = {
            c.id: c.nome
            for c in db.query(ExpenseCategory).filter(
                ExpenseCategory.id.in_(category_ids)
            ).all()
        } if category_ids else {}

        lancamentos = []

        for p in payables:
            lancamentos.append({
                "id": p.id,
                "tipo": "PAGAR",
                "descricao": p.descricao,
                "valor": p.valor,
                "vencimento": p.vencimento,
                "data_liquidacao": p.data_pagamento,
                "competencia": p.competencia,
                "status": p.status,
                "fornecedor_nome": contacts.get(p.financial_contact_id),
                "categoria_nome": categories.get(p.category_id),
            })

        for r in receivables:
            lancamentos.append({
                "id": r.id,
                "tipo": "RECEBER",
                "descricao": r.descricao,
                "valor": r.valor,
                "vencimento": r.vencimento,
                "data_liquidacao": r.data_recebimento,
                "competencia": r.competencia,
                "status": r.status,
                "fornecedor_nome": contacts.get(r.financial_contact_id),
                "categoria_nome": categories.get(r.category_id),
            })

        lancamentos.sort(
            key=lambda item: item["vencimento"],
            reverse=True
        )

        return lancamentos[skip:skip + limit]

    @staticmethod
    def get_fornecedores(db, current_user):

        return db.query(FinancialContact).filter(
            FinancialContact.client_id == current_user.client_id
        ).order_by(FinancialContact.nome).all()

    @staticmethod
    def get_categorias(db, current_user):

        categorias = db.query(ExpenseCategory).filter(
            ExpenseCategory.client_id == current_user.client_id
        ).order_by(ExpenseCategory.nome).all()

        if not categorias:
            return []

        category_ids = [c.id for c in categorias]

        subcategorias = db.query(ExpenseSubcategory).filter(
            ExpenseSubcategory.category_id.in_(category_ids)
        ).all()

        by_category = {}

        for sub in subcategorias:
            by_category.setdefault(sub.category_id, []).append(sub)

        resultado = []

        for categoria in categorias:

            resultado.append({
                "id": categoria.id,
                "nome": categoria.nome,
                "ativo": categoria.ativo,
                "subcategorias": by_category.get(categoria.id, []),
            })

        return resultado

    @staticmethod
    def get_contas_bancarias(db, current_user):

        return db.query(BankAccount).filter(
            BankAccount.client_id == current_user.client_id
        ).all()
