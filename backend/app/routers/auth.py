from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..modelos import Usuario
from ..seguridad import verificar, hashear, crear_token, auditar, requiere, PERMISOS

router = APIRouter(tags=["seguridad"])


class Login(BaseModel):
    login: str = Field(min_length=1)
    clave: str = Field(min_length=1)


class UsuarioNuevo(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    clave: str = Field(min_length=8)
    rol: str = Field(min_length=1)


@router.post("/login")
def login(datos: Login, db: Session = Depends(get_db)):
    ahora = datetime.now(timezone.utc)
    usuario = datos.login.strip()
    u = db.scalar(select(Usuario).where(Usuario.login == usuario))
    if u is None:
        # mismo mensaje que con clave incorrecta, para no revelar si el usuario existe
        raise HTTPException(401, "Usuario o contraseña incorrectos")

    if u.bloqueado_hasta and u.bloqueado_hasta > ahora:
        raise HTTPException(423, f"Cuenta bloqueada hasta las {u.bloqueado_hasta:%H:%M}. Intente más tarde.")

    if not verificar(datos.clave, u.clave_hash):
        u.intentos += 1
        if u.intentos >= config.MAX_INTENTOS:
            u.bloqueado_hasta = ahora + timedelta(minutes=config.MINUTOS_BLOQUEO)
            u.intentos = 0
        auditar(db, u.id, "LOGIN_FALLIDO", "sesion")
        db.commit()
        raise HTTPException(401, "Usuario o contraseña incorrectos")

    u.intentos = 0
    auditar(db, u.id, "LOGIN_OK", "sesion")
    db.commit()
    return {"token": crear_token(u), "rol": u.rol}


@router.post("/usuarios", status_code=201)
def crear_usuario(datos: UsuarioNuevo, db: Session = Depends(get_db),
                  admin: Usuario = Depends(requiere("usuarios:gestionar"))):
    login = datos.login.strip()
    if not login:
        raise HTTPException(422, "El nombre de usuario no puede estar vacío")
    if datos.rol not in PERMISOS:
        raise HTTPException(422, f"Rol no válido. Use uno de: {', '.join(PERMISOS)}")
    if db.scalar(select(Usuario).where(Usuario.login == login)):
        raise HTTPException(409, "Ese usuario ya existe")
    u = Usuario(login=login, clave_hash=hashear(datos.clave), rol=datos.rol)
    db.add(u)
    db.flush()
    auditar(db, admin.id, "USUARIO_CREADO", f"usuario:{u.id}")
    db.commit()
    return {"id": u.id, "login": u.login, "rol": u.rol}


@router.patch("/usuarios/{id_usuario}/rol")
def cambiar_rol(id_usuario: int, rol: str, db: Session = Depends(get_db),
                admin: Usuario = Depends(requiere("usuarios:gestionar"))):
    if id_usuario == admin.id:
        raise HTTPException(400, "No puede cambiar su propio rol")
    u = db.get(Usuario, id_usuario)
    if u is None:
        raise HTTPException(404, "Usuario no encontrado")
    if rol not in PERMISOS:
        raise HTTPException(422, "Rol no válido")
    anterior, u.rol = u.rol, rol
    auditar(db, admin.id, "ROL_CAMBIADO", f"usuario:{u.id} {anterior}->{rol}")
    db.commit()
    return {"id": u.id, "rol": u.rol}
