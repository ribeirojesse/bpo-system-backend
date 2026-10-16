"""Importa contas a pagar/receber exportadas do sistema financeiro antigo.

Uso (dentro do container da API):

    python scripts/importar_legado.py \\
        --arquivo import/apae_pagar.xlsx \\
        --tipo pagar \\
        --cliente "APAE" \\
        --tag apae-2026-10

Sem `--aplicar` o script só simula: lê a planilha, resolve cliente,
categorias e contatos, mostra o resumo e NÃO grava nada. Com `--aplicar`
grava tudo numa única transação (ou entra tudo, ou nada).

Planilha esperada (uma aba, primeira linha de cabeçalho):

    Nome do fornecedor | Data de competência | Descrição |
    Valor pago da parcela (R$) | Conta bancária | Categoria

Como cada linha vira lançamento:

  - a data da planilha vira vencimento, data de pagamento/recebimento e
    competência (MM/AAAA) — o status entra como PAGO/RECEBIDO;
  - categoria e contato são procurados pelo nome no cadastro do cliente
    (sem diferenciar acento/caixa) e criados quando não existem;
  - linha sem nome de contato vai para "NAO INFORMADO";
  - a conta bancária da planilha fica na observação: no sistema a conta
    de um lançamento vem do vínculo de conciliação com o extrato, que
    não existe para dado importado;
  - a observação também leva uma etiqueta [importado:<tag>:<hash>], que
    é o que torna o script seguro de rodar de novo: linha já importada
    com a mesma etiqueta é pulada em vez de duplicar.

Para desfazer uma importação inteira, apague por essa etiqueta:

    DELETE FROM accounts_payable WHERE observacao LIKE '%[importado:apae-2026-10:%';
"""

import argparse
import hashlib
import os
import sys
import unicodedata

from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

# Rodando como "python scripts/importar_legado.py", o Python coloca
# scripts/ no sys.path — não a raiz do projeto —, então "app" não seria
# encontrado. Com a raiz na frente, o script funciona de qualquer pasta
# e sem precisar de PYTHONPATH.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

from openpyxl import load_workbook  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402

# Os relacionamentos dos models são declarados por NOME ("Tenant",
# "Client"...). Importando só alguns, o SQLAlchemy não acha os outros na
# hora de montar o mapper e quebra com "failed to locate a name". A API
# normal não sofre disso porque carrega tudo pelas rotas; aqui, o script
# registra o pacote inteiro antes de qualquer consulta.
import importlib  # noqa: E402
import pkgutil  # noqa: E402

import app.models as _models  # noqa: E402

for _modulo in pkgutil.iter_modules(_models.__path__):
    importlib.import_module(f"app.models.{_modulo.name}")

from app.models.accounts_payable import AccountsPayable  # noqa: E402
from app.models.accounts_receivable import (  # noqa: E402
    AccountsReceivable
)
from app.models.client import Client  # noqa: E402
from app.models.expense_category import ExpenseCategory  # noqa: E402
from app.models.financial_contact import (  # noqa: E402
    FinancialContact
)


CONTATO_PADRAO = "NAO INFORMADO"

LIMITE_VALOR = Decimal("99999999.99")

# Chaves do dicionário devolvido por `preparar_linha` — o que cada linha
# da planilha vira, antes de virar registro no banco.
# (data, valor, descricao, contato, categoria, conta, marca)


def normalizar(texto):
    """Sem acento, sem espaço duplo, em caixa alta — usado só para
    comparar nomes já cadastrados com os da planilha."""

    texto = unicodedata.normalize("NFKD", str(texto or ""))

    texto = "".join(
        c for c in texto if not unicodedata.combining(c)
    )

    return " ".join(texto.upper().split())


def parse_data(valor):

    if valor is None:
        return None

    if hasattr(valor, "date"):
        return valor.date()

    if hasattr(valor, "year"):
        return valor

    texto = str(valor).strip()

    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    return None


