from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..modelos import Cita, Medico, Paciente
from ..seguridad import requiere, auditar

router = APIRouter(tags=["citas"])


class MedicoIn(BaseModel):
    nombre: str = Field(min_length=2)
    especialidad: str = Field(min_length=2)
    sede: str = Field(min_length=2)


class CitaIn(BaseModel):
    id_paciente: int = Field(gt=0)
    id_medico: int = Field(gt=0)
    inicio: datetime
    fin: datetime
    consultorio: str = Field(min_length=1)


@router.post("/medicos", status_code=201)
def crear_medico(m: MedicoIn, db: Session = Depends(get_db), u=Depends(requiere("medicos:gestionar"))):
    medico = Medico(**m.model_dump())
    db.add(medico)
    db.flush()
    auditar(db, u.id, "MEDICO_CREADO", f"medico:{medico.id}")
    db.commit()
    return {"id": medico.id}


@router.get("/medicos")
def listar_medicos(especialidad: str | None = None, db: Session = Depends(get_db),
                   u=Depends(requiere("citas:leer"))):
    consulta = select(Medico).where(Medico.activo.is_(True))
    if especialidad:
        consulta = consulta.where(Medico.especialidad.ilike(especialidad))
    return db.scalars(consulta).all()


@router.get("/medicos/{id_medico}/ocupacion")
def ocupacion(id_medico: int, fecha: datetime, db: Session = Depends(get_db),
              u=Depends(requiere("citas:leer"))):
    """Franjas ya tomadas de un medico en un dia. Lo que no aparece esta libre."""
    desde = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    consulta = (select(Cita.inicio, Cita.fin)
                .where(Cita.id_medico == id_medico, Cita.estado != "CANCELADA",
                       Cita.inicio >= desde, Cita.inicio < desde + timedelta(days=1))
                .order_by(Cita.inicio))
    return [{"inicio": i, "fin": f} for i, f in db.execute(consulta)]


@router.post("/citas", status_code=201)
def agendar(datos: CitaIn, db: Session = Depends(get_db), u=Depends(requiere("citas:crear"))):
    if datos.fin <= datos.inicio:
        raise HTTPException(422, "La hora final debe ser posterior a la inicial")
    if db.get(Paciente, datos.id_paciente) is None:
        raise HTTPException(404, "Paciente no encontrado")
    medico = db.get(Medico, datos.id_medico)
    if medico is None or not medico.activo:
        raise HTTPException(404, "Médico no encontrado o sin agenda activa")

    cita = Cita(**datos.model_dump())
    try:
        db.add(cita)
        db.flush()
        auditar(db, u.id, "CITA_CREADA", f"cita:{cita.id}")
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # la base de datos es la que decide si hay cruce, asi funciona tambien con peticiones simultaneas
        if "cita_sin_cruces" in str(e.orig):
            raise HTTPException(409, "El médico ya tiene una cita en esa franja")
        raise
    return {
        "id": cita.id, "paciente": datos.id_paciente, "medico": medico.nombre,
        "inicio": cita.inicio, "fin": cita.fin, "consultorio": cita.consultorio,
    }


@router.post("/citas/{id_cita}/cancelar")
def cancelar(id_cita: int, motivo: str, db: Session = Depends(get_db), u=Depends(requiere("citas:cancelar"))):
    if not motivo.strip():
        raise HTTPException(422, "Debe indicar el motivo de la cancelación")
    cita = db.get(Cita, id_cita)
    if cita is None:
        raise HTTPException(404, "Cita no encontrada")
    if cita.estado != "PROGRAMADA":
        raise HTTPException(409, "Solo se pueden cancelar citas programadas")
    cita.estado = "CANCELADA"
    cita.motivo_cancel = motivo.strip()
    auditar(db, u.id, "CITA_CANCELADA", f"cita:{cita.id}")
    db.commit()
    return {"id": cita.id, "estado": cita.estado}
