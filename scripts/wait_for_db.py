import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import settings


def main() -> None:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    deadline = time.monotonic() + 60
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("Database is ready")
            return
        except OperationalError as exc:
            last_error = exc
            print("Waiting for database...")
            time.sleep(2)

    raise RuntimeError("Database did not become ready within 60 seconds") from last_error


if __name__ == "__main__":
    main()
