from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "is_vip" BOOL NOT NULL DEFAULT False,
    "is_admin" BOOL NOT NULL DEFAULT False,
    "max_id" VARCHAR(255) UNIQUE,
    "external_id" VARCHAR(255) UNIQUE
);
COMMENT ON TABLE "users" IS 'Модель пользователя';
CREATE TABLE IF NOT EXISTS "messages" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "json" JSONB NOT NULL,
    "text" TEXT,
    "user_id" INT REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "messages" IS 'Модель сообщения';
CREATE TABLE IF NOT EXISTS "user_states" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "use_pagination" BOOL NOT NULL DEFAULT False,
    "flow_stack" JSONB NOT NULL,
    "search_type" VARCHAR(255) NOT NULL DEFAULT '',
    "callback_message_id" VARCHAR(255),
    "callback_message_inline_markup" JSONB,
    "callback_message_need_to_delete" BOOL NOT NULL DEFAULT False,
    "cards_json" JSONB,
    "cards_current_page" INT NOT NULL DEFAULT -1,
    "cards_total_length" INT NOT NULL DEFAULT -1,
    "user_id" INT NOT NULL UNIQUE REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_states" IS 'Модель состояния пользователя';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
