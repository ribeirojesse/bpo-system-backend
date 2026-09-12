from sqlalchemy import func

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


class PortalService:

    @staticmethod
    def get_dashboard(db, current_user):

        client_id = current_user.client_id

        saldo_contas = db.query(
            func.coalesce(func.sum(BankAccount.saldo_inicial), 0)
        ).filter(
            BankAccount.client_id == client_id
        ).scalar()

        total_pago = db.query(
            func.coalesce(func.sum(AccountsPayable.valor), 0)
        ).filter(
            AccountsPayable.client_id == client_id,
            AccountsPayable.status == "PAGO"
        ).scalar()

        total_a_pagar = db.query(
            func.coalesce(func.sum(AccountsPayable.valor), 0)
        ).filter(
            AccountsPayable.client_id == client_id,
            AccountsPayable.status == "PENDENTE"
        ).scalar()

        total_recebido = db.query(
            func.coalesce(func.sum(AccountsReceivable.valor), 0)
        ).filter(
            AccountsReceivable.client_id == client_id,
            AccountsReceivable.status == "RECEBIDO"
        ).scalar()

        total_a_receber = db.query(
            func.coalesce(func.sum(AccountsReceivable.valor), 0)
        ).filter(
            AccountsReceivable.client_id == client_id,
            AccountsReceivable.status == "PENDENTE"
        ).scalar()

        contas_bancarias = db.query(BankAccount).filter(
            BankAccount.client_id == client_id
        ).all()

        return {
            "saldo_contas": saldo_contas,
            "total_pago": total_pago,
            "total_recebido": total_recebido,
            "total_a_pagar": total_a_pagar,
            "total_a_receber": total_a_receber,
            "contas_bancarias": contas_bancarias,
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
