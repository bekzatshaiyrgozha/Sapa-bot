from functools import wraps
from bot.db.database import AsyncSessionLocal
from bot.db.models import User
from sqlalchemy import select


def _reply_denied(update, context):
    if getattr(update, 'callback_query', None):
        return update.callback_query.answer("⛔ Доступ запрещён", show_alert=True)
    if getattr(update, 'message', None):
        return update.message.reply_text("⛔ Доступ запрещён")


def check_role(allowed_roles):
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(User).where(User.id == user_id))
                user = res.scalar_one_or_none()
                if not user or user.role not in allowed_roles:
                    await _reply_denied(update, context)
                    return
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator
