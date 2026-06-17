"""Access control middleware - restrict bot usage to specific users"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message
import config


class AccessControlMiddleware(BaseMiddleware):
    """Middleware для проверки доступа к боту"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем username пользователя
        username = None
        
        if isinstance(event, Update):
            if event.message:
                username = event.message.from_user.username
            elif event.callback_query:
                username = event.callback_query.from_user.username
            elif event.inline_query:
                username = event.inline_query.from_user.username
        
        # Если ALLOWED_USERNAMES пуст или содержит "*" — доступ открыт всем
        allowed = config.ALLOWED_USERNAMES
        if not allowed or "*" in allowed:
            return await handler(event, data)

        # Проверяем доступ
        if username and username in allowed:
            return await handler(event, data)
        else:
            if isinstance(event, Update) and event.message:
                await event.message.answer(
                    "🚫 <b>Kirish taqiqlangan</b>\n\n"
                    "Bu bot test rejimida va faqat ruxsat etilgan foydalanuvchilar uchun mavjud.\n\n"
                    "Kirish uchun murojaat qiling: @StarPayUzAdmin",
                    parse_mode="HTML"
                )
            return
