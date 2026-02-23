import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_settings
from bot.handlers import SCHEDULES, router
from bot.storage import ScheduleStorage


async def main() -> None:
    settings = load_settings()
    storage = ScheduleStorage(settings.schedules_file)
    SCHEDULES.extend(storage.load())

    bot = Bot(token=settings.bot_token)
    bot["storage"] = storage

    dp = Dispatcher(storage=MemoryStorage())
    dp["accounts"] = settings.accounts
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
