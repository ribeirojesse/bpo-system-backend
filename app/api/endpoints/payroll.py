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

from app.dependencies.auth import (
    require_role
)

from app.models.user import User

from app.repositories.bank_transaction_repository import (
    BankTransactionRepository
)

from app.services.payroll_pdf_service import (
    PayrollPDFService,
    TIPOS_ACEITOS
)

from app.services.payroll_service import (
    PayrollService
)

from app.services.ai_client import AIClient



router = APIRouter()

UPLOAD_DIR = "uploads/payroll"

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
        raise HTTPException(status_code=404, detail="Transação não encontrada")

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

    media_type = PayrollPDFService.detectar_tipo(conteudo)

    if media_type not in TIPOS_ACEITOS:
        raise HTTPException(
            status_code=400,
            detail="Formato não suportado. Envie PDF, PNG, JPG ou WEBP."
        )

    return conteudo, media_type


@router.get("/capabilities")
def payroll_capabilities(
    current_user: User = Depends(require_role("ADMIN"))
):
    """O que a leitura de folha aceita neste servidor. Sem IA ativada,
    só PDF (leitura automática local); com IA, também imagem."""

    ia = AIClient.habilitado()

    return {
        "ia_habilitada": ia,
        "aceita_imagem": ia,
    }


@router.post("/preview")
def preview_payroll(
    transaction_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Lê o comprovante (com IA quando configurada) e devolve a lista de
    funcionários pra conferência — não grava nada."""

    transaction = _get_transaction(db, current_user, transaction_id)

    conteudo, media_type = _ler_arquivo(file)

    return PayrollService.pre_visualizar(
        db,
        current_user,
        transaction,
        conteudo,
        media_type
    )


@router.post("/process")
def process_payroll(
    transaction_id: str = Form(...),
    competencia: str = Form(...),
    category_id: str = Form(...),
    file: UploadFile = File(...),
    # Lista conferida na tela (JSON: [{"funcionario", "cpf", "valor"}]).
    # Opcional: sem ela, o arquivo é lido de novo (fluxo antigo).
    funcionarios_json: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    transaction = _get_transaction(db, current_user, transaction_id)

    conteudo, media_type = _ler_arquivo(file)

    funcionarios_confirmados = None

    if funcionarios_json:

        try:
            funcionarios_confirmados = json.loads(funcionarios_json)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Lista de funcionários inválida"
            )

        if (
            not isinstance(funcionarios_confirmados, list)
            or len(funcionarios_confirmados) > 2000
        ):
            raise HTTPException(
                status_code=400,
                detail="Lista de funcionários inválida"
            )

    # Guarda o comprovante original (nome aleatório, nunca o do usuário).
    nome_seguro = gerar_nome_seguro(
        f"arquivo{_EXTENSOES[media_type]}"
    )

    caminho = f"{UPLOAD_DIR}/{nome_seguro}"

    with open(caminho, "wb") as buffer:
        buffer.write(conteudo)

    return PayrollService.processar_pdf(
        db,
        current_user,
        transaction,
        conteudo,
        media_type,
        competencia,
        category_id,
        funcionarios_confirmados
    )
