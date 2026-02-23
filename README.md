# Social Planner (Web-only)

Полноценный web-сервис (FastAPI + Jinja + SQLite) в стиле Buffer: создание, планирование и управление постами по колонкам.

## Что реализовано по "1:1" требованиям
В рамках этого репозитория добавлены все базовые подсистемы SaaS:
1. **OAuth-подключение аккаунтов и хранение refresh tokens** (таблица `social_accounts`, форма подключения в UI).
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
