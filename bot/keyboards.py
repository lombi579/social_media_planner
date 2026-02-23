from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models import Platform


def platforms_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="YouTube", callback_data=f"platform:{Platform.YOUTUBE}")],
            [InlineKeyboardButton(text="Instagram", callback_data=f"platform:{Platform.INSTAGRAM}")],
            [InlineKeyboardButton(text="TikTok", callback_data=f"platform:{Platform.TIKTOK}")],
        ]
    )


def accounts_keyboard(accounts: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=account, callback_data=f"account:{account}")]
            for account in accounts
        ]
    )


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no")],
        ]
    )
