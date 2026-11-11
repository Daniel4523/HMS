# SaludIntegral HMS

Aplicación web sencilla para gestionar pacientes, citas, médicos e historias clínicas. Incluye una interfaz en español, una API y una base de datos PostgreSQL.

## Instalación y primer inicio en Windows

Para ejecutar la aplicación con Docker no necesitas instalar Python en Windows.

1. Instala [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/) y ábrelo. Espera a que indique que Docker está en ejecución. Si el instalador lo solicita, habilita WSL 2 y reinicia Windows.
2. Abre PowerShell o la terminal de VS Code en la carpeta principal del proyecto, donde está este README y `docker-compose.yml`. Puedes comprobarlo con:

       Get-Location
       Get-ChildItem

3. La primera vez, crea la configuración local copiando el ejemplo:

       Copy-Item .env.example .env

   Abre `.env` y cambia `SECRET_KEY` por una clave larga y aleatoria y `ADMIN_CLAVE` por una contraseña propia. No compartas ni publiques `.env`.
4. Construye e inicia la aplicación y la base de datos:

       docker compose up -d --build

   La primera ejecución puede tardar unos minutos mientras Docker descarga imágenes.
5. Abre **http://localhost:8000** e inicia sesión con los valores de `ADMIN_LOGIN` y `ADMIN_CLAVE` en `.env`.

La documentación interactiva de la API está en **http://localhost:8000/docs**.

### Usuario inicial y cuentas del personal

En una instalación nueva, el sistema crea un administrador con las credenciales de `ADMIN_LOGIN` y `ADMIN_CLAVE` configuradas en `.env`. El archivo de ejemplo trae estos valores, que debes reemplazar en `.env` **antes del primer inicio**:

- Usuario de ejemplo: `admin`
- Contraseña de ejemplo: `cambiar-en-el-primer-ingreso`

No uses las credenciales de ejemplo en una instalación real. La contraseña se lee al crear el primer usuario administrador. Si el administrador ya existe, cambiar `.env` no cambia su contraseña.

Si olvidaste la contraseña o la del archivo `.env` no funciona, desde la carpeta principal del proyecto ejecuta:

    docker compose exec api python -m app.reset_admin_password

Escribe la contraseña nueva dos veces en la terminal. No aparecerá mientras la escribes; se actualizará el administrador indicado por `ADMIN_LOGIN` en `.env`, sin borrar pacientes ni otros datos. Después inicia sesión con ese usuario y la contraseña nueva.

Después de iniciar sesión como administrador, entra en **Usuarios** para crear cuentas para el personal. El rol determina qué secciones y acciones puede utilizar cada persona:

| Rol | Acceso principal |
|---|---|
| `admin` | Gestionar usuarios y médicos, consultar pacientes y auditoría |
| `admisiones` | Registrar y buscar pacientes; agendar y cancelar citas |
| `medico` | Buscar pacientes y consultar o registrar evoluciones clínicas |
| `enfermeria` | Consultar pacientes, citas e historias clínicas |

Para habilitar citas, inicia sesión como administrador, crea primero uno o más médicos en **Médicos**, y luego crea una cuenta con el rol `admisiones`. La cuenta `admin` no es una cuenta de admisiones.

## Uso diario

Desde la carpeta del proyecto:

    docker compose up -d

Abre **http://localhost:8000**. Para revisar el estado de los servicios:

    docker compose ps

Para ver los mensajes de la API:

    docker compose logs -f api

Para detener los servicios:

    docker compose down

`docker compose down` conserva los datos de la base de datos. **No uses `docker compose down -v` salvo que quieras borrar también los datos guardados.**

Si la API no inicia porque PostgreSQL todavía está arrancando, espera unos segundos y ejecuta:

    docker compose up -d api

Si editas `.env` después de iniciar el proyecto y quieres aplicar los cambios al contenedor:

    docker compose up -d --force-recreate api

## Ejecutar las pruebas unitarias en Windows

Las pruebas locales necesitan Python 3.11. Puedes instalarlo desde [python.org](https://www.python.org/downloads/). Abre PowerShell en la carpeta principal del proyecto y ejecuta:

    py -3.11 -m venv backend\.venv
    Set-Location backend
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m pytest tests

Ejecuta pytest desde `backend` para que Python encuentre el paquete `app`.

Si el comando `py` no está disponible, usa `python` en su lugar únicamente si `python --version` indica Python 3.11.

## Estructura

- `backend/app/frontend/`: interfaz web.
- `backend/app/routers/`: rutas de pacientes, citas, historias clínicas, acceso y auditoría.
- `docker-compose.yml`: servicios de la API y PostgreSQL.
