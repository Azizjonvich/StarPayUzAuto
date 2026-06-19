from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery

import config


class IsAdmin(Filter):
    async def __call__(self, message: Message | CallbackQuery) -> bool:
        user_id = None
        if isinstance(message, Message):
            user_id = message.from_user.id if message.from_user else None
        elif isinstance(message, CallbackQuery):
            user_id = message.from_user.id if message.from_user else None
        return user_id is not None and user_id in config.ADMINS