def parse_valor(valor):

    if valor is None:
        return None

    if isinstance(valor, (int, float, Decimal)):
        try:
            return Decimal(str(valor)).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None

    texto = str(valor).strip().replace("R$", "").replace(" ", "")

    if not texto:
        return None

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def marca_da_linha(tipo, numero, data, valor, descricao,
                   contato, categoria):
    """Identidade da linha dentro da planilha. Entra na observação como
    [importado:<tag>:<marca>] e é o que faz uma segunda rodada do mesmo
    arquivo pular o que já entrou, em vez de duplicar.

    O número da linha faz parte da assinatura de propósito: duas contas
    de água iguais no mesmo dia são lançamentos diferentes e precisam
    das duas entrar."""

    assinatura = "|".join([
        tipo,
        str(numero),
        data.isoformat(),
        f"{valor:.2f}",
        normalizar(descricao),
        normalizar(contato),
        normalizar(categoria),
    ])

    return hashlib.sha1(
        assinatura.encode("utf-8")
    ).hexdigest()[:12]


def preparar_linha(tipo, bruta):
    """Converte uma linha da planilha no que vai pro banco. Devolve
    (dados, problema): um dos dois é sempre None."""

    (
        numero,
        nome_contato,
        data_bruta,
        descricao,
        valor_bruto,
        conta,
        categoria_nome,
    ) = bruta

    data = parse_data(data_bruta)

    valor = parse_valor(valor_bruto)

    descricao = " ".join(str(descricao or "").split())

    if data is None:
        return None, f"linha {numero}: data inválida ({data_bruta!r})"

    if valor is None or valor <= 0:
        return None, f"linha {numero}: valor inválido ({valor_bruto!r})"

    if valor > LIMITE_VALOR:
        return None, (
            f"linha {numero}: valor acima do limite do campo ({valor})"
        )

    if not descricao:
        descricao = str(
            categoria_nome or "Lançamento importado"
        ).strip()

    contato = str(nome_contato or CONTATO_PADRAO).strip()[:150]

    categoria = str(categoria_nome or "SEM CATEGORIA").strip()[:120]

    return {
        "numero": numero,
        "data": data,
        "valor": valor,
        "descricao": descricao[:200],
        "contato": contato,
        "categoria": categoria,
        "conta": str(conta or "").strip() or None,
        "competencia": f"{data.month:02d}/{data.year}",
        "marca": marca_da_linha(
            tipo, numero, data, valor, descricao,
            contato, categoria
        ),
    }, None


def resumo_por_mes(preparadas):
    """{'01/2025': (quantidade, soma)} — é o recorte que dá pra comparar
    com o relatório do sistema antigo."""

    por_mes = {}

    for item in preparadas:

        quantidade, soma = por_mes.get(
            item["competencia"], (0, Decimal("0.00"))
        )

        por_mes[item["competencia"]] = (
            quantidade + 1,
            soma + item["valor"],
        )

    return por_mes


def ordem_competencia(competencia):

    mes, ano = competencia.split("/")

    return (int(ano), int(mes))


def resumo_por_categoria(preparadas):

    por_categoria = {}

    for item in preparadas:

        chave = normalizar(item["categoria"])

        quantidade, soma, nome = por_categoria.get(
            chave, (0, Decimal("0.00"), item["categoria"])
        )

        por_categoria[chave] = (
            quantidade + 1,
            soma + item["valor"],
            nome,
        )

    return por_categoria


def ler_planilha(caminho):
    """Devolve [(numero_da_linha, contato, data, descricao, valor,
    conta, categoria)] — só as linhas com algum conteúdo."""

    wb = load_workbook(caminho, data_only=True)

    ws = wb.active

    linhas = []

    for numero in range(2, ws.max_row + 1):

        valores = [
            ws.cell(row=numero, column=coluna).value
            for coluna in range(1, 7)
        ]

        if all(
            v is None or str(v).strip() == ""
            for v in valores
        ):
            continue

        linhas.append((numero, *valores))

    return ws.title, linhas


