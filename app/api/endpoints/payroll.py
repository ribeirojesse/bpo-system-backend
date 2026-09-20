import os
import shutil

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

from app.services.payroll_service import (
    PayrollService
)



router = APIRouter()

UPLOAD_DIR = "uploads/payroll"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


@router.post("/process")
def process_payroll(
    transaction_id: str = Form(...),
    competencia: str = Form(...),
    category_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):

    transaction = BankTransactionRepository.get_by_id(
        db,
        current_user.tenant_id,
        transaction_id
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    nome_seguro = gerar_nome_seguro(file.filename)

    caminho = f"{UPLOAD_DIR}/{nome_seguro}"

    with open(caminho, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return PayrollService.processar_pdf(
        db,
        current_user,
        transaction,
        caminho,
        competencia,
        category_id
    )
