from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    require_role
)

from app.models.user import User

from app.schemas.portal import (
    PortalDashboardSchema,
    PortalLancamentoSchema,
    PortalFornecedorSchema,
    PortalCategoriaSchema,
    PortalContaBancariaSchema
)

from app.services.portal_service import PortalService


router = APIRouter()


# Portal do CLIENTE: só-leitura, sempre escopado a current_user.client_id
# (nunca tenant_id). Nenhuma rota aqui cria, edita ou exclui nada — é
# exatamente o "não editar, apenas ver" pedido para esse perfil.


@router.get(
    "/dashboard",
    response_model=PortalDashboardSchema
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("CLIENTE"))
):

    return PortalService.get_dashboard(db, current_user)


@router.get(
    "/lancamentos",
    response_model=list[PortalLancamentoSchema]
)
def get_lancamentos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("CLIENTE"))
):

    return PortalService.get_lancamentos(
        db,
        current_user,
        skip,
        limit
    )


@router.get(
    "/fornecedores",
    response_model=list[PortalFornecedorSchema]
)
def get_fornecedores(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("CLIENTE"))
):

    return PortalService.get_fornecedores(db, current_user)


@router.get(
    "/categorias",
    response_model=list[PortalCategoriaSchema]
)
def get_categorias(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("CLIENTE"))
):

    return PortalService.get_categorias(db, current_user)


@router.get(
    "/contas-bancarias",
    response_model=list[PortalContaBancariaSchema]
)
def get_contas_bancarias(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("CLIENTE"))
):

    return PortalService.get_contas_bancarias(db, current_user)
