from logging import Logger
from types import MappingProxyType
from typing import Any

from common.logger import get_logger
from common.utils import Sentinels, format_message_for_max

from .keyboard import (
    add_button_to_inline_markup,
    build_inline_keyboard,
    build_keyboard,
)
from .max_client import MaxClient
from .schemas import Button, InlineButton, User
from .types import Menus


logger: Logger = get_logger(__name__)


class BaseResponse:
    """Базовый класс для всех обработчиков"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        """
        Инициализация базового обработчика
        
        Args:
            config: Конфигурация обработчика
            common: Общие данные
        """
        self.config: dict[str, Any] = config

        self.content: str = config.get("content", Sentinels.EMPTY_STR)

        self.menus: Menus = common["menus"]
        self.errors: dict[str, str] = common["errors"]
        self.buttons: dict[str, dict[str, str]] = common["buttons"]

        self.exit_button_content: str = self.buttons["exit"]["content"]
        self.exit_button: InlineButton = InlineButton(**self.buttons["exit"])
        self.exit_button_inline_markup: dict[str, Any] = build_inline_keyboard(
            [self.exit_button],
        )

    async def _send_message(
        self,
        update: dict[str, Any],
        client: MaxClient,
        content: str,
        photo: str | None = None,
        video: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Отправить сообщение пользователю
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            content: Текст сообщения
            photo: URL фото
            video: URL видео
            reply_markup: Клавиатура
            
        Returns:
            dict[str, Any] | None: Отправленное сообщение
        """
        # Получаем chat_id из нормализованной структуры
        chat_id = None
        if "message" in update:
            chat = update["message"].get("chat", {})
            chat_id = chat.get("id")
        elif "callback_query" in update and "message" in update["callback_query"]:
            chat = update["callback_query"]["message"].get("chat", {})
            chat_id = chat.get("id")
        
        # Проверяем что chat_id валидный
        if not chat_id or chat_id == "":
            logger.error(f"Не удалось получить chat_id из обновления. Update: {update}")
            return None
        
        # Конвертируем в int если это строка с числом
        try:
            chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
        except ValueError:
            logger.error(f"Невалидный chat_id: {chat_id}")
            return None
        
        try:
            # Форматируем текст
            formatted_content = format_message_for_max(content)
            
            if photo:
                result = await client.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=formatted_content,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )
            elif video:
                result = await client.send_video(
                    chat_id=chat_id,
                    video=video,
                    caption=formatted_content,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )
            else:
                result = await client.send_message(
                    chat_id=chat_id,
                    text=formatted_content,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return None

    async def _remove_callback_buttons(
        self,
        client: MaxClient,
        user: User,
        chat_id: str,
    ) -> User:
        """
        Удалить или изменить клавиатуру предыдущего сообщения
        
        Args:
            client: Клиент MAX
            user: Пользователь
            chat_id: ID чата
            
        Returns:
            User: Обновленный пользователь
        """
        if user.state.callback_message_id == Sentinels.EMPTY_STR:
            return user

        inline_markup: dict[str, Any] | None = user.state.callback_message_inline_markup
        
        try:
            if user.state.callback_message_need_to_delete:
                await client.delete_message(
                    chat_id=chat_id,
                    message_id=user.state.callback_message_id,
                )
            else:
                await client.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=user.state.callback_message_id,
                    reply_markup=inline_markup,
                )

        except Exception as e:
            logger.warning(
                f"Не удалось обновить/удалить клавиатуру для пользователя: {user.max_id}, "
                f"message_id: {user.state.callback_message_id}. Ошибка: {e}"
            )

        user.state.callback_message_id = None

        return user


