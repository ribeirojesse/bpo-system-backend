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

    @staticmethod
    def importar(
        db,
        current_user,
        caminho_arquivo,
        bank_account_id
    ):

        # A conta bancária é a que o usuário escolheu explicitamente na
        # tela de importação — não tentamos mais "adivinhar" casando o
        # número da conta dentro do arquivo OFX com o cadastro, porque
        # bancos costumam formatar esse número de forma diferente do que
        # foi digitado no cadastro (zeros à esquerda, máscara, dígito
        # verificador), e uma divergência de formatação fazia a conta
        # inteira ser pulada em silêncio, sem importar nenhuma transação e
        # sem avisar o usuário do motivo.
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

        total_importadas = 0

        for conta in ofx.accounts:

            account_id = conta.account_id

            for t in conta.statement.transactions:

                valor = float(t.amount)

                if valor == 0:
                    # Linhas de saldo ("Saldo Anterior", "Saldo do dia")
                    # não são movimentações reais — não faz sentido
                    # gravar como transação bancária.
                    continue

                descricao = (
                    t.memo
                    or
                    t.payee
                    or
                    "Sem descrição"
                )

                hash_transacao = (
                    BankTransactionService.gerar_hash(
                        current_user.tenant_id,
                        t.date,
                        valor,
                        descricao,
                        account_id
                    )
                )

                existente = db.query(
                    BankTransaction
                ).filter(
                    BankTransaction.hash_transacao
                    ==
                    hash_transacao,

                    BankTransaction.tenant_id
                    ==
                    current_user.tenant_id
                ).first()

                if existente:
                    continue

                transaction = BankTransaction(
                    tenant_id=current_user.tenant_id,
                    client_id=bank_account.client_id,
                    bank_account_id=bank_account.id,
                    data_transacao=t.date,
                    descricao=descricao,
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
                    hash_transacao=hash_transacao
                )

                db.add(transaction)

                db.flush()

                AutoReconciliationService.conciliar_transacao(
                    db,
                    transaction
                )

                total_importadas += 1

        db.commit()

        return {
            "message": (
                "Importação concluída"
            ),
            "importadas": total_importadas
        }
