"""Pruebas del servicio de pedidos (casos 6 a 9 de la sección 9.2)."""

import pytest

from app.services.order_service import CheckoutToken, InvalidCheckoutTokenError


def test_token_de_confirmacion_es_de_un_solo_uso():
    session = {}
    checkout = CheckoutToken(session)
    token = checkout.issue(total=25000)

    assert checkout.consume(token) == 25000
    with pytest.raises(InvalidCheckoutTokenError):
        checkout.consume(token)


def test_tokens_emitidos_son_distintos_y_el_nuevo_reemplaza_al_anterior():
    session = {}
    checkout = CheckoutToken(session)
    first = checkout.issue(total=1000)
    second = checkout.issue(total=2000)

    assert first != second
    with pytest.raises(InvalidCheckoutTokenError):
        checkout.consume(first)


@pytest.mark.parametrize("submitted", [None, "", "token-falso", "ñandú", 123])
def test_token_invalido_se_rechaza_y_descarta_el_vigente(submitted):
    session = {}
    checkout = CheckoutToken(session)
    token = checkout.issue(total=1000)

    with pytest.raises(InvalidCheckoutTokenError):
        checkout.consume(submitted)
    with pytest.raises(InvalidCheckoutTokenError):
        checkout.consume(token)


@pytest.mark.parametrize("stored", [None, "corrupto", {"token": "abc"}, {"total": 5}])
def test_token_corrupto_en_la_sesion_se_rechaza(stored):
    session = {} if stored is None else {CheckoutToken.KEY: stored}

    with pytest.raises(InvalidCheckoutTokenError):
        CheckoutToken(session).consume("abc")
