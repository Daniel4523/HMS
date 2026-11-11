from getpass import getpass

from sqlalchemy import select

from . import config
from .db import SessionLocal
from .modelos import Usuario
from .seguridad import hashear


def main() -> None:
    clave = getpass("Nueva contraseña del administrador (mínimo 8 caracteres): ")
    if len(clave) < 8:
        raise SystemExit("La contraseña debe tener al menos 8 caracteres.")

    confirmacion = getpass("Confirma la nueva contraseña: ")
    if clave != confirmacion:
        raise SystemExit("Las contraseñas no coinciden. No se hicieron cambios.")

    with SessionLocal() as db:
        usuario = db.scalar(
            select(Usuario).where(Usuario.login == config.ADMIN_LOGIN, Usuario.rol == "admin")
        )
        if usuario is None:
            raise SystemExit(
                f"No se encontró un administrador con el usuario configurado en ADMIN_LOGIN ({config.ADMIN_LOGIN})."
            )

        usuario.clave_hash = hashear(clave)
        usuario.intentos = 0
        usuario.bloqueado_hasta = None
        db.commit()

    print("Contraseña del administrador actualizada.")


if __name__ == "__main__":
    main()
