import pytest
from fastapi import HTTPException

from app.routers.historia import validar_cie10
from app.seguridad import hashear, verificar


def test_cie10_valido():
    assert validar_cie10(" j06.9 ") == "J06.9"


@pytest.mark.parametrize("codigo", ["", "123", "J0", "J06.999", "' OR 1=1 --"])
def test_cie10_invalido(codigo):
    with pytest.raises(HTTPException):
        validar_cie10(codigo)


def test_hash_no_es_la_clave():
    h = hashear("secreta123")
    assert h != "secreta123"
    assert verificar("secreta123", h)
    assert not verificar("otra", h)
