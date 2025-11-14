from logging import Logger
from types import MappingProxyType
from typing import Any, cast

from common.logger import get_logger

from .base import BaseCommand
from .decorators import middleware
from .max_client import MaxClient
from .schemas import User

logger: Logger = get_logger(__name__)


class StartCommand(BaseCommand):
    """Обработчик команды /start"""
    
    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать команду /start
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        if user is None:
            logger.error("Пользователь не найден для команды /start")
            return None, None

        user = cast(User, user)

        # Сбрасываем состояние пользователя
        user.state.flow_stack = ["main"]
        user.state.use_pagination = False
        user.state.search_type = ""
        user.state.cards_json = None

        # Выбираем клавиатуру в зависимости от VIP статуса
        keyboard_markup = (
            self.main_menu_keyboard_markup["vip"] 
            if user.is_vip 
            else self.main_menu_keyboard_markup["all"]
        )

        # Отправляем приветственное сообщение
        await self._send_message(
            update=update,
            client=client,
            content=self.content,
            reply_markup=keyboard_markup,
        )

        return user, None


class ResetCommand(BaseCommand):
    """Обработчик команды /reset"""
    
    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать команду /reset
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        if user is None:
            logger.error("Пользователь не найден для команды /reset")
            return None, None

        user = cast(User, user)

        # Сбрасываем состояние пользователя
        user.state.flow_stack = ["main"]
        user.state.use_pagination = False
        user.state.search_type = ""
        user.state.cards_json = None
        user.state.callback_message_id = None

        # Выбираем клавиатуру в зависимости от VIP статуса
        keyboard_markup = (
            self.main_menu_keyboard_markup["vip"] 
            if user.is_vip 
            else self.main_menu_keyboard_markup["all"]
        )

        # Отправляем сообщение о сбросе
        await self._send_message(
            update=update,
            client=client,
            content=self.content,
            reply_markup=keyboard_markup,
        )

        return user, None

