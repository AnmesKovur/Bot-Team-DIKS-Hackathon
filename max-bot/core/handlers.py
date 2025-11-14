from logging import Logger
from types import MappingProxyType
from typing import Any, cast

from clients.ai import AIClient
from common.logger import get_logger
from common.utils import Sentinels

from .base import BaseChatHandler, BaseHandler
from .decorators import middleware
from .keyboard import build_inline_keyboard, build_keyboard
from .max_client import MaxClient
from .response_builder import card_from_json
from .schemas import Button, InlineButton, User

logger: Logger = get_logger(__name__)


class StaticHandler(BaseHandler):
    """Обработчик статического контента"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        super().__init__(config=config, common=common)

        buttons: list[InlineButton] = []
        for button_config in config["buttons"]["inline"]:
            buttons.append(InlineButton(**button_config))

        # Если кнопок нет - не создаем клавиатуру (MAX API не принимает пустые)
        self.inline_markup: dict[str, Any] | None = build_inline_keyboard(buttons) if buttons else None

    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать обновление
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        if "message" not in update:
            return user, None

        is_valid: bool
        user, is_valid = await self.validate_user(update=update, user=user)
        if not is_valid:
            return user, None

        user = cast(User, user)

        # StaticHandler - это конечные информационные страницы
        # Они просто показывают контент без изменения навигационного состояния
        logger.info(f"StaticHandler: показываем контент '{self.current_flow}'")

        # Отправляем сообщение
        await self._send_message(
            update=update,
            client=client,
            content=self.content,
            photo=self.photo,
            reply_markup=self.inline_markup,
        )

        return user, None


class ExtendedStaticHandler(BaseHandler):
    """Обработчик расширенного статического контента с клавиатурой"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        super().__init__(config=config, common=common)

        buttons: list[Button] = self.menus[self.current_flow]
        
        # Для вложенных flows добавляем кнопку "Назад" внизу
        is_nested = config.get("is_nested", False)
        if is_nested:
            # Создаем кнопку "Назад" из конфигурации
            exit_button_config = self.buttons["exit"]
            exit_button = Button(name=exit_button_config["name"], privileged=False)
            buttons_with_back = buttons + [exit_button]
            
            self.keyboard_markup: dict[str, dict[str, Any]] = {
                "vip": build_keyboard(buttons_with_back, True),
                "all": build_keyboard(buttons_with_back, False),
            }
        else:
            self.keyboard_markup: dict[str, dict[str, Any]] = {
                "vip": build_keyboard(buttons, True),
                "all": build_keyboard(buttons, False),
            }

    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать обновление
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        if "message" not in update:
            logger.warning(f"ExtendedStaticHandler: нет 'message' в update")
            return None, None

        is_valid: bool
        user, is_valid = await self.validate_user(update=update, user=user)
        if not is_valid:
            logger.warning(f"ExtendedStaticHandler: validate_user failed")
            return user, None

        user = cast(User, user)

        logger.info(f"ExtendedStaticHandler: current_flow={self.current_flow}, user flow_stack={user.state.flow_stack}")
        logger.info(f"ExtendedStaticHandler: is_nested={self.is_nested}, parent_name={self.parent_name}")
        
        # Для корневых элементов (не nested) - сбрасываем стек
        if not self.is_nested:
            logger.info(f"ExtendedStaticHandler: Корневой элемент, сбрасываем flow_stack")
            user.state.flow_stack = ["main"]
        
        user, is_valid = await self.validate_flow(update=update, user=user)
        if not is_valid:
            logger.warning(f"ExtendedStaticHandler: validate_flow failed for {self.current_flow}")
            logger.warning(f"  is_nested={self.is_nested}, parent_name='{self.parent_name}', current_user_flow='{user.state.flow_stack[-1] if user.state.flow_stack else 'empty'}'")
            return user, None

        logger.info(f"ExtendedStaticHandler: ✅ Все валидации пройдены, отправляем сообщение")
        user.state.flow_stack.append(self.current_flow)

        keyboard_markup: dict[str, Any] = (
            self.keyboard_markup["vip"] if user.is_vip else self.keyboard_markup["all"]
        )

        # Отправляем сообщение
        await self._send_message(
            update=update,
            client=client,
            content=self.content,
            photo=self.photo,
            reply_markup=keyboard_markup,
        )

        return user, None


