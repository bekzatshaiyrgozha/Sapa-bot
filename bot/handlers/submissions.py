import asyncio
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.db.database import AsyncSessionLocal
from bot.db.models import SlideSubmission, User
from sqlalchemy import select


async def list_submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user or user.role not in ('admin', 'bm'):
            await update.message.reply_text('Доступно только для админов и БМ.')
            return

        res2 = await session.execute(select(SlideSubmission).order_by(SlideSubmission.uploaded_at.desc()).limit(20))
        subs = res2.scalars().all()

        if not subs:
            await update.message.reply_text('Подач пока нет.')
            return

        lines = []
        for s in subs:
            # get teacher name if available
            t = None
            if s.teacher_id:
                tres = await session.execute(select(User).where(User.id == s.teacher_id))
                t = tres.scalar_one_or_none()
            tname = t.full_name if t and t.full_name else str(s.teacher_id)
            summary = s.ai_check_status or 'unknown'
            # include short snippet of ai_check_result for quick inspection
            snippet = ''
            if s.ai_check_result:
                try:
                    import json as _json
                    raw = _json.dumps(s.ai_check_result, ensure_ascii=False)
                except Exception:
                    raw = str(s.ai_check_result)
                snippet = raw[:200]
            lines.append(f"{s.id}: {tname} | plan {s.plan_id} | {s.file_name} | {summary} | {snippet}")

        # send as plain text (short list)
        await update.message.reply_text('\n'.join(lines))


def get_handler():
    return CommandHandler('submissions', list_submissions)
