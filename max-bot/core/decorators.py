from functools import wraps
from logging import Logger
from typing import Any, Callable

from database.crud import get_or_create_user, update_user_state
from database.schemas import DBUser, DBUserState

from .schemas import User


def middleware(logger: Logger) -> Callable:
    """
    Middleware декоратор для обработчиков
    
    Args:
        logger: Логгер
        
    Returns:
        Callable: Декорированная функция
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            self,
            update: dict[str, Any],
            client: Any,
            user: User | None,
        ) -> tuple[User | None, int | None]:
            try:
                # Логируем входящее обновление
                logger.info(f"Обработка обновления: {update.get('update_id')}")
                
                # Вызываем оригинальную функцию
                user, state = await func(self, update, client, user)
                
                # Сохраняем состояние пользователя, если он есть
                if user is not None:
                    await update_user_state(
                        user_id=user.id,
                        state_data=user.state.model_dump(exclude={"id", "created_at", "updated_at"})
                    )
                
                return user, state
                
            except Exception as e:
                logger.error(f"Ошибка в обработчике: {e}", exc_info=True)
                return user, None
        
        return wrapper
    return decorator

