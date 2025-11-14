from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from common.utils import Sentinels


class DBUserState(BaseModel):
    """Схема состояния пользователя"""
    
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime
    created_at: datetime

    use_pagination: bool = False
    flow_stack: list[str] = Field(default_factory=lambda: ["main"])
    search_type: str = Sentinels.EMPTY_STR

    callback_message_id: str | None = None
    callback_message_inline_markup: dict[str, Any] | None = None
    callback_message_need_to_delete: bool = False

    cards_json: list[dict[str, Any]] | None = None
    cards_current_page: int = Sentinels.EMPTY_INT
    cards_total_length: int = Sentinels.EMPTY_INT


class DBUser(BaseModel):
    """Схема пользователя"""
    
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime
    created_at: datetime

    is_vip: bool
    is_admin: bool
    max_id: str | None
    external_id: str | None


class DBMessage(BaseModel):
    """Схема сообщения"""
    
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    json: dict
    text: str | None

