from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .modelos import Usuario, Auditoria

bearer = HTTPBearer(auto_error=False)

# permisos por rol, formato "modulo:accion"
PERMISOS = {
    "admin": {"usuarios:gestionar", "auditoria:leer", "pacientes:leer", "medicos:gestionar", "citas:leer"},
    "admisiones": {"pacientes:leer", "pacientes:escribir", "citas:leer", "citas:crear", "citas:cancelar"},
    "medico": {"pacientes:leer", "citas:leer", "historia:leer", "historia:escribir"},
    "enfermeria": {"pacientes:leer", "citas:leer", "historia:leer"},
}


def hashear(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


def verificar(clave: str, clave_hash: str) -> bool:
    return bcrypt.checkpw(clave.encode(), clave_hash.encode())


def crear_token(usuario: Usuario) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.MINUTOS_TOKEN)
    return jwt.encode({"sub": str(usuario.id), "rol": usuario.rol, "exp": exp},
                      config.SECRET_KEY, algorithm="HS256")


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                   db: Session = Depends(get_db)) -> Usuario:
    if cred is None:
        raise HTTPException(401, "Falta iniciar sesión")
    try:
        datos = jwt.decode(cred.credentials, config.SECRET_KEY, algorithms=["HS256"])
        sub = int(datos["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(401, "La sesión expiró, ingrese de nuevo")
    usuario = db.get(Usuario, sub)
    if usuario is None or not usuario.activo:
        raise HTTPException(401, "Usuario no válido")
    return usuario


def requiere(permiso: str):
    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if permiso not in PERMISOS.get(usuario.rol, set()):
            raise HTTPException(403, "No tiene permiso para esta acción")
        return usuario
    return dependencia


def auditar(db: Session, id_usuario: int | None, accion: str, recurso: str):
    db.add(Auditoria(id_usuario=id_usuario, accion=accion, recurso=recurso))
