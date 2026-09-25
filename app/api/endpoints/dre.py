from fastapi import (
    APIRouter,
    Depends
)

from fastapi.responses import Response

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.auth import (
    require_role
)

from app.models.user import User

from app.schemas.dre import (
    DreTemplateCreateSchema,
    DreTemplateUpdateSchema,
    DreTemplateResponseSchema,
    DreGerarRequestSchema,
    LancamentosExcelRequestSchema,
    DreResultadoSchema
)

from app.services.dre_service import DreService

from app.services.dre_pdf_service import DrePdfService

from app.services import dre_excel_service


router = APIRouter()


# Relatório de DRE — disponível tanto pro ADMIN (qualquer cliente da
# carteira, informando client_id) quanto pro próprio CLIENTE no portal
# (sempre escopado ao próprio client_id — ver DreService._resolve_
# client_id e DreService.get_template).


@router.post(
    "/templates",
    response_model=DreTemplateResponseSchema
)
def create_template(
    data: DreTemplateCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "CLIENTE"))
):

    template = DreService.create_template(
        db, current_user, data
    )

    return DreTemplateResponseSchema.from_model(template)


@router.get(
    "/templates",
    response_model=list[DreTemplateResponseSchema]
)
def list_templates(
    client_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "CLIENTE"))
):

    templates = DreService.list_templates(
        db, current_user, client_id
    )

    return [
        DreTemplateResponseSchema.from_model(t)
        for t in templates
    ]


@router.put(
    "/templates/{template_id}",
    response_model=DreTemplateResponseSchema
)
def update_template(
    template_id: str,
    data: DreTemplateUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "CLIENTE"))
):

    template = DreService.update_template(
        db, current_user, template_id, data
    )

    return DreTemplateResponseSchema.from_model(template)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "CLIENTE"))
):

    return DreService.delete_template(
        db, current_user, template_id
    )


@router.post(
    "/gerar",
    response_model=DreResultadoSchema
)
def gerar_dre(
    params: DreGerarRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "CLIENTE"))
):

    return DreService.gerar(db, current_user, params)


@router.post("/gerar/pdf")
def gerar_dre_pdf(
    params: DreGerarRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "CLIENTE"))
):

    dados = DreService.gerar(db, current_user, params)

    pdf_bytes = DrePdfService.gerar(dados)

    nome_arquivo = (
        f"DRE_{dados['cliente_nome']}_{dados['ano']}.pdf"
        .replace(" ", "_")
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="{nome_arquivo}"'
        }
    )


@router.post("/lancamentos/excel")
def exportar_lancamentos_excel(
    params: LancamentosExcelRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "CLIENTE"))
):
    """Planilha .xlsx com os lançamentos pagos/recebidos do período
    personalizado (único filtro), um por linha. ADMIN informa o cliente;
    CLIENTE sempre recebe só os próprios lançamentos."""

    dados = DreService.listar_lancamentos(
        db,
        current_user,
        params.client_id,
        params.data_inicio,
        params.data_fim
    )

    conteudo = dre_excel_service.gerar(dados)

    nome = dre_excel_service.nome_arquivo(
        dados["cliente_nome"],
        dados["data_inicio"],
        dados["data_fim"]
    )

    return Response(
        content=conteudo,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{nome}"'
        }
    )
