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
        
        # Проверяем доступ
        if username and username in config.ALLOWED_USERNAMES:
            # Доступ разрешен - продолжаем обработку
            return await handler(event, data)
        else:
            # Доступ запрещен - отправляем сообщение
            if isinstance(event, Update) and event.message:
                await event.message.answer(
                    "🚫 <b>Доступ запрещен</b>\n\n"
                    "Этот бот находится в режиме тестирования и доступен только авторизованным пользователям.\n\n"
                    "По вопросам доступа обращайтесь: @StarPayUzAdmin",
                    parse_mode="HTML"
                )
            return  # Прерываем обработку
