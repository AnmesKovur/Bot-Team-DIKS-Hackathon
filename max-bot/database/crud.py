from typing import Any

from database.models import MessageModel, UserModel, UserStateModel
from database.schemas import DBUser, DBUserState


async def get_or_create_user(max_id: str) -> tuple[DBUser, DBUserState]:
    """
    Получить или создать пользователя по MAX ID
    
    Args:
        max_id: ID пользователя в MAX мессенджере
        
    Returns:
        tuple[DBUser, DBUserState]: Пользователь и его состояние
    """
    user_model, _ = await UserModel.get_or_create(max_id=max_id)
    
    # Получаем или создаем состояние пользователя
    user_state_model, _ = await UserStateModel.get_or_create(user=user_model)
    
    # Загружаем связанные данные
    await user_model.fetch_related("user_state")
    
    user = DBUser.model_validate(user_model)
    user_state = DBUserState.model_validate(user_state_model)
    
    return user, user_state


async def update_user_state(user_id: int, state_data: dict[str, Any]) -> None:
    """
    Обновить состояние пользователя
    
    Args:
        user_id: ID пользователя
        state_data: Данные для обновления
    """
    from common.logger import get_logger
    logger = get_logger(__name__)
    
    # Исключаем поля, которые не должны обновляться
    fields_to_exclude = {"id", "created_at", "updated_at"}
    
    logger.debug(f"📥 Получены данные для обновления: {list(state_data.keys())}")
    clean_data = {k: v for k, v in state_data.items() if k not in fields_to_exclude}
    logger.debug(f"🧹 После фильтрации: {list(clean_data.keys())}")
    
    if clean_data:
        try:
            await UserStateModel.filter(user_id=user_id).update(**clean_data)
            logger.debug(f"✅ Состояние пользователя {user_id} обновлено")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления состояния: {e}")
            logger.error(f"   Попытка обновить поля: {list(clean_data.keys())}")
            raise


async def save_message(user_id: int, message_json: dict[str, Any], text: str | None = None) -> None:
    """
    Сохранить сообщение в базу данных
    
    Args:
        user_id: ID пользователя
        message_json: JSON представление сообщения
        text: Текст сообщения
    """
    await MessageModel.create(
        user_id=user_id,
        json=message_json,
        text=text
    )

