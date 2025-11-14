import asyncio
from logging import Logger

from aiohttp import web
from tortoise import run_async

from common.logger import get_logger
from configs import settings
from core.bot import get_bot
from database.config import init_db

logger: Logger = get_logger(__name__)


async def main() -> None:
    """Главная функция запуска бота"""
    # Инициализируем базу данных
    await init_db()
    logger.info("База данных инициализирована")

    # Создаем бота
    bot = get_bot()
    logger.info("Бот инициализирован")

    # Запускаем в режиме long polling
    logger.info("Запуск бота в режиме long polling")
    await bot.start_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
