import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://hms:hms@localhost:5432/hms")
SECRET_KEY = os.environ.get("SECRET_KEY", "solo-para-desarrollo")
ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
ADMIN_CLAVE = os.environ.get("ADMIN_CLAVE", "admin12345")

MAX_INTENTOS = 3
MINUTOS_BLOQUEO = 15
MINUTOS_TOKEN = 30
