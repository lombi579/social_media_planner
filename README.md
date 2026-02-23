# Social Planner (Web-only)

Полноценный web-сервис (FastAPI + Jinja + SQLite) в стиле Buffer: создание, планирование и управление постами по колонкам.

## Важное про "сделай как Buffer"
Сейчас проект = **рабочий production-ready MVP** (сайт, API, Docker, CRUD, фильтры, редактирование, тесты).
Это уже можно развернуть и использовать как сервис. Но **1-в-1 Buffer SaaS** требует ещё OAuth-интеграций с реальными соцсетями, биллинга, ролей, очередей автопостинга, аналитики.

## Почему GitHub показывает "This branch has conflicts"
Это не ошибка приложения — это конфликт **веток в Git**. Значит, в вашей PR-ветке и в целевой ветке (`main`/`master`) изменены одни и те же файлы.

Как исправить безопасно:
```bash
git fetch origin
git checkout <your-branch>
git merge origin/main
# решить конфликты в файлах, убрать <<<<<<< ======= >>>>>>>
git add .
git commit -m "Resolve merge conflicts"
git push
```

## Что уже работает как сервис
- Board UI с колонками: `Draft / Planned / Published / Failed`.
- CRUD постов (создание, редактирование, смена статуса, удаление).
- Фильтры по статусу/платформе + поиск по контенту.
- Поддержка платформ: YouTube / Instagram / TikTok / Telegram.
- Валидация даты `YYYY-MM-DD HH:MM`.
- SQLite-хранилище (`DATABASE_FILE`).
- JSON API: `GET /api/posts` (поддерживает фильтры `status/platform/q`).
- Health endpoint: `GET /health`.

## Локальный запуск
```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```
Открой: `http://localhost:8080`

## Docker запуск (production-like)
```bash
docker compose up --build
```

## ENV
- `APP_ENV` = `development|production`
- `APP_HOST` = host bind
- `APP_PORT` = port
- `APP_RELOAD` = `true|false`
- `DATABASE_FILE` = путь к sqlite

## Структура
- `web_app.py` — web и API маршруты
- `web/repository.py` — CRUD + валидации + SQLite
- `web/settings.py` — конфигурация окружения
- `web/templates/board.html` — интерфейс доски
- `web/static/board.css` — стили
- `main.py` — запуск сервера

## Что добавить дальше для полного SaaS как Buffer
1. OAuth-подключение аккаунтов платформ и хранение refresh tokens.
2. Очередь автопубликаций (workers + retries + dead-letter).
3. Мультипользовательность: auth, workspaces, roles, permissions.
4. Биллинг и тарифы.
5. Аналитика, audit trail, нотификации.
