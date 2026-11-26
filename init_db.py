from pathlib import Path

from sqlalchemy import create_engine

from db_config import database_url, exec_script

SQL_DIR = Path(__file__).resolve().parent / "sql"


def init_db(engine=None):
    engine = engine or create_engine(database_url())
    with engine.begin() as conn:
        for name in ("01_schema.sql", "02_seed.sql", "03_view.sql"):
            exec_script(conn, (SQL_DIR / name).read_text(encoding="utf-8"))
            print(f"executed {name}")


if __name__ == "__main__":
    init_db()
    print("Database initialised with seed data.")
