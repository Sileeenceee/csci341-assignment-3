import os

DEFAULT_URL = "postgresql+psycopg://localhost/conference_review"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def exec_script(conn, sql: str) -> None:
    with conn.connection.cursor() as cur:
        cur.execute(sql)
