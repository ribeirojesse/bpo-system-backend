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
from app.core.files import gerar_nome_seguro, limpar_uploads_antigos
from app.core.rate_limit import rate_limit

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


MAX_FILE_BYTES = 10 * 1024 * 1024

# Quantos dias o arquivo original fica guardado no servidor. As transações
# já estão no banco; o arquivo só serve para conferência recente.
DIAS_RETENCAO = 30

MODOS_VALIDOS = {"VERIFICAR", "IGNORAR", "SUBSTITUIR"}


def _ler_ofx(file: UploadFile) -> bytes:
    """Lê o upload em memória (limitado a 10MB) e confere pelo conteúdo
    que é mesmo um extrato OFX — não confia em extensão nem Content-Type."""

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

    # Arquivo binário (PDF, imagem, executável...) nunca é OFX.
    if b"\x00" in conteudo[:4096]:
        raise HTTPException(
            status_code=400,
            detail="Arquivo não é um extrato OFX válido"
        )

    inicio = conteudo[:4096].upper()

    if b"OFXHEADER" not in inicio and b"<OFX" not in inicio:
        raise HTTPException(
            status_code=400,
            detail="Arquivo não é um extrato OFX válido"
        )

    return conteudo


@router.post(
    "/import",
    dependencies=[Depends(rate_limit("ofx-import", 20, 60))]
)
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

    if (modo or "VERIFICAR").upper() not in MODOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail="Modo de importação inválido"
        )

    conteudo = _ler_ofx(file)

    # Extensão fixa: o nome enviado pelo usuário nunca decide o que vai
    # para o disco.
    nome_seguro = gerar_nome_seguro("extrato.ofx")

    caminho = (
        f"{UPLOAD_DIR}/{nome_seguro}"
    )

    with open(caminho, "wb") as buffer:
        buffer.write(conteudo)

    # Manutenção oportunista (não há cron no projeto): descarta extratos
    # antigos a cada importação.
    limpar_uploads_antigos(UPLOAD_DIR, DIAS_RETENCAO)

    return OFXImportService.importar(
        db,
        current_user,
        caminho,
        bank_account_id,
        modo
    )
