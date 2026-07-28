"""SQLite database connection management."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from gitpulse.exceptions import DatabaseInitializationError
from gitpulse.storage.migrations.manager import MigrationManager


class Database:
    """Manage SQLite engine, initialization, and sessions."""

    def __init__(self, database_path: Path, *, timeout_seconds: float = 10.0) -> None:
        self.database_path = Path(database_path).expanduser()
        self.timeout_seconds = timeout_seconds
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def initialize(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            MigrationManager(self.engine).migrate()
        except SQLAlchemyError as exc:
            raise DatabaseInitializationError("数据库初始化失败。") from exc
        except OSError as exc:
            raise DatabaseInitializationError(f"无法创建数据库目录：{self.database_path.parent}") from exc

    def create_session(self) -> Session:
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        return self._session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.create_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

    def _create_engine(self) -> Engine:
        engine = create_engine(
            f"sqlite+pysqlite:///{self.database_path}",
            connect_args={"check_same_thread": False, "timeout": self.timeout_seconds},
            future=True,
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    def foreign_keys_enabled(self) -> bool:
        with self.engine.connect() as connection:
            return bool(connection.execute(text("PRAGMA foreign_keys")).scalar())