class BaseCommand(BaseResponse):
    """Базовый класс для команд"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        super().__init__(config=config, common=common)

        main_menu_buttons: list[Button] = self.menus["main"]

        self.main_menu_keyboard_markup: dict[str, dict[str, Any]] = {
            "vip": build_keyboard(buttons=main_menu_buttons, vip_status=True),
            "all": build_keyboard(buttons=main_menu_buttons, vip_status=False),
        }


class BaseCallback(BaseResponse):
    """Базовый класс для callback обработчиков"""
    
    async def validate_user(
        self,
        update: dict[str, Any],
        user: User | None,
    ) -> tuple[User | None, bool]:
        """
        Проверить пользователя
        
        Args:
            update: Обновление
            user: Пользователь
            
        Returns:
            tuple[User | None, bool]: Пользователь и флаг валидности
        """
        content: str | None = None

        if user is None:
            content = self.errors["user_not_registered"]

        is_valid: bool = content is None
        
        return user, is_valid


class BaseHandler(BaseResponse):
    """Базовый класс для обработчиков сообщений"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        super().__init__(config=config, common=common)

        self.current_flow: str = config["name"]
        self.photo: str | None = config["photo"]

        self.is_nested: bool = config.get("is_nested", False)
        self.privileged: bool = config.get("privileged", False)
        self.parent_name: str = config.get("parent_name", "main")

    async def validate_user(
        self,
        update: dict[str, Any],
        user: User | None,
    ) -> tuple[User | None, bool]:
        """
        Проверить пользователя
        
        Args:
            update: Обновление
            user: Пользователь
            
        Returns:
            tuple[User | None, bool]: Пользователь и флаг валидности
        """
        content: str | None = None

        if user is None:
            content = self.errors["user_not_registered"]

        elif self.privileged and not user.is_vip:
            content = self.errors["user_not_allowed"]

        is_valid: bool = content is None

        return user, is_valid

    async def validate_flow(
        self, 
        update: dict[str, Any], 
        user: User
    ) -> tuple[User, bool]:
        """
        Проверить флоу пользователя
        
        Args:
            update: Обновление
            user: Пользователь
            
        Returns:
            tuple[User, bool]: Пользователь и флаг валидности
        """
        content: str | None = None

        user_current_flow: str = user.state.flow_stack[-1]
        
        # Если пользователь уже находится в этом flow (дубликат или повторное нажатие)
        # - просто разрешаем навигацию
        if user_current_flow == self.current_flow:
            logger.info(f"validate_flow: пользователь уже в '{self.current_flow}', разрешаем")
            is_valid = True
            return user, is_valid
        
        # Проверяем, доступна ли кнопка в текущем меню пользователя
        # Это решает проблему, когда одна и та же кнопка определена в нескольких flows
        current_menu_buttons = self.menus.get(user_current_flow, [])
        button_names = [btn.name for btn in current_menu_buttons]
        
        logger.debug(f"validate_flow: current_flow={self.current_flow}, user_flow={user_current_flow}")
        logger.debug(f"validate_flow: available buttons in '{user_current_flow}': {button_names}")
        logger.debug(f"validate_flow: is_nested={self.is_nested}, parent_name={self.parent_name}")
        
        # Для nested флоу: проверяем, что кнопка есть в меню текущего flow пользователя
        # Для корневых (не nested): проверяем, что пользователь в главном меню
        if self.is_nested:
            # Проверяем, что кнопка есть в доступном меню
            if self.current_flow not in button_names:
                logger.warning(f"validate_flow: кнопка '{self.current_flow}' не найдена в меню '{user_current_flow}'")
                content = self.errors["button_not_found"]
        else:
            # Для корневых элементов требуем быть в main
            if user_current_flow != "main":
                logger.warning(f"validate_flow: корневой элемент '{self.current_flow}', но user_flow='{user_current_flow}' (не 'main')")
                content = self.errors["button_not_found"]

        is_valid: bool = content is None

        return user, is_valid


class BaseChatHandler(BaseResponse):
    """Базовый класс для обработчика чата с AI"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        super().__init__(config=config, common=common)

        exit_button: InlineButton = InlineButton(**self.buttons["exit"])
        next_button: InlineButton = InlineButton(**self.buttons["next"])
        accept_button: InlineButton = InlineButton(**self.buttons["accept"])
        inactive_button: InlineButton = InlineButton(**self.buttons["inactive"])

        buttons_no_pagination: list[list[InlineButton]] = [
            [exit_button],
        ]
        buttons_with_pagination: list[list[InlineButton]] = [
            [inactive_button, accept_button, next_button],
            [exit_button],
        ]

        self.inline_markup: dict[str, dict[str, Any]] = {
            "no_pagination": build_inline_keyboard(buttons_no_pagination),
            "with_pagination": build_inline_keyboard(buttons_with_pagination),
        }

    async def validate_user(
        self,
        update: dict[str, Any],
        user: User | None,
    ) -> tuple[User | None, bool]:
        """
        Проверить пользователя
        
        Args:
            update: Обновление
            user: Пользователь
            
        Returns:
            tuple[User | None, bool]: Пользователь и флаг валидности
        """
        content: str | None = None

        if user is None:
            content = self.errors["user_not_registered"]

        is_valid: bool = content is None

        return user, is_valid

