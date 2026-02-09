# voice-input

Телеграм-бот, который принимает голосовые сообщения, превращает их в текст через ИИ и затем отправляет этот текст на обработку ИИ.

## Быстрый старт

1. Установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Настройте переменные окружения (пример в `.env.example`). Файл `.env` будет загружен автоматически.

3. Запустите бота:

```bash
python main.py
```

## Запуск в Docker

1. Скопируйте `.env.example` в `.env` и заполните токены.
2. Запустите контейнер:

```bash
docker compose up --build
```

Все необходимые файлы для запуска уже находятся в репозитории (Dockerfile, docker-compose.yml, .env.example).

## Меню

Используйте команду `/menu` или кнопку **Начать диалог**, чтобы получить подсказку и перейти к отправке голосовых сообщений.

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` — токен вашего Telegram-бота.
- `OPENAI_API_KEY` — API-ключ OpenAI.
- `OPENAI_AUDIO_MODEL` — модель распознавания речи (по умолчанию `gpt-4o-mini-transcribe`).
- `OPENAI_CHAT_MODEL` — модель обработки текста (по умолчанию `gpt-4o-mini`).
- `OPENAI_SYSTEM_PROMPT` — системный промпт для обработки текста.
