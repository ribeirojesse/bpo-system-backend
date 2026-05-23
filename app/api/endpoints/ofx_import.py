import os
import shutil

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    get_current_user
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
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    caminho = (
        f"{UPLOAD_DIR}/{file.filename}"
    )

    with open(caminho, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    resultado = OFXImportService.importar(
        db,
        current_user,
        caminho
    )

    return resultado