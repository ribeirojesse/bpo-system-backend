"""Regra de senha aplicada ao CRIAR ou TROCAR senhas (nunca no login:
senhas antigas continuam entrando até serem trocadas)."""

import secrets
import string

from typing import Annotated, Optional

from pydantic import AfterValidator, BeforeValidator, Field


MIN_LENGTH = 10
MAX_LENGTH = 128

_FRACAS = {
    "1234567890",
    "123456789a",
    "senha12345",
    "password123",
    "qwerty12345",
    "cliente@123",
    "admin12345",
}


def validar_senha(valor: str) -> str:

    if len(valor) < MIN_LENGTH:
        raise ValueError(
            f"A senha deve ter pelo menos {MIN_LENGTH} caracteres"
        )

    if not any(c.isalpha() for c in valor):
        raise ValueError("A senha deve conter pelo menos uma letra")

    if not any(c.isdigit() for c in valor):
        raise ValueError("A senha deve conter pelo menos um número")

    if valor.lower() in _FRACAS:
        raise ValueError("Senha muito comum. Escolha outra")

    return valor


# Tipo reutilizável nos schemas: `password: SenhaForte`.
SenhaForte = Annotated[
    str,
    Field(max_length=MAX_LENGTH),
    AfterValidator(validar_senha),
]


def _vazio_vira_none(valor):

    return None if valor == "" else valor


# Para campos de troca de senha opcionais: string vazia (formulário sem a
# senha preenchida) significa "não trocar", não "senha inválida".
SenhaOpcional = Annotated[
    Optional[SenhaForte],
    BeforeValidator(_vazio_vira_none),
]


def gerar_senha_temporaria(tamanho: int = 16) -> str:
    """Senha aleatória (letras + números + símbolo) usada quando um acesso
    é criado sem senha informada. Cumpre a regra acima."""

    alfabeto = string.ascii_letters + string.digits

    while True:

        senha = "".join(secrets.choice(alfabeto) for _ in range(tamanho))

        senha += secrets.choice("!@#$%&*")

        try:
            return validar_senha(senha)
        except ValueError:
            continue
