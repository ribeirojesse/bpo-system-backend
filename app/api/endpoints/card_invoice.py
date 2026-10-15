import json
import os

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException
)

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.files import gerar_nome_seguro
from app.core.rate_limit import rate_limit

from app.dependencies.auth import (
    require_role
)

from app.models.user import User

from app.repositories.bank_transaction_repository import (
    BankTransactionRepository
)

from app.services.ai_client import AIClient

from app.services.card_invoice_pdf_service import (
    CardInvoicePDFService,
    TIPOS_ACEITOS
)

from app.services.card_invoice_service import (
    CardInvoiceService
)


router = APIRouter()

UPLOAD_DIR = "uploads/card-invoices"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

MAX_FILE_BYTES = 10 * 1024 * 1024

_EXTENSOES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def _get_transaction(db, current_user, transaction_id):

    transaction = BankTransactionRepository.get_by_id(
        db,
        current_user.tenant_id,
        transaction_id
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transação não encontrada"
        )

    return transaction


def _ler_arquivo(file: UploadFile):
    """Lê o upload inteiro em memória (limitado a 10MB) e identifica o
    tipo pelo conteúdo — não confia na extensão nem no Content-Type."""

    conteudo = file.file.read(MAX_FILE_BYTES + 1)

    if len(conteudo) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Arquivo maior que 10MB"
        )

    if not conteudo:
        raise HTTPException(
            status_code=400,
            detail="Arquivo vazio"
        )

    media_type = CardInvoicePDFService.detectar_tipo(conteudo)

    if media_type not in TIPOS_ACEITOS:
        raise HTTPException(
            status_code=400,
            detail="Formato não suportado. Envie PDF, PNG, JPG ou WEBP."
        )

    return conteudo, media_type


@router.get("/capabilities")
def card_invoice_capabilities(
    current_user: User = Depends(require_role("ADMIN"))
):
    """O que a leitura de fatura aceita neste servidor. Sem IA ativada,
    só PDF (leitura automática local); com IA, também imagem."""

    ia = AIClient.habilitado()

    return {
        "ia_habilitada": ia,
        "aceita_imagem": ia,
    }


@router.post(
    "/preview",
    # Pode chamar a IA (custo) — limita por IP.
    dependencies=[Depends(rate_limit("card-invoice-preview", 20, 60))]
)
def preview_card_invoice(
    transaction_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Lê a fatura (com IA quando configurada) e devolve os lançamentos
    pra conferência — não grava lançamento nenhum."""

    transaction = _get_transaction(db, current_user, transaction_id)

    conteudo, media_type = _ler_arquivo(file)

    return CardInvoiceService.pre_visualizar(
        db,
        current_user,
        transaction,
        conteudo,
        media_type
    )


@router.post(
    "/process",
    dependencies=[Depends(rate_limit("card-invoice-process", 20, 60))]
)
def process_card_invoice(
    transaction_id: str = Form(...),
    competencia: str = Form(...),
    file: UploadFile = File(...),
    # Lista conferida na tela (JSON: [{"data", "descricao", "valor",
    # "parcela", "cartao", "subcategory_id"}]). Sem ela, o arquivo é
    # lido de novo.
    itens_json: str | None = Form(None),
    # true = o usuário confirmou na tela que a fatura é desta transação
    # mesmo com banco/final de cartão diferentes.
    confirmar_divergencia: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    transaction = _get_transaction(db, current_user, transaction_id)

    conteudo, media_type = _ler_arquivo(file)

    itens_confirmados = None

    if itens_json:

        try:
            itens_confirmados = json.loads(itens_json)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Lista de itens inválida"
            )

        if (
            not isinstance(itens_confirmados, list)
            or len(itens_confirmados) > 2000
        ):
            raise HTTPException(
                status_code=400,
                detail="Lista de itens inválida"
            )

    # Guarda a fatura original (nome aleatório, nunca o do usuário).
    nome_seguro = gerar_nome_seguro(
        f"arquivo{_EXTENSOES[media_type]}"
    )

    caminho = f"{UPLOAD_DIR}/{nome_seguro}"

    with open(caminho, "wb") as buffer:
        buffer.write(conteudo)

    return CardInvoiceService.processar(
        db,
        current_user,
        transaction,
        conteudo,
        media_type,
        competencia,
        itens_confirmados,
        confirmar_divergencia
    )
