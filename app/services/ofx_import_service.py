import io
import logging
import re

from fastapi import HTTPException

from ofxparse import OfxParser

from app.models.bank_transaction import (
    BankTransaction
)

from app.repositories.bank_account_repository import (
    BankAccountRepository
)

from app.services.auto_reconciliation_service import (
    AutoReconciliationService
)

from app.services.bank_transaction_service import (
    BankTransactionService
)


logger = logging.getLogger(__name__)

# Algumas linhas de OFX vêm com <FITID></FITID> vazio — normalmente
# marcadores de saldo ("Saldo Anterior", "Saldo do dia") que alguns bancos
# (ex.: Banco do Brasil) incluem no extrato, e não transações de verdade.
# Regex em bytes: a sanitização acontece ANTES de qualquer decodificação,
# operando direto sobre o arquivo cru (ver o comentário em carregar_ofx
# sobre por que não decodificamos nós mesmos).
FITID_VAZIO_RE = re.compile(rb"<FITID>\s*</FITID>", re.IGNORECASE)


class OFXImportService:

    @staticmethod
    def sanitizar_bytes(dados):

        # A lib ofxparse acessa node.fitid.contents[0] ao ler cada
        # transação. Quando a tag <FITID> vem vazia, contents é uma lista
        # vazia e isso derruba o parser com IndexError — que caía no
        # "except Exception" abaixo e virava sempre "Arquivo OFX inválido
        # ou corrompido", mesmo em arquivos perfeitamente válidos.
        # Geramos um FITID sintético só para as tags vazias, sem alterar
        # mais nada do conteúdo original (mexemos direto nos bytes, sem
        # decodificar nada, então nenhum acento é tocado).

        contador = {"n": 0}

        def substituir(match):

            contador["n"] += 1

            return (
                f"<FITID>AUTOFITID-{contador['n']}</FITID>"
            ).encode("ascii")

        return FITID_VAZIO_RE.sub(substituir, dados)

    @staticmethod
    def carregar_ofx(caminho):

        try:

            # A lib ofxparse já sabe ler o cabeçalho OFX (ENCODING/
            # CHARSET) e escolher a decodificação correta sozinha — é
            # assim que ela é documentada pra ser usada (arquivo aberto
            # em modo binário, "rb"). A versão anterior deste serviço
            # decodificava o arquivo em texto antes de entregar pra lib
            # (tentando adivinhar o encoding aqui), e isso conflitava com
            # a própria detecção de encoding da lib: ela lia o cabeçalho
            # de novo e tentava redecodificar um conteúdo que já era
            # texto, quebrando em qualquer caractere acentuado (ou, com
            # certas combinações de cabeçalho, um LookupError de encoding
            # inexistente). Passando bytes crus pra lib, ela decodifica
            # certo na primeira e única vez.
            with open(caminho, "rb") as f:
                dados = f.read()

            dados = OFXImportService.sanitizar_bytes(
                dados
            )

            return OfxParser.parse(
                io.BytesIO(dados)
            )

        except HTTPException:
            raise

        except Exception:

            # Antes o erro real era descartado — agora fica registrado
            # no log do servidor pra facilitar diagnosticar o próximo
            # arquivo problemático, mesmo que o usuário só veja a
            # mensagem genérica.
            logger.exception(
                "Falha ao interpretar arquivo OFX (%s)",
                caminho
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "Arquivo OFX inválido ou corrompido"
                )
            )

    # Como tratar transações do arquivo que já existem no sistema (mesmo
    # hash = mesma data + valor + descrição + conta):
    #   VERIFICAR  -> padrão. Se houver repetidas, NÃO grava nada e devolve
    #                 409 com o resumo, pra tela perguntar o que fazer.
    #   IGNORAR    -> grava só as novas e pula as repetidas (comportamento
    #                 antigo, agora só quando a pessoa escolhe).
    #   SUBSTITUIR -> apaga a transação antiga e grava a do arquivo novo.
    #                 Antigas já conciliadas / processadas na folha são
    #                 mantidas (apagar quebraria o vínculo com o lançamento
    #                 pago/recebido) e a linha do arquivo é pulada.
    MODOS = ("VERIFICAR", "IGNORAR", "SUBSTITUIR")

    @staticmethod
    def _linhas_do_arquivo(ofx, current_user):
        """Transações reais do arquivo, já com o hash calculado."""

        linhas = []

        for conta in ofx.accounts:

            account_id = conta.account_id

            for t in conta.statement.transactions:

                valor = float(t.amount)

                if valor == 0:
                    # Linhas de saldo ("Saldo Anterior", "Saldo do dia")
                    # não são movimentações reais.
                    continue

                descricao = (
                    t.memo
                    or
                    t.payee
                    or
                    "Sem descrição"
                )

                linhas.append({
                    "t": t,
                    "valor": valor,
                    "descricao": descricao,
                    "hash": BankTransactionService.gerar_hash(
                        current_user.tenant_id,
                        t.date,
                        valor,
                        descricao,
                        account_id
                    ),
                })

        return linhas

    @staticmethod
    def importar(
        db,
        current_user,
        caminho_arquivo,
        bank_account_id,
        modo="VERIFICAR"
    ):

        modo = (modo or "VERIFICAR").upper()

        if modo not in OFXImportService.MODOS:
            raise HTTPException(
                status_code=400,
                detail="Modo de importação inválido"
            )

        # A conta bancária é a que o usuário escolheu explicitamente na
        # tela de importação (não adivinhamos pelo número no OFX — bancos
        # formatam diferente do cadastro e a conta acabava pulada em
        # silêncio).
        bank_account = BankAccountRepository.get_by_id(
            db,
            current_user.tenant_id,
            bank_account_id
        )

        if not bank_account:
            raise HTTPException(
                status_code=404,
                detail="Conta bancária não encontrada"
            )

        ofx = (
            OFXImportService.carregar_ofx(
                caminho_arquivo
            )
        )

        linhas = OFXImportService._linhas_do_arquivo(ofx, current_user)

        hashes = list({linha["hash"] for linha in linhas})

        existentes = {
            t.hash_transacao: t
            for t in db.query(BankTransaction).filter(
                BankTransaction.tenant_id == current_user.tenant_id,
                BankTransaction.hash_transacao.in_(hashes)
            ).all()
        } if hashes else {}

        bloqueadas = {
            h: BankTransactionService.motivo_bloqueio_exclusao(db, t)
            for h, t in existentes.items()
        }

        bloqueadas = {h: m for h, m in bloqueadas.items() if m}

        # ---------------- Só verificar: há repetidas? ----------------

        if modo == "VERIFICAR" and existentes:

            repetidas = [l for l in linhas if l["hash"] in existentes]

            raise HTTPException(
                status_code=409,
                detail={
                    "codigo": "OFX_DUPLICADO",
                    "mensagem": (
                        "Parte deste arquivo já foi importada antes."
                    ),
                    "total_arquivo": len(linhas),
                    "novas": len(linhas) - len(repetidas),
                    "repetidas": len(repetidas),
                    # Das repetidas, quantas NÃO podem ser substituídas
                    # (já conciliadas / ligadas à folha).
                    "repetidas_bloqueadas": sum(
                        1 for l in repetidas if l["hash"] in bloqueadas
                    ),
                    "exemplos": [
                        {
                            "data": str(l["t"].date.date())
                            if hasattr(l["t"].date, "date")
                            else str(l["t"].date),
                            "descricao": l["descricao"],
                            "valor": abs(l["valor"]),
                            "tipo": "CREDITO" if l["valor"] > 0 else "DEBITO",
                            "conciliada": l["hash"] in bloqueadas,
                        }
                        for l in repetidas[:5]
                    ],
                }
            )

        # ---------------- Gravar ----------------

        total_importadas = 0
        total_substituidas = 0
        total_ignoradas = 0
        total_mantidas = 0

        # Hashes já tratados nesta importação: a mesma linha repetida
        # dentro do PRÓPRIO arquivo não pode apagar a que acabamos de
        # gravar (e esbarraria na constraint única).
        vistos = set()

        for linha in linhas:

            h = linha["hash"]

            if h in vistos:
                total_ignoradas += 1
                continue

            vistos.add(h)

            antiga = existentes.get(h)

            if antiga is not None:

                if modo != "SUBSTITUIR":
                    total_ignoradas += 1
                    continue

                if h in bloqueadas:
                    total_mantidas += 1
                    continue

                db.delete(antiga)

                db.flush()

                total_substituidas += 1

            t = linha["t"]
            valor = linha["valor"]

            transaction = BankTransaction(
                tenant_id=current_user.tenant_id,
                client_id=bank_account.client_id,
                bank_account_id=bank_account.id,
                data_transacao=t.date,
                descricao=linha["descricao"],
                valor=abs(valor),
                tipo=(
                    "CREDITO"
                    if valor > 0
                    else "DEBITO"
                ),
                documento=(
                    getattr(t, "checknum", None)
                ),
                identificador_externo=(
                    getattr(t, "id", None)
                ),
                saldo=None,
                conciliado=False,
                hash_transacao=h
            )

            db.add(transaction)

            db.flush()

            AutoReconciliationService.conciliar_transacao(
                db,
                transaction
            )

            if antiga is None:
                total_importadas += 1

        db.commit()

        return {
            "message": "Importação concluída",
            # "importadas" = só as novas (mantém o campo que a tela já usa)
            "importadas": total_importadas,
            "substituidas": total_substituidas,
            "ignoradas": total_ignoradas,
            # repetidas que não puderam ser substituídas (já conciliadas)
            "mantidas": total_mantidas,
        }
