from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..modelos import Auditoria
from ..seguridad import requiere

router = APIRouter(prefix="/auditoria", tags=["auditoría"])


@router.get("")
def consultar(desde: datetime | None = None, hasta: datetime | None = None,
              id_usuario: int | None = None, accion: str | None = None,
              db: Session = Depends(get_db), u=Depends(requiere("auditoria:leer"))):
    consulta = select(Auditoria).order_by(Auditoria.fecha.desc()).limit(500)
    if desde:
        consulta = consulta.where(Auditoria.fecha >= desde)
    if hasta:
        consulta = consulta.where(Auditoria.fecha <= hasta)
    if id_usuario:
        consulta = consulta.where(Auditoria.id_usuario == id_usuario)
    if accion:
        consulta = consulta.where(Auditoria.accion == accion)
    return db.scalars(consulta).all()
