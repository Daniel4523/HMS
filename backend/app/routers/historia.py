import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..modelos import HistoriaClinica, Evolucion
from ..seguridad import requiere, auditar

router = APIRouter(prefix="/historia", tags=["historia clínica"])

CIE10 = re.compile(r"^[A-Z][0-9]{2}(\.[0-9A-Z]{1,2})?$")


class EvolucionIn(BaseModel):
    motivo: str = Field(min_length=3)
    nota: str = Field(min_length=3)
    diagnostico_cie10: str


def validar_cie10(codigo: str) -> str:
    codigo = codigo.strip().upper()
    if not CIE10.match(codigo):
        raise HTTPException(422, "Código CIE-10 no válido (ejemplo: J06.9)")
    return codigo


def historia_de(db: Session, id_paciente: int) -> HistoriaClinica:
    h = db.scalar(select(HistoriaClinica).where(HistoriaClinica.id_paciente == id_paciente))
    if h is None:
        raise HTTPException(404, "El paciente no tiene historia clínica")
    return h


@router.get("/{id_paciente}")
def ver(id_paciente: int, db: Session = Depends(get_db), u=Depends(requiere("historia:leer"))):
    h = historia_de(db, id_paciente)
    auditar(db, u.id, "HISTORIA_CONSULTADA", f"paciente:{id_paciente}")
    db.commit()
    return {"id": h.id, "fecha_apertura": h.fecha_apertura, "evoluciones": h.evoluciones}


@router.post("/{id_paciente}/evoluciones", status_code=201)
def registrar(id_paciente: int, datos: EvolucionIn, db: Session = Depends(get_db),
              u=Depends(requiere("historia:escribir"))):
    h = historia_de(db, id_paciente)
    ev = Evolucion(id_historia=h.id, id_medico=u.id, motivo=datos.motivo, nota=datos.nota,
                   diagnostico_cie10=validar_cie10(datos.diagnostico_cie10))
    db.add(ev)
    db.flush()
    auditar(db, u.id, "EVOLUCION_CREADA", f"evolucion:{ev.id}")
    db.commit()
    return {"id": ev.id, "version": ev.version}


@router.post("/evoluciones/{id_evolucion}/corregir", status_code=201)
def corregir(id_evolucion: int, datos: EvolucionIn, db: Session = Depends(get_db),
             u=Depends(requiere("historia:escribir"))):
    """No se edita nada: la correccion queda como una version nueva y la anterior se conserva."""
    base = db.get(Evolucion, id_evolucion)
    if base is None:
        raise HTTPException(404, "Evolución no encontrada")
    raiz = base.id_original or base.id
    ultima = db.scalar(select(Evolucion.version).where(
        (Evolucion.id == raiz) | (Evolucion.id_original == raiz)).order_by(Evolucion.version.desc()))
    nueva = Evolucion(id_historia=base.id_historia, id_medico=u.id, motivo=datos.motivo,
                      nota=datos.nota, diagnostico_cie10=validar_cie10(datos.diagnostico_cie10),
                      version=ultima + 1, id_original=raiz)
    db.add(nueva)
    db.flush()
    auditar(db, u.id, "EVOLUCION_CORREGIDA", f"evolucion:{nueva.id} v{nueva.version}")
    db.commit()
    return {"id": nueva.id, "version": nueva.version}
