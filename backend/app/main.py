from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from . import config
from .db import Base, engine, SessionLocal
from .modelos import Usuario
from .routers import auth, pacientes, citas, historia, auditoria
from .seguridad import hashear


@asynccontextmanager
async def arranque(app: FastAPI):
    with engine.begin() as con:
        con.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    Base.metadata.create_all(engine)

    # primer administrador; hay que cambiar la clave al entrar
    with SessionLocal() as db:
        if db.scalar(select(Usuario).where(Usuario.login == config.ADMIN_LOGIN)) is None:
            db.add(Usuario(login=config.ADMIN_LOGIN, clave_hash=hashear(config.ADMIN_CLAVE), rol="admin"))
            db.commit()
    yield


app = FastAPI(title="SaludIntegral HMS", version="0.1.0", lifespan=arranque)

for modulo in (auth, pacientes, citas, historia, auditoria):
    app.include_router(modulo.router)


@app.get("/salud")
def salud():
    return {"estado": "ok"}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "frontend", html=True), name="frontend")
