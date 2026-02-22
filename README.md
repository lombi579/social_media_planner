# Social Planner (Web-only)

Полностью убран Telegram-бот. Репозиторий теперь — цельное web-приложение в стиле Buffer.

## Что готово сейчас
- Чистый web-сервис на FastAPI + Jinja.
- Buffer-style board с колонками: `Draft / Planned / Published / Failed`.
- Создание публикации через форму.
- Поддержка платформ: **YouTube, Instagram, TikTok, Telegram Channels**.
- Обновление статуса карточки на доске.
- Удаление карточки.
- Постоянное хранение в SQLite (`data/app.db`).

## Быстрый запуск
```bash
pip install -r requirements.txt
python main.py
```

Открой: `http://localhost:8080`

## Структура
- `web_app.py` — маршруты и web-слой.
- `web/repository.py` — SQLite-репозиторий.
- `web/templates/board.html` — UI.
- `web/static/board.css` — стили.
- `main.py` — запуск uvicorn.

## Что нужно для «продавать как Buffer 1:1»
Сейчас это сильный MVP UI/CRUD. Для полноценно продаваемого SaaS уровня Buffer ещё нужны:
1. Авторизация, workspace/team, роли и permissions.
2. OAuth-подключение реальных аккаунтов и каналов по каждой платформе.
3. Фоновая очередь публикаций + retries + webhooks статусов.
4. Загрузка и хранение медиа (S3-compatible), обработка видео, thumbnails.
5. Аналитика, биллинг, аудит-логи, уведомления.
6. Drag&drop, календарный view, bulk actions, templates.

Если хотите, следующим шагом могу добавить именно **SaaS-ядро**: auth + tenants + account connections + publish workers.