class ManagedHandler(BaseHandler):
    """Обработчик управляемого контента (поиск с AI)"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        super().__init__(config=config, common=common)

        self.search_type: str = config["search_type"]
        self.use_pagination: bool = config["use_pagination"]

    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать обновление
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        if "message" not in update:
            return None, None

        is_valid: bool
        user, is_valid = await self.validate_user(update=update, user=user)
        if not is_valid:
            return user, None

        user = cast(User, user)

        user, is_valid = await self.validate_flow(update=update, user=user)
        if not is_valid:
            return user, None

        user.state.search_type = self.search_type
        user.state.flow_stack.append(self.current_flow)
        user.state.use_pagination = self.use_pagination

        # Отправляем сообщение
        await self._send_message(
            update=update,
            client=client,
            content=self.content,
            photo=self.photo,
        )

        return user, None


class ChatHandler(BaseChatHandler):
    """Обработчик чата с AI"""
    
    def __init__(self, config: dict[str, Any], common: MappingProxyType) -> None:
        super().__init__(config=config, common=common)
        self.common = common

        # Атрибуты для ChatHandler
        self.managed_flows: set[str] = common["managed_flows"]

    @middleware(logger)
    async def __call__(
        self,
        update: dict[str, Any],
        client: MaxClient,
        user: User | None,
    ) -> tuple[User | None, int | None]:
        """
        Обработать обновление
        
        Args:
            update: Обновление от MAX
            client: Клиент MAX
            user: Пользователь
            
        Returns:
            tuple[User | None, int | None]: Пользователь и состояние
        """
        logger.info("=== ChatHandler начало выполнения ===")
        
        if "message" not in update:
            logger.warning("ChatHandler: нет сообщения")
            return None, None

        is_valid: bool
        user, is_valid = await self.validate_user(update=update, user=user)
        if not is_valid:
            return user, None

        user = cast(User, user)

        user_current_flow: str = user.state.flow_stack[-1]
        if (
            user_current_flow not in self.managed_flows
            and user_current_flow != Sentinels.EMPTY_STR
        ):
            user.state.use_pagination = False
            user.state.search_type = "questions"
            user.state.flow_stack.append(Sentinels.EMPTY_STR)

        # Получаем текст сообщения
        message_text = update["message"].get("text", "")

        search_type: str = "gpt"
        database_name: str = "faq"
        if user.state.search_type == "companies":
            search_type = "semfuz"
            database_name = "cmp"

        elif user.state.search_type == "products":
            search_type = "semfuz"
            database_name = "prdcts"

        payload: dict[str, Any] = {
            "search_type": search_type,
            "top_k": 10 if user.state.use_pagination else 1,
            "database_name": database_name,
            "history": [{"role": "user", "text": message_text}],
        }
        response: dict[str, Any] = await AIClient.post_request(payload=payload)

        content: str

        if (
            response.get("answer")
            or response.get("cards")
            or response.get("product_cards")
        ):
            if user.state.use_pagination:
                cards: list[dict[str, Any]] | None = response.get("cards")
                if cards is None:
                    cards = response.get("product_cards")

                if cards is not None:
                    current_page: int = 0
                    total_length: int = len(cards)

                    user.state.cards_json = cards
                    user.state.cards_current_page = current_page
                    user.state.cards_total_length = total_length

                    content = card_from_json(cards[0], current_page, total_length - 1)

                else:
                    content = self.errors["query_not_found"]

            else:
                content = response.get("answer", self.errors["query_not_found"])

        else:
            user.state.cards_json = None

            content = self.errors["query_not_found"]

        # Заменяем ссылку на Яндекс
        if "https://ya.ru" in content:
            content = "У меня нет информации по этому вопросу"

        # Определяем клавиатуру
        inline_markup: dict[str, Any] | None = None
        if (
            user.state.use_pagination
            and user.state.cards_json is not None
            and user.state.cards_total_length > 1
        ):
            inline_markup = self.inline_markup["with_pagination"]
        else:
            inline_markup = self.inline_markup["no_pagination"]

        # Отправляем сообщение
        chat_id = update["message"]["chat"]["id"]
        await self._remove_callback_buttons(client, user, chat_id)
        
        sent_message = await self._send_message(
            update=update,
            client=client,
            content=content,
            reply_markup=inline_markup,
        )
        
        if sent_message:
            user.state.callback_message_inline_markup = None
            user.state.callback_message_need_to_delete = False
            user.state.callback_message_id = sent_message.get("message_id")

        return user, None

