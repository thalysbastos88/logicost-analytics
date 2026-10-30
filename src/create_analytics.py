from pathlib import Path

from src.db import get_connection


ANALYTICS_SQL = Path(__file__).resolve().parents[1] / "sql" / "analytics_views.sql"


def create_analytics():
    if not ANALYTICS_SQL.is_file():
        raise FileNotFoundError(f"Arquivo de views analíticas não encontrado: {ANALYTICS_SQL}")

    script = ANALYTICS_SQL.read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('analytics.vw_deliveries_analytics')")
            if cur.fetchone()[0] is None:
                raise RuntimeError(
                    "O esquema-base não está instalado. Execute "
                    "sql/schema_star.sql no banco antes de criar as análises."
                )
            cur.execute(script)

    print("Camada analítica criada no schema analytics.")


if __name__ == "__main__":
    create_analytics()
