.PHONY: help install run docker-build docker-run docker-stop docker-logs clean

help:
	@echo "Доступные команды:"
	@echo "  make install       - Установить зависимости"
	@echo "  make run           - Запустить бота локально"
	@echo "  make docker-build  - Собрать Docker образ"
	@echo "  make docker-run    - Запустить через Docker Compose"
	@echo "  make docker-stop   - Остановить Docker контейнеры"
	@echo "  make docker-logs   - Показать логи Docker"
	@echo "  make clean         - Очистить временные файлы"

install:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

run:
	.venv/bin/python main.py

docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f bot

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache

