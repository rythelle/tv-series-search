import asyncpg

from application.interfaces.clock import Clock
from application.interfaces.unit_of_work import UnitOfWork
from infrastructure.messaging.postgres_outbox_publisher import PostgresOutboxPublisher
from infrastructure.persistence.postgres_comment_repository import PostgresCommentRepository


class PostgresUnitOfWork(UnitOfWork):
    def __init__(self, pool: asyncpg.Pool, clock: Clock):
        self._pool = pool
        self._clock = clock

    async def __aenter__(self) -> "PostgresUnitOfWork":
        self._connection = await self._pool.acquire()
        self._transaction = self._connection.transaction()
        await self._transaction.start()
        self._committed = False
        self.comments = PostgresCommentRepository(self._connection)
        self.events = PostgresOutboxPublisher(self._connection, self._clock)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is not None or not self._committed:
                await self._transaction.rollback()
        finally:
            await self._pool.release(self._connection)

    async def commit(self) -> None:
        await self._transaction.commit()
        self._committed = True
