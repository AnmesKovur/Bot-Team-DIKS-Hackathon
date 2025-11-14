#!/bin/bash

# Скрипт для запуска бота в Docker

set -e

echo "Ожидание готовности PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DATABASE" -c '\q' 2>/dev/null; do
  >&2 echo "PostgreSQL недоступен - ожидание..."
  sleep 1
done

echo "PostgreSQL готов!"

# Применение миграций
echo "Применение миграций..."
aerich upgrade || true

# Запуск бота
echo "Запуск бота..."
exec python main.py

