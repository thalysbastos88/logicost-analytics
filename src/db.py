import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Abre conexão PostgreSQL usando variáveis do arquivo .env."""
    required = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Variáveis ausentes no .env: " + ", ".join(missing)
        )

    return psycopg.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        connect_timeout=10,
        application_name="logicost_analytics"
    )