def resolver_cliente(db, procurado):
    """Aceita o id do cliente ou parte do nome (sem diferenciar
    acento/caixa). Nome ambíguo para a execução: melhor parar do que
    importar na empresa errada."""

    try:
        cliente_id = UUID(str(procurado).strip())
    except (ValueError, AttributeError, TypeError):
        cliente_id = None

    if cliente_id is not None:

        cliente = (
            db.query(Client)
            .filter(Client.id == cliente_id)
            .first()
        )

        if not cliente:
            sys.exit(f"Nenhum cliente com o id {procurado}.")

        return cliente

    clientes = db.query(Client).all()

    alvo = normalizar(procurado)

    achados = [
        c for c in clientes
        if alvo in normalizar(c.nome_fantasia)
        or alvo in normalizar(c.razao_social)
    ]

    if not achados:
        sys.exit(
            f"Nenhum cliente encontrado para \"{procurado}\". "
            "Rode com --listar-clientes para ver os nomes."
        )

    if len(achados) > 1:
        nomes = ", ".join(
            f"{c.nome_fantasia or c.razao_social} ({c.id})"
            for c in achados
        )
        sys.exit(
            f"\"{procurado}\" casa com mais de um cliente: {nomes}. "
            "Use o nome completo ou o id."
        )

    return achados[0]


def conferir(db, args, cliente, Modelo, linhas):
    """Confere o que entrou no banco contra a planilha: quantidade,
    soma e totais por competência. Não grava nada."""

    preparadas = []

    problemas = []

    for bruta in linhas:

        dados, problema = preparar_linha(args.tipo, bruta)

        if problema:
            problemas.append(problema)
        else:
            preparadas.append(dados)

    registros = db.query(
        Modelo.valor,
        Modelo.competencia,
        Modelo.observacao,
    ).filter(
        Modelo.tenant_id == cliente.tenant_id,
        Modelo.client_id == cliente.id,
        Modelo.observacao.like(f"%[importado:{args.tag}:%"),
    ).all()

    total_banco = sum(
        (Decimal(str(r[0])) for r in registros),
        Decimal("0.00")
    )

    total_planilha = sum(
        (item["valor"] for item in preparadas),
        Decimal("0.00")
    )

    print("Conferência planilha x banco")
    print(f"   etiqueta        : {args.tag}")
    print(
        f"   na planilha     : {len(preparadas):>5} lanç.  "
        f"R$ {total_planilha:>14,.2f}"
    )
    print(
        f"   no banco        : {len(registros):>5} lanç.  "
        f"R$ {total_banco:>14,.2f}"
    )

    if problemas:
        print(
            f"   fora da conta   : {len(problemas)} linha(s) "
            "ignorada(s) na planilha"
        )

    bate = (
        len(registros) == len(preparadas)
        and total_banco == total_planilha
    )

    print()
    print("   " + ("TUDO BATENDO" if bate else "DIVERGENTE"))

    # Por competência, pra achar onde está a diferença.
    por_mes_planilha = resumo_por_mes(preparadas)

    por_mes_banco = {}

    for valor, competencia, _obs in registros:

        quantidade, soma = por_mes_banco.get(
            competencia, (0, Decimal("0.00"))
        )

        por_mes_banco[competencia] = (
            quantidade + 1,
            soma + Decimal(str(valor)),
        )

    competencias = sorted(
        set(por_mes_planilha) | set(por_mes_banco),
        key=ordem_competencia
    )

    print()
    print(
        "   competência   planilha                 banco"
    )

    for competencia in competencias:

        qp, sp = por_mes_planilha.get(
            competencia, (0, Decimal("0.00"))
        )

        qb, sb = por_mes_banco.get(
            competencia, (0, Decimal("0.00"))
        )

        marcador = "  " if (qp, sp) == (qb, sb) else " <-"

        print(
            f"   {competencia}   {qp:>5} R$ {sp:>13,.2f}   "
            f"{qb:>5} R$ {sb:>13,.2f}{marcador}"
        )


