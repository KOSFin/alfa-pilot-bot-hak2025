# Alfa Pilot Smart Calculator

Умная система расчётов для малого и среднего бизнеса на базе FastAPI, aiogram и React. Проект сочетает телеграм-бота, веб-приложение и микросервисы (OpenSearch, Redis) для хранения знаний и принятия решений ИИ.

## Архитектура

- **Backend** (`Backend/`)
  - FastAPI приложение с эндпоинтами для загрузки документов, чата и поиска по памяти.
  - Интеграция с aiogram (webhook) для телеграм-бота.
  - Сервисы интеграции: Google Gemini (LLM и эмбеддинги), Groq Whisper для расшифровки голосовых сообщений, OpenSearch для векторного поиска, Redis для сессий и хранения планов расчёта.
- **Frontend** (`Frontend/`)
  - React + Vite мини-приложение (TWA) для загрузки документов, мониторинга памяти и общения с ИИ.
- **Инфраструктура**
  - Redis и OpenSearch развёртываются как отдельные сервисы (см. `.env` в `Backend/`).
  - Докерфайлы в `Backend/Dockerfile` и `Frontend/Dockerfile` обеспечивают развёртывание без docker-compose.

## Быстрый старт (локально)

1. **Подготовьте окружение**
	```bash
	cd Backend
	python -m venv .venv
	.venv\Scripts\activate
	pip install -r requirements.txt
	```
2. **Запустите backend**
	```bash
	uvicorn app.main:app --reload
	```
3. **Запустите frontend**
	```bash
	cd ../Frontend
	npm install
	npm run dev
	```

Backend поднимет FastAPI сервер на `http://localhost:8000`, frontend будет доступен на `http://localhost:5173`. Настройте переменные `.env` в `Backend/.env` (бот, ключи API, URL Redis и OpenSearch). Укажите `WEBHOOK_BASE_URL` (например, `https://your-domain`) и, при необходимости, `WEBHOOK_SECRET_TOKEN`, чтобы бот работал через webhook; без них backend автоматически переключится на long polling, что удобно для локальной отладки.

## Работа системы

1. **Первое взаимодействие**
	- Команда `/start` в Telegram: бот просит загрузить документы (кнопка веб-аппа) и пройти интеграцию с Альфа-Бизнес (заглушка).
	- Документы индексируются в OpenSearch, эмбеддинги создаются через Gemini, метаданные хранит Redis.
2. **Диалог и расчёты**
	- Сообщения и голосовые (через Groq Whisper) отправляются в orchestrator.
	- LLM решает, нужен ли расчёт или достаточно ответа-совета.
	- При выборе расчёта пользователь получает план и подтверждает запуск (веб-апп или команда `/execute_<ID>` в Telegram).
	- Код расчёта выполняется в безопасном sandbox (`python_code_executor`), результат возвращается пользователю и индексируется.
3. **Mini-app**
	- Отображает статистику индексации, список документов, контекст ответов ИИ и чат с подтверждением планов.

## Докер

### Backend

```bash
cd Backend
docker build -t alfa-pilot-backend .
docker run --env-file .env -p 8000:8000 alfa-pilot-backend
```

### Frontend

```bash
cd Frontend
docker build -t alfa-pilot-frontend .
docker run -p 8080:80 -e VITE_API_BASE_URL="http://backend-host:8000/api" alfa-pilot-frontend
```

## Тестовые интеграции

- **Redis**: используется для хранения диалогов, планов расчётов, кэшей.
- **OpenSearch**: два индекса (`alfa-pilot-knowledge`, `alfa-pilot-dialogs`) для документов и диалогов.
- **Gemini**: принятие решений и генерация эмбеддингов.
- **Groq Whisper**: API `whisper-large-v3-turbo` для транскрипций голосовых.

## Полезные команды

- Lint frontend: `npm run lint`
- Проверка зависимостей backend: `pip list`
- Health-чек: `GET http://localhost:8000/api/health`

## Структура backend

- `app/main.py` — точка входа FastAPI + webhook aiogram.
- `app/routers` — эндпоинты (чаты, документы, поиск).
- `app/services` — интеграции (AI, хранилища, транскрипция, калькулятор).
- `bot/handlers` — сценарии Telegram (старт, документы, голос, расчёт).

## Структура frontend

- `src/App.jsx` — основной интерфейс мини-приложения.
- `src/api.js` — клиентские вызовы API backend.
- `src/App.css` — стили панелей и чата.

## Дальнейшие шаги

- Настроить публичный URL для webhook Telegram (`/telegram/webhook`).
- Реализовать хранение загруженных документов в объектном хранилище.
- Добавить дополнительные инструменты для расчётов (например, интеграцию с внешними сервисами Альфа-Бизнес).