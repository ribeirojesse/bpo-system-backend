import os
import shutil

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form
)

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.files import gerar_nome_seguro

from app.dependencies.auth import (
    require_role
)

from app.models.user import User

from app.services.ofx_import_service import (
    OFXImportService
)


router = APIRouter()

UPLOAD_DIR = "uploads/ofx"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


@router.post("/import")
def import_ofx(
    file: UploadFile = File(...),
    # Conta bancária escolhida pelo usuário na tela de importação. Antes
    # esse campo vinha do frontend mas era ignorado pelo backend, que
    # tentava adivinhar a conta casando o número informado no OFX com o
    # cadastro — e pulava silenciosamente (sem importar nada) qualquer
    # conta cujo número no extrato não batesse exatamente com o cadastro
    # (ex.: zeros à esquerda, máscara diferente). Agora usamos a conta que
    # a pessoa efetivamente selecionou.
    bank_account_id: str = Form(...),
    # VERIFICAR (padrão): se o arquivo tiver transações já importadas,
    # não grava nada e responde 409 com o resumo, pra tela perguntar.
    # IGNORAR: grava só as novas. SUBSTITUIR: troca as antigas pelas do
    # arquivo (exceto as já conciliadas). Ver OFXImportService.importar.
    modo: str = Form("VERIFICAR"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN")
    )
):

    nome_seguro = gerar_nome_seguro(file.filename)

    caminho = (
        f"{UPLOAD_DIR}/{nome_seguro}"
    )

    with open(caminho, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    return OFXImportService.importar(
        db,
        current_user,
        caminho,
        bank_account_id,
        modo
    )
