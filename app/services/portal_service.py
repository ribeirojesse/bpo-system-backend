from datetime import date

from decimal import Decimal

from app.models.bank_account import BankAccount
from app.models.accounts_payable import AccountsPayable
from app.models.accounts_receivable import AccountsReceivable
from app.models.financial_contact import FinancialContact
from app.models.expense_category import ExpenseCategory
from app.models.expense_subcategory import ExpenseSubcategory

from app.services.dre_service import DreService


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

        # 12 meses (eram 6): um ano inteiro deixa a sazonalidade visível
        # e é o período que o cliente costuma comparar. O rótulo leva o
        # ano porque a janela cruza a virada ("dez/25" e "dez/26" não
        # podem aparecer iguais).
        evolucao_ordenada = sorted(evolucao_por_mes.items())[-12:]

        evolucao_mensal = [
            {
                "mes": f"{MESES_PT[mes - 1].lower()}/{str(ano)[-2:]}",
                "pago": valores["pago"],
                "recebido": valores["recebido"],
                "resultado": (
                    valores["recebido"] - valores["pago"]
                ),
            }
            for (ano, mes), valores in evolucao_ordenada
        ]

        # ------------------------------------------------------------
        # Fechamento do mês corrente e do anterior (pra comparação)
        # ------------------------------------------------------------

        hoje = date.today()

        def resumo_do_mes(ano, mes):

            valores = evolucao_por_mes.get(
                (ano, mes),
                {"pago": Decimal("0"), "recebido": Decimal("0")}
            )

            return {
                "label": f"{MESES_PT[mes - 1].lower()}/{ano}",
                "recebido": valores["recebido"],
                "pago": valores["pago"],
                "resultado": (
                    valores["recebido"] - valores["pago"]
                ),
            }

        mes_atual = resumo_do_mes(hoje.year, hoje.month)

        ano_anterior = hoje.year if hoje.month > 1 else hoje.year - 1

        mes_anterior = resumo_do_mes(
            ano_anterior,
            hoje.month - 1 if hoje.month > 1 else 12
        )

        # ------------------------------------------------------------
        # Em aberto e próximos vencimentos
        # ------------------------------------------------------------

        payables_pendentes = db.query(AccountsPayable).filter(
            AccountsPayable.client_id == client_id,
            AccountsPayable.status == "PENDENTE"
        ).all()

        receivables_pendentes = db.query(AccountsReceivable).filter(
            AccountsReceivable.client_id == client_id,
            AccountsReceivable.status == "PENDENTE"
        ).all()

        def soma(itens, vencidos=False):

            return sum(
                (
                    item.valor for item in itens
                    if (not vencidos) or (
                        item.vencimento and item.vencimento < hoje
                    )
                ),
                Decimal("0")
            )

        em_aberto = {
            "a_pagar": soma(payables_pendentes),
            "a_receber": soma(receivables_pendentes),
            "a_pagar_vencido": soma(payables_pendentes, True),
            "a_receber_vencido": soma(receivables_pendentes, True),
        }

        pendentes = [
            {
                "id": item.id,
                "tipo": tipo,
                "descricao": item.descricao,
                "valor": item.valor,
                "vencimento": item.vencimento,
                "dias": (item.vencimento - hoje).days,
                "contato_nome": fornecedores.get(
                    item.financial_contact_id
                ),
            }
            for tipo, itens in (
                ("PAGAR", payables_pendentes),
                ("RECEBER", receivables_pendentes),
            )
            for item in itens
            if item.vencimento
        ]

        pendentes.sort(key=lambda item: item["vencimento"])

        proximos_vencimentos = pendentes[:8]

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
            "mes_atual": mes_atual,
            "mes_anterior": mes_anterior,
            "em_aberto": em_aberto,
            "proximos_vencimentos": proximos_vencimentos,
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

        # Conta de cada lançamento: conciliação com o extrato ou lote de
        # folha/fatura de cartão. É o que faz o salário aparecer aqui com
        # a conta de onde saiu.
        contas = {
            c.id: f"{c.banco} • {c.conta}"
            for c in db.query(BankAccount).filter(
                BankAccount.client_id == client_id
            ).all()
        }

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
                "conta_nome": contas.get(
                    banco_por_payable.get(p.id)
                ),
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
                "conta_nome": contas.get(
                    banco_por_receivable.get(r.id)
                ),
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
