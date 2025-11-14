from typing import Any
import json
import ssl

from aiohttp import ClientSession, ClientTimeout, web
from aiohttp.web import Request, Response

from common.logger import get_logger
from configs import settings


logger = get_logger(__name__)


class MaxClient:
    """Клиент для работы с MAX API"""

    def __init__(self, token: str):
        """
        Инициализация клиента MAX

        Args:
            token: Токен бота MAX
        """
        self.token = token
        self.api_url = "https://platform-api.max.ru"
        self.timeout = ClientTimeout(total=30)

        # Создаем SSL контекст, который не проверяет сертификаты (для разработки)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        """
        Отправить текстовое сообщение

        Args:
            chat_id: ID чата (число или строка с числом)
            text: Текст сообщения
            reply_markup: Клавиатура (inline или reply)
            parse_mode: Режим парсинга (Markdown, HTML)

        Returns:
            dict[str, Any]: Ответ от API
        """
        # Конвертируем chat_id в int если это строка
        chat_id_int = int(chat_id) if isinstance(chat_id, str) else chat_id
        
        # Согласно документации MAX API: https://dev.max.ru/docs-api/methods/POST/messages
        # chat_id передается как query parameter, а не в body!
        endpoint = f"/messages?chat_id={chat_id_int}"
        
        # Body запроса (без chat_id!)
        payload = {
            "text": text,
        }

        # Кнопки передаются через attachments, а не replyMarkup
        if reply_markup:
            # Проверяем, что это inline_keyboard
            if reply_markup.get("type") == "inline_keyboard":
                payload["attachments"] = [reply_markup]
            else:
                # Для обычной клавиатуры (если понадобится)
                payload["replyMarkup"] = reply_markup

        if parse_mode:
            # Согласно документации: используется "format", не "parseMode"
            # Значения: "markdown" или "html"
            format_value = parse_mode.lower() if parse_mode else None
            if format_value in ["markdown", "html"]:
                payload["format"] = format_value

        logger.info(f"Отправка сообщения в чат {chat_id_int}: {text[:50]}...")
        logger.debug(f"Endpoint: {endpoint}")
        logger.info(f"💬 Payload для MAX API:")
        logger.info(f"   text: {payload.get('text', '')[:100]}")
        if "attachments" in payload:
            logger.info(f"   attachments: {len(payload['attachments'])} элементов")
            for i, att in enumerate(payload['attachments']):
                logger.info(f"      [{i}] type={att.get('type')}")
                if att.get('type') == 'inline_keyboard':
                    buttons = att.get('payload', {}).get('buttons', [])
                    logger.info(f"          buttons: {len(buttons)} рядов")
        logger.debug(f"Полный payload: {payload}")

        return await self._make_rest_request("POST", endpoint, payload)

    async def send_photo(
        self,
        chat_id: str | int,
        photo: str,
        caption: str | None = None,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        """
        Отправить фото

        Args:
            chat_id: ID чата (число или строка с числом)
            photo: URL фото
            caption: Подпись
            reply_markup: Клавиатура
            parse_mode: Режим парсинга

        Returns:
            dict[str, Any]: Ответ от API
        """
        # Конвертируем chat_id в int если это строка
        chat_id_int = int(chat_id) if isinstance(chat_id, str) else chat_id
        
        # chat_id в query parameters
        endpoint = f"/messages?chat_id={chat_id_int}"
        
        # Согласно документации MAX API
        payload = {
            "attachments": [{"type": "image", "payload": {"url": photo}}],
        }

        if caption:
            payload["text"] = caption

        # Кнопки передаются через attachments
        if reply_markup:
            if reply_markup.get("type") == "inline_keyboard":
                # Добавляем клавиатуру к attachments
                payload["attachments"].append(reply_markup)
            else:
                payload["replyMarkup"] = reply_markup

        if parse_mode:
            format_value = parse_mode.lower() if parse_mode else None
            if format_value in ["markdown", "html"]:
                payload["format"] = format_value

        return await self._make_rest_request("POST", endpoint, payload)

    async def send_video(
        self,
        chat_id: str | int,
        video: str,
        caption: str | None = None,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        """
        Отправить видео

        Args:
            chat_id: ID чата (число или строка с числом)
            video: URL видео
            caption: Подпись
            reply_markup: Клавиатура
            parse_mode: Режим парсинга

        Returns:
            dict[str, Any]: Ответ от API
        """
        # Конвертируем chat_id в int если это строка
        chat_id_int = int(chat_id) if isinstance(chat_id, str) else chat_id
        
        # chat_id в query parameters
        endpoint = f"/messages?chat_id={chat_id_int}"
        
        # Согласно документации MAX API
        payload = {
            "attachments": [{"type": "video", "payload": {"url": video}}],
        }

        if caption:
            payload["text"] = caption

        # Кнопки передаются через attachments
        if reply_markup:
            if reply_markup.get("type") == "inline_keyboard":
                # Добавляем клавиатуру к attachments
                payload["attachments"].append(reply_markup)
            else:
                payload["replyMarkup"] = reply_markup

        if parse_mode:
            format_value = parse_mode.lower() if parse_mode else None
            if format_value in ["markdown", "html"]:
                payload["format"] = format_value

        return await self._make_rest_request("POST", endpoint, payload)

    async def edit_message_reply_markup(
        self,
        chat_id: str | int,
        message_id: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Изменить клавиатуру сообщения
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения
            reply_markup: Новая клавиатура
            
        Returns:
            dict[str, Any]: Ответ от API
        """
        payload = {}
        
        # Кнопки передаются через attachments
        if reply_markup:
            if reply_markup.get("type") == "inline_keyboard":
                payload["attachments"] = [reply_markup]
            else:
                payload["replyMarkup"] = reply_markup
        
        return await self._make_rest_request("PATCH", f"/messages/{message_id}", payload)
    
    async def delete_message(
        self,
        chat_id: str | int,
        message_id: str,
    ) -> dict[str, Any]:
        """
        Удалить сообщение
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения
            
        Returns:
            dict[str, Any]: Ответ от API
        """
        return await self._make_rest_request("DELETE", f"/messages/{message_id}", {})
    
    async def answer_callback_query(
        self,
        callback_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> dict[str, Any]:
        """
        Ответить на callback запрос
        
        Args:
            callback_id: ID callback запроса
            text: Текст уведомления
            show_alert: Показать как alert
            
        Returns:
            dict[str, Any]: Ответ от API
        """
        payload = {
            "callback_query_id": callback_id,
            "show_alert": show_alert,
        }
        
        if text:
            payload["text"] = text
        
        return await self._make_request("answerCallbackQuery", payload)
    
    async def set_webhook(self, url: str) -> dict[str, Any]:
        """
        Установить webhook
        
        Args:
            url: URL для webhook
            
        Returns:
            dict[str, Any]: Ответ от API
        """
        payload = {
            "url": url,
        }
        
        return await self._make_request("setWebhook", payload)
    
    async def delete_webhook(self) -> dict[str, Any]:
        """
        Удалить webhook
        
        Returns:
            dict[str, Any]: Ответ от API
        """
        return await self._make_request("deleteWebhook", {})
    
    async def get_updates(
        self, 
        marker: int | None = None, 
        limit: int = 100, 
        timeout: int = 30
    ) -> dict[str, Any]:
        """
        Получить обновления через long polling
        
        Args:
            marker: Маркер последнего обработанного обновления (integer)
            limit: Количество обновлений для получения (1-1000, по умолчанию 100)
            timeout: Таймаут long polling в секундах (0-90, по умолчанию 30)
            
        Returns:
            dict[str, Any]: Ответ с обновлениями и новым marker
            {
                "updates": [...],
                "marker": <integer>
            }
        """
        # Формируем query параметры для GET запроса
        params = f"?limit={limit}&timeout={timeout}"
        if marker is not None:
            params += f"&marker={marker}"
        
        endpoint = f"/updates{params}"
        
        try:
            logger.debug(f"Запрос обновлений (marker: {marker}, limit: {limit}, timeout: {timeout})")
            result = await self._make_rest_request("GET", endpoint, {})
            
            updates_count = len(result.get("updates", []))
            new_marker = result.get("marker")
            logger.debug(f"Получено обновлений: {updates_count}, новый marker: {new_marker}")
            
            return result
        except Exception as e:
            logger.error(f"Ошибка получения обновлений: {e}", exc_info=True)
            return {"updates": [], "marker": marker}
    
    async def _make_rest_request(
        self, 
        http_method: str, 
        endpoint: str, 
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Выполнить REST запрос к API
        
        Args:
            http_method: HTTP метод (GET, POST, PATCH, DELETE)
            endpoint: Endpoint API (например /messages)
            payload: Данные запроса
            
        Returns:
            dict[str, Any]: Ответ от API
        """
        url = f"{self.api_url}{endpoint}"
        
        # Заголовок с токеном авторизации
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Отправка {http_method} запроса к MAX API: {endpoint}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Payload: {payload}")
        
        # Используем ssl_context для обхода проблем с сертификатами на macOS
        import aiohttp
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with ClientSession(timeout=self.timeout, connector=connector) as session:
            # Для GET запросов не передаем json в теле
            request_kwargs = {"headers": headers}
            if http_method != "GET" and payload:
                request_kwargs["json"] = payload
            
            async with session.request(http_method, url, **request_kwargs) as response:
                response_text = await response.text()
                logger.debug(f"Ответ от API ({response.status}): {response_text}")
                
                response.raise_for_status()
                
                # Если ответ пустой (например, для DELETE), возвращаем пустой словарь
                if not response_text:
                    return {}
                
                result = await response.json()
                return result
    
    async def _make_request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Выполнить запрос к API (старый формат, для совместимости с webhook)
        
        Args:
            method: Метод API
            payload: Данные запроса
            
        Returns:
            dict[str, Any]: Ответ от API
        """
        # Для webhook используем другой endpoint
        return await self._make_rest_request("POST", f"/bot/v1/{method}", payload)


class MaxWebhookHandler:
    """Обработчик webhook для MAX"""
    
    def __init__(self, bot_instance):
        """
        Инициализация обработчика webhook
        
        Args:
            bot_instance: Экземпляр бота
        """
        self.bot = bot_instance
        
    async def handle_update(self, request: Request) -> Response:
        """
        Обработать входящий webhook
        
        Args:
            request: HTTP запрос
            
        Returns:
            Response: HTTP ответ
        """
        try:
            # Читаем сырые данные для логирования
            body = await request.text()
            logger.info("=== ПОЛУЧЕН WEBHOOK ===")
            logger.info(f"Метод: {request.method}")
            logger.info(f"URL: {request.url}")
            logger.info(f"Заголовки: {dict(request.headers)}")
            logger.info(f"Тело запроса: {body}")
            
            # Парсим JSON
            data = await request.json()
            logger.info(f"Распарсенные данные: {data}")
            
            # Обрабатываем обновление
            await self.bot.process_update(data)
            
            logger.info("=== WEBHOOK ОБРАБОТАН УСПЕШНО ===")
            return web.Response(text="OK")
            
        except Exception as e:
            logger.error("=== ОШИБКА ОБРАБОТКИ WEBHOOK ===")
            logger.error(f"Ошибка: {e}", exc_info=True)
            return web.Response(status=500, text=str(e))

