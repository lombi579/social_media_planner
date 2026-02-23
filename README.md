# Social Planner (Web-only)

Полноценный web-сервис (FastAPI + Jinja + SQLite) в стиле Buffer: создание, планирование и управление постами по колонкам.

## Что реализовано по "1:1" требованиям
В рамках этого репозитория добавлены ключевые подсистемы SaaS:
1. **OAuth-подключение аккаунтов и хранение refresh tokens** (YouTube через реальный OAuth start/callback + таблица `social_accounts`).
2. **Очередь автопубликаций с retries/dead-letter** (`publish_jobs`, `dead_letters`, `process_due_jobs`).
3. **Workspaces/teams/roles** (`workspaces`, `memberships`, роли `owner/admin/editor/viewer`).
4. **Биллинг и тарифы** (`plans`, `subscriptions`, смена тарифа workspace).
5. **Аудит, нотификации, webhooks** (`audit_events`, `notifications`, `webhooks`).

## Что уже работает как сервис
- Регистрация и логин пользователей (session-based auth).
- Изоляция данных по пользователям и workspace.
- Board UI с колонками: `Draft / Planned / Published / Failed`.
- CRUD постов, фильтры и поиск.
- Управление workspace, участниками, планом подписки, OAuth-аккаунтами и webhook.
- JSON API: `/api/posts`, `/api/audit`, `/api/notifications`, `/api/webhooks`.
- Запуск воркера публикации через `/api/worker/run`.
- Health endpoint: `GET /health`.
- Docker и docker-compose для запуска как сервиса.

## Локальный запуск
```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```
Открой: `http://localhost:8080`

## Реальное подключение YouTube OAuth
1. Создай OAuth client в Google Cloud и включи YouTube Data API.
2. В `.env` заполни:
   - `YOUTUBE_CLIENT_ID`
   - `YOUTUBE_CLIENT_SECRET`
   - `YOUTUBE_REDIRECT_URI` (по умолчанию `http://localhost:8080/oauth/youtube/callback`)
3. В интерфейсе нажми **Connect YouTube via Google OAuth**.

## Docker запуск
```bash
docker compose up --build
```

## ENV
- `APP_ENV` = `development|production`
- `APP_HOST` = host bind
- `APP_PORT` = port
- `APP_RELOAD` = `true|false`
- `DATABASE_FILE` = путь к sqlite
- `APP_SECRET_KEY` = ключ сессий (обязательно сменить в production)
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI` = OAuth конфиг YouTube

## Почему GitHub показывает "This branch has conflicts"
Это не ошибка приложения — это конфликт веток в Git (изменены одни и те же файлы в PR и target ветке).

```bash
git fetch origin
git checkout <your-branch>
git merge origin/main
# решить конфликты и убрать <<<<<<< ======= >>>>>>>
git add .
git commit -m "Resolve merge conflicts"
git push
```
