# Social Planner (Web-only)

Полноценный web-сервис (FastAPI + Jinja + SQLite) в стиле Buffer: создание, планирование и управление постами по колонкам.

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
После этого PR станет mergeable, и сайт останется целым.

## Что уже работает как сервис
- Board UI с колонками: `Draft / Planned / Published / Failed`.
- CRUD постов (создание, смена статуса, удаление).
- Поддержка платформ: YouTube / Instagram / TikTok / Telegram.
- Валидация даты `YYYY-MM-DD HH:MM`.
- SQLite-хранилище (`DATABASE_FILE`).
- JSON API: `GET /api/posts`.
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

## Чтобы было "как полноценный продаваемый SaaS"
Дальше нужны: auth/users/workspaces, OAuth-подключение реальных соц. аккаунтов, background workers для автопубликаций, billing, аналитика, аудит, медиа-хранилище.
