import json
import re
from pathlib import Path
from types import MappingProxyType
from typing import Any

from common.logger import get_logger

from .schemas import Button
from .types import Flow, Flows, Menus

logger = get_logger(__name__)


# Константы для состояний ConversationHandler (если понадобится)
WAITING_ANNOUNCEMENT = 1
WAITING_CONFIRMATION = 2


def resolve_references(data: Any, context: Any) -> Any:
    """
    Рекурсивно разрешить ссылки в данных
    
    Args:
        data: Данные для обработки
        context: Контекст для поиска ссылок (корневой объект)
        
    Returns:
        Any: Данные с разрешенными ссылками
    """
    if isinstance(data, dict):
        return {key: resolve_references(value, context) for key, value in data.items()}

    elif isinstance(data, list):
        return [resolve_references(item, context) for item in data]

    elif isinstance(data, str) and data.startswith("@"):
        reference: str = data[1:]
        parts: list[str] = reference.split(".")
        base_key: str = parts[0]

        try:
            resolved: Any = context["buttons"][base_key]

        except KeyError:
            logger.critical(f"Reference '@{base_key}' not found in buttons.")
            raise ValueError

        for subkey in parts[1:]:
            if isinstance(resolved, dict) and subkey in resolved:
                resolved = resolved[subkey]

            else:
                logger.critical(
                    f"Reference '@{reference}' is invalid: missing '{subkey}' key."
                )
                raise ValueError

        return resolved

    return data


def load_json_with_references(file_path: str) -> Any:
    """
    Загрузить JSON с поддержкой ссылок (@button.name)
    
    Args:
        file_path: Путь к JSON файлу
        
    Returns:
        Any: Загруженные данные с разрешенными ссылками
    """
    with open(file_path, "r", encoding="utf-8") as file:
        data: Any = json.load(file)

    resolved_data: Any = resolve_references(data, data)

    return resolved_data


def get_managed_flows(flows: Flows) -> set[str]:
    """
    Рекурсивно собирает все managed flows
    
    Args:
        flows: Список флоу
        
    Returns:
        set[str]: Множество имен managed flows
    """
    managed_flows: set[str] = set()

    flow: Flow
    for flow in flows:
        try:
            if flow["type"] == "managed":
                managed_flows.add(flow["name"])

        except Exception:
            logger.critical("Managed flow missing important key", exc_info=True)
            raise

        if "flows" in flow:
            managed_flows |= get_managed_flows(flow["flows"])

    return managed_flows


def get_menus(flows: Flows, parent_name: str | None = None) -> Menus:
    """
    Рекурсивно строит меню из flows
    
    Args:
        flows: Список флоу
        parent_name: Имя родительского флоу (None для главного меню)
        
    Returns:
        Menus: Словарь меню
    """
    key: str = "main" if parent_name is None else parent_name
    menus: Menus = {key: []}

    flow: Flow
    for flow in flows:
        try:
            button: Button = Button(name=flow["name"], privileged=flow["privileged"])

        except Exception:
            logger.critical("Flow missing required key", exc_info=True)
            raise

        menus[key].append(button)

        if "flows" in flow:
            menus |= get_menus(flow["flows"], parent_name=flow["name"])

    return menus


def build_shared_data(config: dict[str, Any]) -> MappingProxyType:
    """
    Построить общие данные для всех обработчиков
    
    Args:
        config: Конфигурация бота
        
    Returns:
        MappingProxyType: Неизменяемый словарь с общими данными
    """
    flows: Flows = config.get("flows", [])

    mapping_data: dict[str, Any] = {
        "menus": get_menus(flows),
        "errors": config.get("errors", {}),
        "buttons": config.get("buttons", {}),
        "managed_flows": get_managed_flows(flows),
    }

    return MappingProxyType(mapping_data)


def extract_user_id_from_update(update: dict[str, Any]) -> str | None:
    """
    Извлечь ID пользователя из обновления MAX API
    
    Проверяет несколько источников в порядке приоритета согласно документации MAX API:
    https://dev.max.ru/docs-api/methods/GET/updates

    Args:
        update: Обновление от MAX API

    Returns:
        str | None: ID пользователя или None
        
    Структура MAX API:
    - recipient.user_id - для диалогов (основной)
    - sender.user_id - отправитель сообщения/callback
    - callback.user.user_id - для callback событий
    """
    # Вариант 1 (приоритетный): sender.user_id - отправитель сообщения
    # Это самый надежный источник, т.к. всегда содержит того, кто отправил сообщение
    if "sender" in update and isinstance(update["sender"], dict):
        user_id = update["sender"].get("user_id")
        if user_id:
            return str(user_id)
    
    # Вариант 2: message.recipient.user_id - для диалогов с ботом
    # recipient находится ВНУТРИ message
    if "message" in update and isinstance(update["message"], dict):
        message = update["message"]
        if "recipient" in message and isinstance(message["recipient"], dict):
            user_id = message["recipient"].get("user_id")
            if user_id:
                return str(user_id)
    
    # Вариант 3: callback.user.user_id - для callback событий
    if "callback" in update and isinstance(update["callback"], dict):
        callback = update["callback"]
        if "user" in callback and isinstance(callback["user"], dict):
            user_id = callback["user"].get("user_id")
            if user_id:
                return str(user_id)
    
    # Вариант 4: прямой user_id в корне (старый формат?)
    if "user_id" in update:
        return str(update["user_id"])
    
    # Вариант 5: user объект в корне (fallback)
    if "user" in update and isinstance(update["user"], dict):
        user_id = update["user"].get("user_id")
        if user_id:
            return str(user_id)
    
    # Вариант 6: message.from.user_id (может быть в некоторых случаях)
    if "message" in update and isinstance(update["message"], dict):
        message = update["message"]
        if "from" in message and isinstance(message["from"], dict):
            user_id = message["from"].get("user_id")
            if user_id:
                return str(user_id)
    
    return None


def extract_chat_id_from_update(update: dict[str, Any]) -> str | None:
    """
    Извлечь ID чата из обновления MAX API
    
    Args:
        update: Обновление от MAX API
        
    Returns:
        str | None: ID чата или None
    """
    # Вариант 1 (основной): message.recipient.chat_id
    # recipient находится ВНУТРИ message
    if "message" in update and isinstance(update["message"], dict):
        message = update["message"]
        if "recipient" in message and isinstance(message["recipient"], dict):
            chat_id = message["recipient"].get("chat_id")
            if chat_id:
                return str(chat_id)
    
    # Вариант 2: прямой chat_id в корне (fallback)
    if "chat_id" in update:
        return str(update["chat_id"])
    
    return None

