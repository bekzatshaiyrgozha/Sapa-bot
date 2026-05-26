import asyncio
from datetime import datetime
from bot.db.database import AsyncSessionLocal
from bot.db.models import WeeklyPlan, SlideSubmission
from bot.db.models import User, Subject
from sqlalchemy import select


async def check_deadlines(app):
    now = datetime.now()
    async with AsyncSessionLocal() as session:
        subq = select(SlideSubmission.plan_id)
        res = await session.execute(
            select(WeeklyPlan).where(WeeklyPlan.deadline < now).where(~WeeklyPlan.id.in_(subq))
        )
        overdue = res.scalars().all()

    for plan in overdue:
        try:
            async with AsyncSessionLocal() as session:
                teacher = await session.get(User, plan.teacher_id)
                subject = await session.get(Subject, plan.subject_id)
            teacher_name = teacher.full_name if teacher else str(plan.teacher_id)
            subject_name = subject.name if subject else str(plan.subject_id)
            await app.bot.send_message(
                chat_id=plan.created_by,
                text=(
                    f"⚠️ ДЕДЛАЙН ПРОСРОЧЕН\n"
                    f"Предмет: {subject_name}\n"
                    f"Учитель: {teacher_name}\n"
                    f"Тема: {plan.topic}\n"
                    f"Неделя: {plan.week_label}\n"
                    f"Дедлайн был: {plan.deadline.strftime('%d.%m.%Y %H:%M')}\n"
                    f"Слайд не загружен!"
                )
            )
        except Exception:
            pass


def start_background_scheduler(app):
    async def _bg():
        # initial delay
        await asyncio.sleep(60)
        while True:
            try:
                await check_deadlines(app)
            except Exception:
                pass
            await asyncio.sleep(15 * 60)

    # try to create the background task immediately (when running inside the app loop)
    try:
        app.create_task(_bg())
        return None
    except Exception:
        # if that fails, schedule it to be created after initialization
        try:
            app.post_init(lambda a: a.create_task(_bg()))
        except Exception:
            pass
    return None
    return None
