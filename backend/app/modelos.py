from datetime import datetime, date

from sqlalchemy import (String, Text, Integer, BigInteger, Date, DateTime, ForeignKey,
                        CheckConstraint, UniqueConstraint, text, func)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Usuario(Base):
    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    login: Mapped[str] = mapped_column(String(50), unique=True)
    clave_hash: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(20))
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activo: Mapped[bool] = mapped_column(default=True)


class Paciente(Base):
    __tablename__ = "paciente"
    __table_args__ = (UniqueConstraint("tipo_doc", "num_doc", name="paciente_documento_unico"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo_doc: Mapped[str] = mapped_column(String(5))
    num_doc: Mapped[str] = mapped_column(String(20))
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    fecha_nac: Mapped[date] = mapped_column(Date)
    telefono: Mapped[str] = mapped_column(String(20))
    correo: Mapped[str | None] = mapped_column(String(120))
    eps: Mapped[str] = mapped_column(String(80))
    regimen: Mapped[str] = mapped_column(String(15))


class Medico(Base):
    __tablename__ = "medico"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    especialidad: Mapped[str] = mapped_column(String(60))
    sede: Mapped[str] = mapped_column(String(60))
    activo: Mapped[bool] = mapped_column(default=True)


class Cita(Base):
    __tablename__ = "cita"
    __table_args__ = (
        CheckConstraint("fin > inicio", name="cita_fin_mayor_inicio"),
        # un medico no puede tener dos citas activas que se solapen
        ExcludeConstraint(
            ("id_medico", "="),
            (text("tstzrange(inicio, fin)"), "&&"),
            name="cita_sin_cruces",
            using="gist",
            where=text("estado <> 'CANCELADA'"),
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_paciente: Mapped[int] = mapped_column(ForeignKey("paciente.id"))
    id_medico: Mapped[int] = mapped_column(ForeignKey("medico.id"))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consultorio: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(15), default="PROGRAMADA")
    motivo_cancel: Mapped[str | None] = mapped_column(Text)


class HistoriaClinica(Base):
    __tablename__ = "historia_clinica"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_paciente: Mapped[int] = mapped_column(ForeignKey("paciente.id"), unique=True)
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    evoluciones: Mapped[list["Evolucion"]] = relationship(order_by="Evolucion.fecha")


class Evolucion(Base):
    __tablename__ = "evolucion"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_historia: Mapped[int] = mapped_column(ForeignKey("historia_clinica.id"))
    id_medico: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    motivo: Mapped[str] = mapped_column(Text)
    nota: Mapped[str] = mapped_column(Text)
    diagnostico_cie10: Mapped[str] = mapped_column(String(10))
    version: Mapped[int] = mapped_column(Integer, default=1)
    id_original: Mapped[int | None] = mapped_column(ForeignKey("evolucion.id"))


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_usuario: Mapped[int | None] = mapped_column(BigInteger)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accion: Mapped[str] = mapped_column(String(40))
    recurso: Mapped[str] = mapped_column(String(80))
