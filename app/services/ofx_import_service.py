import hashlib

from ofxparse import OfxParser

from app.models.bank_transaction import (
    BankTransaction
)

from app.models.bank_account import (
    BankAccount
)

from app.services.auto_reconciliation_service import (
    AutoReconciliationService
)


class OFXImportService:

    @staticmethod
    def detectar_encoding(caminho):

        with open(caminho, "rb") as f:

            header = (
                f.read(500)
                .decode(
                    "latin-1",
                    errors="ignore"
                )
                .upper()
            )

            if "CHARSET:1252" in header:
                return "cp1252"

            if "ISO-8859-1" in header:
                return "latin-1"

        return "latin-1"

    @staticmethod
    def carregar_ofx(caminho):

        encoding = (
            OFXImportService.detectar_encoding(
                caminho
            )
        )

        with open(
            caminho,
            encoding=encoding,
            errors="ignore"
        ) as f:

            return OfxParser.parse(f)

    @staticmethod
    def gerar_hash(
        data,
        valor,
        descricao,
        conta
    ):

        conteudo = (
            f"{data}_{valor}_{descricao}_{conta}"
        )

        return hashlib.md5(
            conteudo.encode()
        ).hexdigest()

    @staticmethod
    def importar(
        db,
        current_user,
        caminho_arquivo
    ):

        ofx = (
            OFXImportService.carregar_ofx(
                caminho_arquivo
            )
        )

        total_importadas = 0

        for conta in ofx.accounts:

            account_id = conta.account_id

            bank_account = db.query(
                BankAccount
            ).filter(
                BankAccount.conta == account_id,
                BankAccount.tenant_id ==
                current_user.tenant_id
            ).first()

            if not bank_account:
                continue

            for t in conta.statement.transactions:

                descricao = (
                    t.memo
                    or
                    t.payee
                    or
                    "Sem descrição"
                )

                valor = float(t.amount)

                hash_transacao = (
                    OFXImportService.gerar_hash(
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
                    hash_transacao
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