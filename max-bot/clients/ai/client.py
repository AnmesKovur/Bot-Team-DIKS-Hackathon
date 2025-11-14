from typing import Any

from aiohttp import ClientSession, ClientTimeout
from tenacity import retry, stop_after_attempt, wait_fixed

from configs import settings


class AIClient:
    """Клиент для работы с AI сервером"""

    api_url: str = f"{settings.AIServer.host}:{settings.AIServer.port}"  # type: ignore

    @classmethod
    @retry(stop=stop_after_attempt(15), wait=wait_fixed(1))
    async def post_request(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Отправить запрос к AI серверу

        Args:
            payload: Данные запроса

        Returns:
            dict[str, Any]: Ответ от AI сервера
        """
        # Проверяем, включены ли запросы к AI серверу
        if not getattr(settings.AIServer, "ai_enabled", True):
            # Возвращаем пустой ответ, если AI отключен
            return {}

        url = f"{cls.api_url}/search/"

        timeout = ClientTimeout(total=15)
        async with ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as raw_response:
                raw_response.raise_for_status()

                response = await raw_response.json()

                return response

