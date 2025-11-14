from logging import Logger
from types import MappingProxyType
from typing import Any, cast

from common.logger import get_logger

from .base import BaseCallback
from .decorators import middleware
from .keyboard import build_inline_keyboard, build_keyboard
from .max_client import MaxClient
from .response_builder import card_from_json
from .schemas import Button, InlineButton, User

logger: Logger = get_logger(__name__)


class ExitCallback(BaseCallback):
    """Обработчик кнопки 'Назад'"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        super().__init__(config=config, common=common)
        
        # Создаем клавиатуры для всех flows
        self.keyboard_markup: dict[str, dict[str, Any]] = {}
        
        flow_name: str
        flow_buttons: list[Button]
        for flow_name, flow_buttons in self.menus.items():
            self.keyboard_markup[flow_name] = {
                "vip": build_keyboard(buttons=flow_buttons, vip_status=True),
                "all": build_keyboard(buttons=flow_buttons, vip_status=False),
            }
    
    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать callback 'Назад'
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        if "callback_query" not in update:
            return user, None

        is_valid: bool
        user, is_valid = await self.validate_user(update=update, user=user)
        if not is_valid:
            return user, None

        user = cast(User, user)

        # Возвращаемся на уровень выше в стеке
        if len(user.state.flow_stack) > 1:
            user.state.flow_stack.pop()

        # Сбрасываем состояние поиска
        user.state.use_pagination = False
        user.state.search_type = ""
        user.state.cards_json = None
        
        # Определяем текущий flow после возврата
        current_flow_name = user.state.flow_stack[-1] if user.state.flow_stack else "main"
        
        # Получаем клавиатуру для текущего flow
        keyboard_markup = None
        if current_flow_name in self.keyboard_markup:
            keyboard_markup = (
                self.keyboard_markup[current_flow_name]["vip"]
                if user.is_vip
                else self.keyboard_markup[current_flow_name]["all"]
            )
        
        # Отправляем сообщение с клавиатурой
        chat_id = None
        if "message" in update["callback_query"]:
            message = update["callback_query"]["message"]
            chat_id = message["chat"]["id"]
        
        if chat_id and keyboard_markup:
            await client.send_message(
                chat_id=chat_id,
                text=self.content,
                reply_markup=keyboard_markup,
                parse_mode="Markdown",
            )
        
        logger.info(f"ExitCallback: возврат в flow '{current_flow_name}', stack={user.state.flow_stack}")

        return user, None


class HideMessageCallback(BaseCallback):
    """Обработчик кнопки 'Скрыть'"""
    
    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать callback 'Скрыть'
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        if "callback_query" not in update:
            return user, None

        is_valid: bool
        user, is_valid = await self.validate_user(update=update, user=user)
        if not is_valid:
            return user, None

        user = cast(User, user)

        # Удаляем сообщение
        if "message" in update["callback_query"]:
            message = update["callback_query"]["message"]
            chat_id = message["chat"]["id"]
            message_id = message["message_id"]
            
            await client.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )

        return user, None


class PaginationCallback(BaseCallback):
    """Обработчик кнопок пагинации"""
    
    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать callback пагинации
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        if "callback_query" not in update:
            return user, None

        is_valid: bool
        user, is_valid = await self.validate_user(update=update, user=user)
        if not is_valid:
            return user, None

        user = cast(User, user)

        # Получаем тип callback
        callback_data = update["callback_query"].get("data")
        
        if not callback_data or not user.state.cards_json:
            return user, None

        # Обрабатываем разные типы callback
        if callback_data == "previous_callback":
            if user.state.cards_current_page > 0:
                user.state.cards_current_page -= 1
        
        elif callback_data == "next_callback":
            if user.state.cards_current_page < user.state.cards_total_length - 1:
                user.state.cards_current_page += 1
        
        elif callback_data == "accept_callback":
            # Принять текущую карточку (может быть реализовано позже)
            pass
        
        elif callback_data == "inactive_callback":
            # Неактивная кнопка, ничего не делаем
            callback_id = update["callback_query"].get("id")
            if callback_id:
                await client.answer_callback_query(
                    callback_id=callback_id,
                    text="Это первая страница",
                )
            return user, None

        # Формируем новое содержимое
        current_card = user.state.cards_json[user.state.cards_current_page]
        content = card_from_json(
            current_card,
            user.state.cards_current_page,
            user.state.cards_total_length - 1
        )

        # Формируем клавиатуру
        previous_button = InlineButton(**self.buttons["previous"])
        next_button = InlineButton(**self.buttons["next"])
        inactive_button = InlineButton(**self.buttons["inactive"])
        accept_button = InlineButton(**self.buttons["accept"])
        exit_button = InlineButton(**self.buttons["exit"])

        # Определяем, какие кнопки показывать
        nav_buttons = []
        if user.state.cards_current_page > 0:
            nav_buttons.append(previous_button)
        else:
            nav_buttons.append(inactive_button)
        
        nav_buttons.append(accept_button)
        
        if user.state.cards_current_page < user.state.cards_total_length - 1:
            nav_buttons.append(next_button)
        else:
            nav_buttons.append(inactive_button)

        inline_markup = build_inline_keyboard([nav_buttons, [exit_button]])

        # Редактируем сообщение
        if "message" in update["callback_query"]:
            message = update["callback_query"]["message"]
            chat_id = message["chat"]["id"]
            message_id = message["message_id"]
            
            await client.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=inline_markup,
            )

        # Отправляем подтверждение callback
        callback_id = update["callback_query"].get("id")
        if callback_id:
            await client.answer_callback_query(callback_id=callback_id)

        return user, None

