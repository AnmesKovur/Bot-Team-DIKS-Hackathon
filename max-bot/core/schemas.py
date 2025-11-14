from __future__ import annotations

from pydantic import BaseModel

from database.schemas import DBUser, DBUserState


class User(DBUser):
    """Схема пользователя с состоянием"""
    state: DBUserState


class Button(BaseModel):
    """Схема кнопки клавиатуры"""
    name: str
    privileged: int


class InlineButton(BaseModel):
    """Схема инлайн кнопки"""
    name: str
    url: str | None = None
    pattern: str | None = None


class MaxUpdate(BaseModel):
    """Схема обновления от MAX API"""
    update_id: int
    message: MaxMessage | None = None
    callback_query: MaxCallbackQuery | None = None


class MaxMessage(BaseModel):
    """Схема сообщения MAX"""
    message_id: str
    from_user: MaxUser
    chat: MaxChat
    text: str | None = None
    photo: list[MaxPhotoSize] | None = None
    video: MaxVideo | None = None


class MaxUser(BaseModel):
    """Схема пользователя MAX"""
    user_id: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class MaxChat(BaseModel):
    """Схема чата MAX"""
    chat_id: str
    type: str  # "private", "group", "supergroup", "channel"


class MaxPhotoSize(BaseModel):
    """Схема фото MAX"""
    file_id: str
    width: int
    height: int


class MaxVideo(BaseModel):
    """Схема видео MAX"""
    file_id: str
    width: int
    height: int
    duration: int


class MaxCallbackQuery(BaseModel):
    """Схема callback запроса MAX"""
    callback_id: str
    from_user: MaxUser
    message: MaxMessage | None = None
    data: str | None = None

