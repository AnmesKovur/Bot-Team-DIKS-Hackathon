import asyncio
import re
from types import MappingProxyType
from typing import Any

from aiohttp import web
from aiohttp.web import Application as WebApp

from common.logger import get_logger
from configs import settings
from database.crud import get_or_create_user, update_user_state

from .callbacks import ExitCallback, HideMessageCallback, PaginationCallback
from .commands import ResetCommand, StartCommand
from .handlers import ChatHandler, ExtendedStaticHandler, ManagedHandler, StaticHandler
from .max_client import MaxClient, MaxWebhookHandler
from .schemas import User
from .utils import build_shared_data, extract_user_id_from_update, load_json_with_references

logger = get_logger(__name__)


class MaxBot:
    """Основной класс MAX бота"""
    
    def __init__(self):
        """Инициализация бота"""
        self.token = settings.MAX.token  # type: ignore
        self.client = MaxClient(self.token)
        self.webhook_handler = MaxWebhookHandler(self)
        
        # Загружаем конфигурацию
        self.bot_config: dict[str, Any] = load_json_with_references("configs/flow.json")
        self.shared_data: MappingProxyType = build_shared_data(self.bot_config)
        
        # Регистрируем обработчики
        self.handlers: dict[str, Any] = {}
        self.callback_handlers: dict[str, Any] = {}
        self._register_handlers()
        
        # Кэш для дедупликации callback (хранит user_id + payload + timestamp)
        # MAX API может отправлять дубликаты с разными callback_id!
        self._processed_callbacks: dict[str, int] = {}  # key: "user_id:payload", value: timestamp
        self._deduplication_window_ms = 2000  # Окно дедупликации: 2 секунды
        
    def _register_handlers(self) -> None:
        """Регистрация всех обработчиков"""
        # Команды
        start_config: dict[str, Any] = self.bot_config["commands"]["start"]
        self.handlers["/start"] = StartCommand(config=start_config, common=self.shared_data)
        
        reset_config: dict[str, Any] = self.bot_config["commands"]["reset"]
        self.handlers["/reset"] = ResetCommand(config=reset_config, common=self.shared_data)
        
        # Обработчики флоу
        for flow in self.bot_config["flows"]:
            self._process_flow(flow)
        
        # Callback обработчики
        exit_config: dict[str, Any] = self.bot_config["callbacks"]["exit"]
        self.callback_handlers["exit_callback"] = ExitCallback(
            config=exit_config, 
            common=self.shared_data
        )
        
        hide_config: dict[str, Any] = self.bot_config["callbacks"]["hide"]
        self.callback_handlers["hide_callback"] = HideMessageCallback(
            config=hide_config, 
            common=self.shared_data
        )
        
        # Пагинация
        self.callback_handlers["previous_callback"] = PaginationCallback(
            config={}, 
            common=self.shared_data
        )
        self.callback_handlers["next_callback"] = PaginationCallback(
            config={}, 
            common=self.shared_data
        )
        self.callback_handlers["inactive_callback"] = PaginationCallback(
            config={}, 
            common=self.shared_data
        )
        self.callback_handlers["accept_callback"] = PaginationCallback(
            config={}, 
            common=self.shared_data
        )
        
        # ChatHandler по умолчанию
        self.chat_handler = ChatHandler(config={}, common=self.shared_data)
        
    def _process_flow(self, flow: dict[str, Any]) -> None:
        """
        Обработать флоу и его вложенные флоу
        
        Args:
            flow: Конфигурация флоу
        """
        # Обрабатываем вложенные флоу
        if "flows" in flow:
            for nested_flow in flow["flows"]:
                nested_flow["is_nested"] = True
                nested_flow["parent_name"] = flow["name"]
                self._process_flow(nested_flow)
        
        # Добавляем обработчик для этого флоу
        self._add_flow_handler(flow)
    
    def _add_flow_handler(self, flow_config: dict[str, Any]) -> None:
        """
        Добавить обработчик для флоу
        
        Args:
            flow_config: Конфигурация флоу
        """
        flow_name: str = flow_config["name"]
        flow_type: str = flow_config["type"]
        
        handler_instance: StaticHandler | ExtendedStaticHandler | ManagedHandler
        
        match flow_type:
            case "static":
                handler_instance = StaticHandler(
                    config=flow_config, 
                    common=self.shared_data
                )
            
            case "extended_static":
                handler_instance = ExtendedStaticHandler(
                    config=flow_config, 
                    common=self.shared_data
                )
            
            case "managed":
                flow_config["is_nested"] = True
                handler_instance = ManagedHandler(
                    config=flow_config, 
                    common=self.shared_data
                )
            
            case _:
                return
        
        self.handlers[flow_name] = handler_instance
    
    async def process_update(self, update: dict[str, Any]) -> None:
        """
        Обработать обновление от MAX API
        
        Args:
            update: Обновление от MAX
        """
        try:
            logger.info(f"Обработка обновления: {update}")
            
            # Получаем тип обновления
            update_type = update.get("update_type")
            logger.info(f"Тип обновления: {update_type}")
            
            # Получаем пользователя
            user_max_id = extract_user_id_from_update(update)
            if not user_max_id:
                logger.error("Не удалось извлечь ID пользователя из обновления")
                return
            
            # Получаем или создаем пользователя в БД
            db_user, db_user_state = await get_or_create_user(user_max_id)
            user = User(
                **db_user.model_dump(),
                state=db_user_state
            )
            
            # Обрабатываем разные типы обновлений
            if update_type == "message_callback":
                # Преобразуем в формат для внутренней обработки
                await self._process_callback(update, user)
            
            elif update_type == "message_created":
                # Преобразуем в формат для внутренней обработки
                await self._process_message(update, user)
            
            else:
                logger.warning(f"Неизвестный тип обновления: {update_type}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки обновления: {e}", exc_info=True)
    
    async def _process_callback(self, update: dict[str, Any], user: User) -> None:
        """
        Обработать callback query
        
        Args:
            update: Обновление от MAX (с типом message_callback)
            user: Пользователь
            
        Структура update для callback согласно MAX API:
        {
            "update_type": "message_callback",
            "timestamp": <int64>,
            "callback": {
                "payload": "button_data",
                "user": {"user_id": <int64>, ...}
            },
            "message": {
                "mid": "...",
                "recipient": {"chat_id": <int64>, "chat_type": "dialog"}
            },
            "sender": {...}
        }
        """
        # Извлекаем данные согласно документации MAX API
        callback = update.get("callback", {})
        message = update.get("message", {})
        sender = message.get("sender", {})  # sender находится ВНУТРИ message (это бот)
        # recipient находится ВНУТРИ message
        recipient = message.get("recipient", {})
        
        # Проверяем callback_id для дедупликации
        # Дедупликация на основе user_id + payload + timestamp
        # MAX API может отправлять дубликаты с разными callback_id!
        callback_id = callback.get("callback_id")
        # user_id берем из callback.user (это пользователь, который нажал кнопку)
        callback_user = callback.get("user", {})
        user_id = callback_user.get("user_id")
        callback_payload = callback.get("payload")
        callback_timestamp = callback.get("timestamp", 0)
        
        logger.info(f"🔍 Дедупликация: user_id={user_id}, payload='{callback_payload[:30]}...', timestamp={callback_timestamp}")
        
        if user_id and callback_payload:
            dedup_key = f"{user_id}:{callback_payload}"
            
            # Проверяем, не обрабатывали ли мы это событие недавно
            if dedup_key in self._processed_callbacks:
                last_timestamp = self._processed_callbacks[dedup_key]
                time_diff = callback_timestamp - last_timestamp
                
                if time_diff < self._deduplication_window_ms:
                    logger.info(f"⏭️  Пропускаем дубликат: user={user_id}, payload='{callback_payload}', "
                               f"time_diff={time_diff}ms")
                    return
            
            # Сохраняем timestamp последнего события
            self._processed_callbacks[dedup_key] = callback_timestamp
            
            # Очищаем старые записи (старше 10 секунд)
            current_time = callback_timestamp
            keys_to_remove = [
                key for key, ts in self._processed_callbacks.items() 
                if current_time - ts > 10000
            ]
            for key in keys_to_remove:
                del self._processed_callbacks[key]
            
            if keys_to_remove:
                logger.debug(f"Очищен кэш дедупликации: удалено {len(keys_to_remove)} старых записей")
        
        # Используем callback_payload вместо callback_data (уже определен выше)
        logger.info(f"🔘 Получен callback с payload: '{callback_payload}' (callback_id: {callback_id[:20] if callback_id else 'None'}...)")
        
        if not callback_payload:
            logger.warning("Callback payload отсутствует")
            return
        
        # ID чата из recipient
        chat_id = recipient.get("chat_id")
        message_id = message.get("mid", "")
        
        # Проверяем что chat_id существует
        if not chat_id:
            logger.error(f"chat_id отсутствует в recipient для callback. Update: {update}")
            return
        
        # Преобразуем в внутренний формат для совместимости с обработчиками
        normalized_update = {
            "callback_query": {
                "data": callback_payload,
                "message": {
                    "message_id": message_id,
                    "chat": {
                        "id": chat_id,
                        "type": recipient.get("chat_type", "dialog"),
                    },
                },
                "from": callback_user,  # пользователь, который нажал кнопку
            },
            "message": {
                "message_id": message_id,
                "chat": {
                    "id": chat_id,
                },
            },
        }
        
        # Ищем обработчик для этого callback
        # Сначала проверяем специальные callback обработчики (exit, hide, pagination, etc.)
        logger.info(f"🔍 Поиск обработчика для callback: '{callback_payload}'")
        logger.info(f"📋 Доступные callback_handlers: {list(self.callback_handlers.keys())}")
        logger.info(f"📋 Доступные handlers (первые 10): {list(self.handlers.keys())[:10]}")
        
        handler = self.callback_handlers.get(callback_payload)
        if handler:
            logger.info(f"✅ Найден callback обработчик: {callback_payload}")
            updated_user, _ = await handler(normalized_update, self.client, user)
            if updated_user:
                logger.info(f"💾 Сохранение состояния пользователя (callback)")
                # Сохраняем обновленное состояние пользователя
                await update_user_state(updated_user.id, updated_user.state.model_dump())
            else:
                logger.warning(f"⚠️ Обработчик не вернул updated_user")
        else:
            # Если не найден в callback_handlers, ищем в обычных handlers
            # (это кнопки навигации по меню)
            handler = self.handlers.get(callback_payload)
            if handler:
                logger.info(f"✅ Найден навигационный обработчик: {callback_payload}")
                updated_user, _ = await handler(normalized_update, self.client, user)
                if updated_user:
                    logger.info(f"💾 Сохранение состояния пользователя (navigation)")
                    # Сохраняем обновленное состояние пользователя
                    await update_user_state(updated_user.id, updated_user.state.model_dump())
                else:
                    logger.warning(f"⚠️ Обработчик не вернул updated_user")
            else:
                logger.error(f"❌ Обработчик НЕ найден для callback: '{callback_payload}'")
    
    async def _process_message(self, update: dict[str, Any], user: User) -> None:
        """
        Обработать текстовое сообщение
        
        Args:
            update: Обновление от MAX (с типом message_created)
            user: Пользователь
            
        Структура update согласно MAX API:
        {
            "update_type": "message_created",
            "timestamp": <int64>,
            "message": {
                "body": {"text": "..."},
                "mid": "message_id",
                "seq": <int64>,
                "recipient": {"chat_id": <int64>, "chat_type": "dialog", "user_id": <int64>}
            },
            "sender": {"user_id": <int64>, "username": "...", ...}
        }
        """
        # Извлекаем данные согласно документации MAX API
        message = update.get("message", {})
        sender = update.get("sender", {})
        # recipient находится ВНУТРИ message
        recipient = message.get("recipient", {})
        
        # Текст сообщения: message.body.text
        message_body = message.get("body", {})
        message_text = message_body.get("text", "")
        
        # ID чата из recipient
        chat_id = recipient.get("chat_id")
        chat_type = recipient.get("chat_type", "dialog")
        
        # Проверяем что chat_id существует
        if not chat_id:
            logger.error(f"chat_id отсутствует в recipient. Update: {update}")
            return
        
        # ID сообщения
        message_id = message.get("mid", "")
        
        # Создаем нормализованную структуру для обработчиков
        normalized_update = {
            "message": {
                "text": message_text,
                "chat": {
                    "id": chat_id,
                    "type": chat_type,
                },
                "from": sender,
                "message_id": message_id,
            }
        }
        
        logger.info(f"Обработка сообщения: '{message_text}' от пользователя {user.max_id}")
        
        # Проверяем, является ли это командой
        if message_text.startswith("/"):
            logger.info(f"Это команда: {message_text}")
            handler = self.handlers.get(message_text)
            if handler:
                logger.info(f"Найден обработчик для команды: {message_text}")
                updated_user, _ = await handler(normalized_update, self.client, user)
                if updated_user:
                    # Сохраняем обновленное состояние пользователя
                    await update_user_state(updated_user.id, updated_user.state.model_dump())
            else:
                logger.warning(f"Команда не найдена: {message_text}")
                logger.info(f"Доступные обработчики: {list(self.handlers.keys())}")
            return
        
        # Проверяем, является ли это кнопкой меню
        handler = self.handlers.get(message_text)
        if handler:
            logger.info(f"Найден обработчик для кнопки: {message_text}")
            updated_user, _ = await handler(normalized_update, self.client, user)
            if updated_user:
                # Сохраняем обновленное состояние пользователя
                await update_user_state(updated_user.id, updated_user.state.model_dump())
        else:
            logger.info("Используем ChatHandler для свободного текста")
            # Используем ChatHandler для обработки свободного текста
            updated_user, _ = await self.chat_handler(normalized_update, self.client, user)
            if updated_user:
                # Сохраняем обновленное состояние пользователя
                await update_user_state(updated_user.id, updated_user.state.model_dump())
    
    async def setup_webhook(self) -> None:
        """Установить webhook"""
        webhook_url = settings.MAX.webhook_url  # type: ignore
        if webhook_url:
            result = await self.client.set_webhook(webhook_url)
            logger.info(f"Webhook установлен: {result}")
        else:
            logger.error("URL webhook не указан в настройках")
    
    async def delete_webhook(self) -> None:
        """Удалить webhook"""
        result = await self.client.delete_webhook()
        logger.info(f"Webhook удален: {result}")
    
    def create_webhook_app(self) -> WebApp:
        """
        Создать веб-приложение для webhook
        
        Returns:
            WebApp: Веб-приложение aiohttp
        """
        app = web.Application()
        app.router.add_post("/webhook", self.webhook_handler.handle_update)
        return app
    
    async def start_polling(self) -> None:
        """
        Запустить бота в режиме long polling
        """
        logger.info("🚀 Запуск бота в режиме long polling")
        marker: int | None = None
        
        try:
            while True:
                try:
                    # Получаем обновления
                    logger.debug(f"🔄 Запрос обновлений с marker={marker}")
                    response = await self.client.get_updates(marker=marker, timeout=30)
                    
                    # Извлекаем обновления и новый marker
                    updates = response.get("updates", [])
                    new_marker = response.get("marker")
                    
                    if updates:
                        logger.info(f"📨 Получено обновлений: {len(updates)}, новый marker: {new_marker}")
                        
                        # Обрабатываем каждое обновление
                        for i, update in enumerate(updates):
                            try:
                                logger.info(f"⚙️ Обработка обновления {i + 1}/{len(updates)}")
                                # Обрабатываем обновление
                                await self.process_update(update)
                                
                            except Exception as e:
                                logger.error(f"Ошибка обработки обновления: {e}", exc_info=True)
                        
                        # Обновляем marker после успешной обработки всех обновлений
                        if new_marker is not None:
                            logger.info(f"✅ Обновлен marker: {marker} → {new_marker}")
                            marker = new_marker
                    
                except KeyboardInterrupt:
                    logger.info("Получен сигнал остановки")
                    break
                    
                except Exception as e:
                    logger.error(f"Ошибка в цикле polling: {e}", exc_info=True)
                    await asyncio.sleep(1)  # Небольшая задержка перед следующей попыткой
                    
        except KeyboardInterrupt:
            logger.info("Бот остановлен пользователем")
        finally:
            logger.info("Завершение работы бота")


def get_bot() -> MaxBot:
    """
    Получить экземпляр бота
    
    Returns:
        MaxBot: Экземпляр бота
    """
    return MaxBot()

