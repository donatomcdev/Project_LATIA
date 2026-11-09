import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


def database_engine(variable="DATABASE_URL"):
    load_dotenv()
    raw_url = os.environ.get(variable) or os.environ.get("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("Configura DATABASE_URL antes de iniciar LATIA.")
    url = make_url(raw_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError("LATIA requiere PostgreSQL con psycopg.")
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)