def main():

    parser = argparse.ArgumentParser(
        description="Importa planilha do sistema antigo"
    )

    parser.add_argument("--arquivo")

    parser.add_argument(
        "--tipo",
        choices=["pagar", "receber"],
    )

    parser.add_argument("--cliente")

    parser.add_argument(
        "--tag",
        help="Etiqueta da importação (vai na observação)"
    )

    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Grava de verdade (sem isso, só simula)"
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=0,
        help="Importa só as N primeiras linhas (teste)"
    )

    parser.add_argument(
        "--listar-clientes",
        action="store_true"
    )

    parser.add_argument(
        "--conferir",
        action="store_true",
        help=(
            "Compara o que está no banco (pela etiqueta) com a "
            "planilha, sem gravar nada"
        )
    )

    args = parser.parse_args()

    db = SessionLocal()

    try:

        if args.listar_clientes:

            for c in db.query(Client).all():
                print(
                    f"{c.id}  {c.nome_fantasia or ''} | "
                    f"{c.razao_social or ''}"
                )

            return

        for obrigatorio in ("arquivo", "tipo", "cliente", "tag"):

            if not getattr(args, obrigatorio):
                sys.exit(
                    f"--{obrigatorio} é obrigatório "
                    "(ou use --listar-clientes)"
                )

        cliente = resolver_cliente(db, args.cliente)

        aba, linhas = ler_planilha(args.arquivo)

        if args.limite:
            linhas = linhas[:args.limite]

        print(
            f"Cliente : {cliente.nome_fantasia or cliente.razao_social}"
            f" ({cliente.id})"
        )
        print(f"Tenant  : {cliente.tenant_id}")
        print(f"Arquivo : {args.arquivo} · aba \"{aba}\"")
        print(f"Linhas  : {len(linhas)}")
        print(f"Tipo    : {args.tipo} · etiqueta {args.tag}")
        print()

        Modelo = (
            AccountsPayable if args.tipo == "pagar"
            else AccountsReceivable
        )

        if args.conferir:

            conferir(db, args, cliente, Modelo, linhas)

            return

        campo_liquidacao = (
            "data_pagamento" if args.tipo == "pagar"
            else "data_recebimento"
        )

        status = "PAGO" if args.tipo == "pagar" else "RECEBIDO"

        tipo_contato = (
            "PAGAR" if args.tipo == "pagar" else "RECEBER"
        )

        # ------------------------------------------------------------
        # Cadastros existentes do cliente
        # ------------------------------------------------------------

        categorias = {
            normalizar(c.nome): c
            for c in db.query(ExpenseCategory).filter(
                ExpenseCategory.tenant_id == cliente.tenant_id,
                ExpenseCategory.client_id == cliente.id,
            ).all()
        }

        contatos = {
            normalizar(c.nome): c
            for c in db.query(FinancialContact).filter(
                FinancialContact.tenant_id == cliente.tenant_id,
                FinancialContact.client_id == cliente.id,
            ).all()
        }

        # Etiquetas já gravadas: é o que impede duplicar numa segunda
        # rodada do mesmo arquivo.
        ja_importados = set()

        for (observacao,) in db.query(Modelo.observacao).filter(
            Modelo.tenant_id == cliente.tenant_id,
            Modelo.client_id == cliente.id,
            Modelo.observacao.like(f"%[importado:{args.tag}:%"),
        ).all():

            marca = observacao.split(f"[importado:{args.tag}:")[-1]

            ja_importados.add(marca.split("]")[0])

        categorias_novas = []

        contatos_novos = []

        criados = 0

        repetidos = 0

        total = Decimal("0.00")

        problemas = []

        preparadas = []

        for bruta in linhas:

            dados, problema = preparar_linha(args.tipo, bruta)

            if problema:
                problemas.append(problema)
                continue

            preparadas.append(dados)

        for dados in preparadas:

            if dados["marca"] in ja_importados:
                repetidos += 1
                continue

            # --- categoria ---
            chave_categoria = normalizar(dados["categoria"])

            categoria = categorias.get(chave_categoria)

            if categoria is None:

                categoria = ExpenseCategory(
                    tenant_id=cliente.tenant_id,
                    client_id=cliente.id,
                    nome=dados["categoria"],
                    ativo=True,
                )

                db.add(categoria)

                db.flush()

                categorias[chave_categoria] = categoria

                categorias_novas.append(categoria.nome)

            # --- contato ---
            chave_contato = normalizar(dados["contato"])

            contato = contatos.get(chave_contato)

            if contato is None:

                contato = FinancialContact(
                    tenant_id=cliente.tenant_id,
                    client_id=cliente.id,
                    nome=dados["contato"],
                    tipo=tipo_contato,
                    ativo=True,
                )

                db.add(contato)

                db.flush()

                contatos[chave_contato] = contato

                contatos_novos.append(contato.nome)

            elif contato.tipo not in (tipo_contato, "AMBOS"):
                # Mesmo nome usado nos dois lados: passa a valer pros
                # dois em vez de ficar marcado só como um.
                contato.tipo = "AMBOS"

            # --- observação ---
            partes = ["Importado do sistema antigo"]

            if dados["conta"]:
                partes.append(f"Conta {dados['conta']}")

            partes.append(
                f"[importado:{args.tag}:{dados['marca']}]"
            )

            campos = {
                "tenant_id": cliente.tenant_id,
                "client_id": cliente.id,
                "financial_contact_id": contato.id,
                "category_id": categoria.id,
                "subcategory_id": None,
                "descricao": dados["descricao"],
                "valor": dados["valor"],
                "vencimento": dados["data"],
                "competencia": dados["competencia"],
                "status": status,
                "observacao": " · ".join(partes)[:400],
                campo_liquidacao: dados["data"],
            }

            db.add(Modelo(**campos))

            criados += 1

            total += dados["valor"]

        # ------------------------------------------------------------
        # Resumo
        # ------------------------------------------------------------

        print(f"A criar          : {criados} lançamento(s)")
        print(f"Soma             : R$ {total:,.2f}")
        print(f"Já importados    : {repetidos} (etiqueta {args.tag})")
        print(f"Categorias novas : {len(categorias_novas)}")

        if categorias_novas:
            print("   " + ", ".join(sorted(set(categorias_novas))[:20]))

        print(f"Contatos novos   : {len(contatos_novos)}")

        if contatos_novos:
            print("   " + ", ".join(sorted(set(contatos_novos))[:15]))

        por_mes = resumo_por_mes(preparadas)

        print()
        print("Totais por competência (confira com o sistema antigo):")

        for competencia in sorted(por_mes, key=ordem_competencia):

            quantidade, soma = por_mes[competencia]

            print(
                f"   {competencia}  {quantidade:>5} lanç.  "
                f"R$ {soma:>14,.2f}"
            )

        por_categoria = resumo_por_categoria(preparadas)

        print()
        print("Maiores categorias:")

        maiores = sorted(
            por_categoria.values(),
            key=lambda item: item[1],
            reverse=True
        )[:15]

        for quantidade, soma, nome in maiores:
            print(
                f"   {nome[:34]:<34} {quantidade:>5} lanç.  "
                f"R$ {soma:>14,.2f}"
            )

        print()

        if problemas:
            print(f"Linhas ignoradas : {len(problemas)}")
            for p in problemas[:15]:
                print("   " + p)
            if len(problemas) > 15:
                print(f"   ... e mais {len(problemas) - 15}")

        print()

        if args.aplicar:

            db.commit()

            print("GRAVADO.")

        else:

            db.rollback()

            print(
                "SIMULAÇÃO — nada foi gravado. "
                "Rode de novo com --aplicar para valer."
            )

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()
