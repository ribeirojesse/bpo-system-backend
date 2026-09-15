from typing import Optional

from datetime import date

from decimal import Decimal

import uuid

from pydantic import BaseModel


class BankReconciliationFromTransactionSchema(BaseModel):
    """Concilia uma transação bancária criando, no mesmo passo, o
    lançamento financeiro (conta a pagar ou a receber) correspondente —
    já finalizado como PAGO/RECEBIDO, sem etapa de confirmação
    separada."""

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID] = None

    competencia: Optional[str] = None

    observacao: Optional[str] = None


class BankReconciliationCreateSchema(BaseModel):

    bank_transaction_id: uuid.UUID

    accounts_payable_id: Optional[uuid.UUID] = None

    accounts_receivable_id: Optional[uuid.UUID] = None

    valor_conciliado: Decimal

    data_conciliacao: date

    observacao: Optional[str] = None


class BankReconciliationResponseSchema(BaseModel):

    id: uuid.UUID

    bank_transaction_id: uuid.UUID

    accounts_payable_id: Optional[uuid.UUID]

    accounts_receivable_id: Optional[uuid.UUID]

    valor_conciliado: Decimal

    data_conciliacao: date

    observacao: Optional[str]

    class Config:
        from_attributes = True


class ReconciliationMatchSchema(BaseModel):
    """Um lançamento (conta a pagar ou a receber) já existente, ainda não
    vinculado a nenhuma conciliação, que parece corresponder à transação
    bancária — mesmo cliente, mesmo valor, e vencimento igual (EXATO) ou
    próximo (PROXIMO). Espelha o "Encontramos"/"Quase lá" do Conta Azul."""

    tipo: str  # "PAYABLE" ou "RECEIVABLE"

    id: uuid.UUID

    descricao: str

    valor: Decimal

    vencimento: date

    financial_contact_id: uuid.UUID

    category_id: uuid.UUID

    subcategory_id: Optional[uuid.UUID] = None

    confianca: str  # "EXATO" ou "PROXIMO"


class ReconciliationSuggestionSchema(BaseModel):

    transaction_id: uuid.UUID

    match: Optional[ReconciliationMatchSchema] = None

    # Preenchidos só quando NÃO há "match" (nenhum lançamento existente
    # pra vincular): contato/categoria/subcategoria mais usados em
    # lançamentos com descrição parecida com a da transação — usados só
    # pra pré-preencher o formulário de "Criar lançamento", nunca pra
    # vincular sozinho.
    sugestao_financial_contact_id: Optional[uuid.UUID] = None

    sugestao_category_id: Optional[uuid.UUID] = None

    sugestao_subcategory_id: Optional[uuid.UUID] = None