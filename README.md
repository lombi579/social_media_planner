# social_media_planner

Теперь в репозитории есть **2 интерфейса**:
- Telegram-бот для быстрого планирования.
- Web Board (в стиле Buffer) для визуального управления публикациями.

## Что сделано «как там» (Buffer-style MVP)
- Канбан-доска с колонками: `Planned / Published / Failed`.
- Создание карточки публикации через форму.
- Изменение статуса карточки прямо на доске.
- Удаление карточек.
- Постоянное хранение карточек в SQLite (`data/board.db`).

## Запуск
```bash
pip install -r requirements.txt
cp .env.example .env
```

### Telegram-бот
```bash
python main.py
```

### Web Board
```bash
uvicorn web_app:app --reload --port 8080
```
Открой: `http://localhost:8080`

## Команды бота
- `/start` — создать новую публикацию.
- `/accounts` — список аккаунтов.
- `/my_schedules` — ваши сохраненные публикации.
- `/buffer_like` — что нужно для full Buffer-уровня.

## Что дальше для полного уровня Buffer
- OAuth-подключение реальных каналов (YouTube/Instagram/TikTok).
- Фоновая очередь автопубликаций и retry-политики.
- Медиа-хранилище и обработка видео.
- Аналитика, роли команды, approvals, аудит.
- Drag&drop между колонками и календарный view.
