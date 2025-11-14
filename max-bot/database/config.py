from configs import settings


# Конфигурация подключения к базе данных
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": settings.Postgres.host,  # type: ignore
                "port": settings.Postgres.port,  # type: ignore
                "user": settings.Postgres.user,  # type: ignore
                "password": settings.Postgres.password,  # type: ignore
                "database": settings.Postgres.database,  # type: ignore
            },
        }
    },
    "apps": {
        "models": {
            "models": ["database.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}


async def init_db() -> None:
    """Инициализация базы данных"""
    from tortoise import Tortoise

    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

