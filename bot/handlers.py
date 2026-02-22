from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import accounts_keyboard, confirmation_keyboard, platforms_keyboard
from bot.models import Platform, UploadRequest
from bot.states import PlannerStates
from bot.storage import ScheduleStorage

router = Router()

SCHEDULES: list[UploadRequest] = []


def _parse_publish_at(raw: str) -> datetime | None:
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(PlannerStates.choosing_platform)
    await message.answer(
        "Привет! Давай запланируем публикацию.\n"
        "1) Выбери платформу\n"
        "2) Выбери аккаунт\n"
        "3) Укажи время публикации\n"
        "4) Добавь описание и хэштеги",
        reply_markup=platforms_keyboard(),
    )


@router.message(Command("accounts"))
async def list_accounts(message: Message, accounts: dict[Platform, list[str]]) -> None:
    text = "Доступные аккаунты:\n"
    for platform, values in accounts.items():
        text += f"\n• {platform.title()}: {', '.join(values)}"
    await message.answer(text)


@router.message(Command("my_schedules"))
async def my_schedules(message: Message) -> None:
    user_schedules = [entry for entry in SCHEDULES if entry.user_id == message.from_user.id]
    if not user_schedules:
        await message.answer("Пока нет запланированных публикаций.")
        return

    lines = ["Твои запланированные публикации:"]
    for idx, item in enumerate(user_schedules, start=1):
        hashtags = item.hashtags or "(не указаны)"
        lines.append(
            f"{idx}. #{item.id[:8]} {item.platform.title()} | {item.account} | {item.publish_at:%Y-%m-%d %H:%M}\n"
            f"Описание: {item.description}\n"
            f"Хэштеги: {hashtags}\n"
            f"Статус: {item.status}"
        )
    await message.answer("\n\n".join(lines))


@router.message(Command("buffer_like"))
async def buffer_like_help(message: Message) -> None:
    await message.answer(
        "Да, можно сделать сервис уровня Buffer, но это отдельный продукт.\n"
        "Что уже есть сейчас: планирование через Telegram и сохранение расписания в файл.\n"
        "Для уровня Buffer дальше нужно: веб-кабинет, роли, календарь/board, авто-публикации, аналитика, retries, billing."
    )


@router.callback_query(PlannerStates.choosing_platform, F.data.startswith("platform:"))
async def choose_platform(
    callback: CallbackQuery,
    state: FSMContext,
    accounts: dict[Platform, list[str]],
) -> None:
    platform = Platform(callback.data.split(":", maxsplit=1)[1])
    await state.update_data(platform=platform)
    await state.set_state(PlannerStates.choosing_account)
    await callback.message.answer(
        f"Выбрана платформа: {platform.title()}\nВыбери аккаунт:",
        reply_markup=accounts_keyboard(accounts[platform]),
    )
    await callback.answer()


@router.callback_query(PlannerStates.choosing_account, F.data.startswith("account:"))
async def choose_account(callback: CallbackQuery, state: FSMContext) -> None:
    account = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(account=account)
    await state.set_state(PlannerStates.choosing_time)
    await callback.message.answer(
        "Отлично. Введи время публикации в формате YYYY-MM-DD HH:MM\n"
        "Например: 2026-02-25 18:30"
    )
    await callback.answer()


@router.message(PlannerStates.choosing_time)
async def enter_time(message: Message, state: FSMContext) -> None:
    publish_at = _parse_publish_at(message.text or "")
    if publish_at is None:
        await message.answer("Неверный формат времени. Пример: 2026-02-25 18:30")
        return

    await state.update_data(publish_at=publish_at)
    await state.set_state(PlannerStates.entering_description)
    await message.answer("Теперь введи описание для поста/ролика:")


@router.message(PlannerStates.entering_description)
async def enter_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    await state.update_data(description=description)
    await state.set_state(PlannerStates.entering_hashtags)
    await message.answer("Добавь хэштеги через пробел (или напиши '-' чтобы пропустить):")


@router.message(PlannerStates.entering_hashtags)
async def enter_hashtags(message: Message, state: FSMContext) -> None:
    hashtags = (message.text or "").strip()
    if hashtags == "-":
        hashtags = ""

    await state.update_data(hashtags=hashtags)
    payload = await state.get_data()

    preview = (
        "Проверь данные перед сохранением:\n"
        f"Платформа: {payload['platform'].title()}\n"
        f"Аккаунт: {payload['account']}\n"
        f"Время: {payload['publish_at']:%Y-%m-%d %H:%M}\n"
        f"Описание: {payload['description']}\n"
        f"Хэштеги: {payload['hashtags'] or '(не указаны)'}"
    )
    await state.set_state(PlannerStates.confirmation)
    await message.answer(preview, reply_markup=confirmation_keyboard())


@router.callback_query(PlannerStates.confirmation, F.data == "confirm:yes")
async def confirm(callback: CallbackQuery, state: FSMContext) -> None:
    payload = await state.get_data()
    request = UploadRequest(
        id=uuid4().hex,
        user_id=callback.from_user.id,
        platform=payload["platform"],
        account=payload["account"],
        publish_at=payload["publish_at"],
        description=payload["description"],
        hashtags=payload.get("hashtags") or None,
    )
    SCHEDULES.append(request)
    storage: ScheduleStorage = callback.bot["storage"]
    storage.save(SCHEDULES)
    await state.clear()
    await callback.message.answer(
        "Готово ✅ Публикация запланирована и сохранена.\n"
        "Используй /start чтобы создать новую, /my_schedules чтобы посмотреть список."
    )
    await callback.answer()


@router.callback_query(PlannerStates.confirmation, F.data == "confirm:no")
async def cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Окей, отменил. Нажми /start чтобы начать заново.")
    await callback.answer()
