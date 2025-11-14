from __future__ import annotations

from tortoise import Model, fields

from common.utils import Sentinels


class UserModel(Model):
    """Модель пользователя"""
    
    id = fields.IntField(pk=True, generated=True)

    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    is_vip = fields.BooleanField(default=False)
    is_admin = fields.BooleanField(default=False)
    
    # ID пользователя в MAX мессенджере
    max_id = fields.CharField(max_length=255, unique=True, null=True)
    external_id = fields.CharField(max_length=255, unique=True, null=True)

    user_state: fields.ReverseRelation[UserStateModel]

    class Meta:  # type: ignore
        table: str = "users"


class UserStateModel(Model):
    """Модель состояния пользователя"""
    
    id = fields.IntField(pk=True, generated=True)

    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    # Состояние флоу пользователя
    use_pagination = fields.BooleanField(default=False)
    flow_stack = fields.JSONField(default=lambda: ["main"])
    search_type = fields.CharField(max_length=255, default=Sentinels.EMPTY_STR)

    # Данные для callback
    callback_message_id = fields.CharField(max_length=255, null=True)
    callback_message_inline_markup = fields.JSONField(null=True)
    callback_message_need_to_delete = fields.BooleanField(default=False)

    # Состояние карточек
    cards_json = fields.JSONField(null=True)
    cards_current_page = fields.IntField(default=Sentinels.EMPTY_INT)
    cards_total_length = fields.IntField(default=Sentinels.EMPTY_INT)

    user = fields.OneToOneField(
        "models.UserModel",
        related_name="user_state",
        on_delete=fields.CASCADE,
    )

    class Meta:  # type: ignore
        table: str = "user_states"


class MessageModel(Model):
    """Модель сообщения"""
    
    id = fields.IntField(pk=True, generated=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    json = fields.JSONField()
    text = fields.TextField(null=True)
    user = fields.ForeignKeyField(
        "models.UserModel",
        related_name="messages",
        on_delete=fields.CASCADE,
        null=True,
    )

    class Meta:  # type: ignore
        table = "messages"

