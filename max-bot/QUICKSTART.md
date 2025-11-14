# Быстрый старт MAX Bot

## 🚀 За 3 минуты

### Вариант 1: Docker (проще всего)

#### Запуск только бота (без AI)

```bash
# 1. Клонируйте репозиторий
git clone <repo-url>
cd max-bot

# 2. Создайте .env файл
cat > .env << EOF
MAX_API_TOKEN=your_token_here
DATABASE_URL=sqlite://data/db.sqlite3
EOF

# 3. Запустите только бот (комментируем AI в docker-compose.yml)
# Или просто:
docker-compose up -d bot

# 4. Проверьте логи
docker-compose logs -f bot
```

#### Запуск с AI Assistant

```bash
# 1. Клонируйте репозиторий
git clone <repo-url>
cd max-bot

# 2. Создайте .env файл
cat > .env << EOF
MAX_API_TOKEN=your_token_here
AI_API_URL=http://ai:8000

# Настройки PostgreSQL для AI Assistant
POSTGRES_HOST=psql
POSTGRES_PORT=5432
POSTGRES_USER=aidb-owner
POSTGRES_PASSWORD=sGyA3PqUwYFd
POSTGRES_DB=aidb

# Опционально: Yandex Cloud
YANDEX_API_KEY=your_yandex_api_key
YANDEX_CATALOG_ID=your_yandex_catalog_id
EOF

# 3. Запустите все сервисы (бот + AI + PostgreSQL)
docker-compose up -d

# 4. Настройте PostgreSQL (первый запуск)
# Создайте расширение pgvector
docker exec -it psql psql -U aidb-owner -d aidb -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 5. Примените миграции AI Assistant
docker exec -it max-ai alembic upgrade head

# 6. Импортируйте FAQ (опционально)
docker exec -it max-ai python scripts/import_faq_to_sqlalchemy.py

# 7. Проверьте логи
docker-compose logs -f bot
docker-compose logs -f ai

# 8. Откройте документацию AI API
# http://localhost:8000/docs
```

### Вариант 2: Локально

```bash
# 1. Установите Python 3.12+

# 2. Создайте виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Создайте .env
echo "MAX_API_TOKEN=your_token_here" > .env

# 5. Запустите
python main.py
```

## ✅ Проверка работы

### MAX Bot

Бот готов, когда в логах видите:

```
INFO - 🚀 Запуск бота в режиме long polling
```

### AI Assistant

AI Assistant готов, когда в логах видите:

```
INFO - ✅ Приложение запущено с SQLAlchemy
INFO:     Application startup complete.
```

Проверьте доступность API:

```bash
curl http://localhost:8000/faq/count
# Должно вернуть: {"count": 0}
```

## 🛑 Остановка

**Docker:**
```bash
docker-compose down
```

**Локально:**
```bash
# Ctrl+C в терминале
```

## 📝 Где взять токены?

### MAX_API_TOKEN

1. Перейдите на https://dev.max.ru
2. Создайте бота в разделе "Чат-бот и мини-приложение"
3. Скопируйте токен из раздела "Настроить"

### Yandex Cloud API (опционально)

Для использования YandexGPT в AI Assistant:

1. Зайдите в https://console.cloud.yandex.ru
2. Создайте или выберите каталог (folder)
3. Перейдите в "API-ключи" → "Создать API-ключ"
4. Скопируйте API-ключ и ID каталога

## 🔧 Настройка меню

Отредактируйте `configs/flow.json` для изменения структуры меню бота.

## 🤖 Работа с AI Assistant

### Добавление FAQ через API

```bash
# Добавить один FAQ элемент
curl -X POST "http://localhost:8000/faq/db" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Как работает бот?",
    "answer": "Бот использует MAX API для получения сообщений и отправки ответов."
  }'

# Получить количество FAQ
curl http://localhost:8000/faq/count

# Получить все FAQ
curl "http://localhost:8000/faq/db?limit=10&offset=0"
```

### Поиск по FAQ

```bash
# Семантический поиск с YandexGPT
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "gpt",
    "database_name": "faq",
    "top_k": 5,
    "history": [
      {"role": "user", "text": "Как зарегистрироваться в системе?"}
    ]
  }'
```

### Поиск компаний и продуктов

```bash
# Поиск компаний
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "semfuz",
    "database_name": "cmp",
    "top_k": 10,
    "history": [
      {"role": "user", "text": "IT компании"}
    ]
  }'

# Поиск продуктов
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "semfuz",
    "database_name": "prdcts",
    "top_k": 10,
    "history": [
      {"role": "user", "text": "CRM система"}
    ]
  }'
```

## 📖 Полная документация

См. [README.md](README.md)

