from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from langgraph.checkpoint.memory import InMemorySaver


@lru_cache(maxsize=1)
def _build_postgres_saver(postgres_dsn: str | None = None):
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # type: ignore
        from psycopg_pool import AsyncConnectionPool  # type: ignore
    except Exception:
        return None

    if not postgres_dsn:
        return None

    try:
        pool = AsyncConnectionPool(
            conninfo=postgres_dsn,
            min_size=1,
            max_size=4,
            open=True,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        saver = AsyncPostgresSaver(pool)
        return saver, pool
    except Exception:
        return None


def build_checkpoint_saver(postgres_dsn: str | None = None):
    built = _build_postgres_saver(postgres_dsn)
    if built:
        saver, _pool = built
        return saver
    return InMemorySaver()


@contextmanager
def checkpoint_saver_context(postgres_dsn: str | None = None) -> Iterator[object]:
    built = _build_postgres_saver(postgres_dsn)
    if built:
        saver, pool = built
        try:
            yield saver
        finally:
            try:
                pool.close()
            except Exception:
                pass
    else:
        yield InMemorySaver()
