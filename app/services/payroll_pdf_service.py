import re

import pdfplumber


class PayrollPDFService:

    @staticmethod
    def extrair_texto(caminho_pdf):

        texto = ""

        with pdfplumber.open(
            caminho_pdf
        ) as pdf:

            for pagina in pdf.pages:

                texto += (
                    pagina.extract_text()
                    or ""
                )

                texto += "\n"

        return texto

    @staticmethod
    def extrair_funcionarios(texto):
        funcionarios = []

        for linha in texto.split("\n"):
            linha = linha.strip()

            if not linha:
                continue

            # pega qualquer valor monetário no final da linha
            match_valor = re.search(r"([\d\.]+,\d{2})\s*$", linha)

            if not match_valor:
                continue

            valor_str = match_valor.group(1)

            try:
                valor = float(
                    valor_str.replace(".", "").replace(",", ".")
                )
            except:
                continue

            if valor <= 0:
                continue

            # remove valor da linha para sobrar só texto
            linha_sem_valor = linha.replace(valor_str, "").strip()

            # remove CPF (se existir)
            linha_sem_valor = re.sub(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", "", linha_sem_valor)

            # limpa múltiplos espaços
            nome = re.sub(r"\s+", " ", linha_sem_valor).strip()

            if len(nome) < 3:
                continue

            funcionarios.append({
                "funcionario": nome,
                "valor": valor
            })

        return funcionarios