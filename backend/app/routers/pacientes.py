from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..modelos import Paciente, HistoriaClinica
from ..seguridad import requiere, auditar

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

REGIMENES = {"CONTRIBUTIVO", "SUBSIDIADO", "ESPECIAL", "PARTICULAR"}
TIPOS_DOC = {"CC", "TI", "CE", "RC", "PA"}


class PacienteIn(BaseModel):
    tipo_doc: str = Field(min_length=2, max_length=5)
    num_doc: str = Field(min_length=4, max_length=20)
    nombres: str = Field(min_length=2)
    apellidos: str = Field(min_length=2)
    fecha_nac: date
    telefono: str = Field(min_length=7, max_length=20)
    correo: str | None = None
    eps: str = Field(min_length=2)
    regimen: str = Field(min_length=2)

    @field_validator("tipo_doc")
    @classmethod
    def validar_tipo_doc(cls, valor: str) -> str:
        if valor not in TIPOS_DOC:
            raise ValueError(f"Tipo de documento no válido ({', '.join(sorted(TIPOS_DOC))})")
        return valor

    @field_validator("regimen")
    @classmethod
    def validar_regimen(cls, valor: str) -> str:
        if valor not in REGIMENES:
            raise ValueError(f"Régimen no válido ({', '.join(sorted(REGIMENES))})")
        return valor

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str | None) -> str | None:
        if valor is not None and "@" not in valor:
            raise ValueError("El correo no tiene un formato válido")
        return valor

    @field_validator("fecha_nac")
    @classmethod
    def validar_fecha(cls, valor: date) -> date:
        if valor > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return valor


class PacienteMod(BaseModel):
    tipo_doc: str | None = Field(default=None, min_length=2, max_length=5)
    num_doc: str | None = Field(default=None, min_length=4, max_length=20)
    nombres: str | None = Field(default=None, min_length=2)
    apellidos: str | None = Field(default=None, min_length=2)
    fecha_nac: date | None = None
    telefono: str | None = Field(default=None, min_length=7, max_length=20)
    correo: str | None = None
    eps: str | None = Field(default=None, min_length=2)
    regimen: str | None = Field(default=None, min_length=2)

    @field_validator("tipo_doc")
    @classmethod
    def validar_tipo_doc(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in TIPOS_DOC:
            raise ValueError(f"Tipo de documento no válido ({', '.join(sorted(TIPOS_DOC))})")
        return valor

    @field_validator("regimen")
    @classmethod
    def validar_regimen(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in REGIMENES:
            raise ValueError(f"Régimen no válido ({', '.join(sorted(REGIMENES))})")
        return valor

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str | None) -> str | None:
        if valor is not None and "@" not in valor:
            raise ValueError("El correo no tiene un formato válido")
        return valor

    @field_validator("fecha_nac")
    @classmethod
    def validar_fecha(cls, valor: date | None) -> date | None:
        if valor is not None and valor > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return valor


def validar(p: PacienteIn):
    if p.tipo_doc not in TIPOS_DOC:
        raise HTTPException(422, f"Tipo de documento no válido ({', '.join(sorted(TIPOS_DOC))})")
    if p.regimen not in REGIMENES:
        raise HTTPException(422, f"Régimen no válido ({', '.join(sorted(REGIMENES))})")
    if p.fecha_nac > date.today():
        raise HTTPException(422, "La fecha de nacimiento no puede ser futura")
    if p.correo and "@" not in p.correo:
        raise HTTPException(422, "El correo no tiene un formato válido")


@router.post("", status_code=201)
def crear(p: PacienteIn, db: Session = Depends(get_db), u=Depends(requiere("pacientes:escribir"))):
    validar(p)
    nuevo = Paciente(**p.model_dump())
    try:
        db.add(nuevo)
        db.flush()
        db.add(HistoriaClinica(id_paciente=nuevo.id))
        auditar(db, u.id, "PACIENTE_CREADO", f"paciente:{nuevo.id}")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe un paciente con ese documento")
    return {"id": nuevo.id}


@router.get("")
def buscar(q: str = Query(min_length=3), db: Session = Depends(get_db),
           u=Depends(requiere("pacientes:leer"))):
    patron = f"%{q}%"
    consulta = select(Paciente).where(or_(
        Paciente.num_doc.ilike(patron),
        Paciente.nombres.ilike(patron),
        Paciente.apellidos.ilike(patron),
    )).limit(50)
    return db.scalars(consulta).all()


@router.get("/{id_paciente}")
def ficha(id_paciente: int, db: Session = Depends(get_db), u=Depends(requiere("pacientes:leer"))):
    p = db.get(Paciente, id_paciente)
    if p is None:
        raise HTTPException(404, "Paciente no encontrado")
    return p


@router.patch("/{id_paciente}")
def modificar(id_paciente: int, cambios: PacienteMod, db: Session = Depends(get_db),
              u=Depends(requiere("pacientes:escribir"))):
    p = db.get(Paciente, id_paciente)
    if p is None:
        raise HTTPException(404, "Paciente no encontrado")
    datos = cambios.model_dump(exclude_none=True)
    if "tipo_doc" in datos and datos["tipo_doc"] not in TIPOS_DOC:
        raise HTTPException(422, f"Tipo de documento no válido ({', '.join(sorted(TIPOS_DOC))})")
    if "regimen" in datos and datos["regimen"] not in REGIMENES:
        raise HTTPException(422, "Régimen no válido")
    if "fecha_nac" in datos and datos["fecha_nac"] > date.today():
        raise HTTPException(422, "La fecha de nacimiento no puede ser futura")
    if "correo" in datos and datos["correo"] is not None and "@" not in datos["correo"]:
        raise HTTPException(422, "El correo no tiene un formato válido")
    try:
        for campo, valor in datos.items():
            setattr(p, campo, valor)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe un paciente con ese documento")
    auditar(db, u.id, "PACIENTE_MODIFICADO", f"paciente:{p.id} campos:{','.join(datos)}")
    db.commit()
    return p
