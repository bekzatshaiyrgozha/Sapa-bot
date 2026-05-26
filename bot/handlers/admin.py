from telegram import Update
from telegram.ext import ContextTypes
from bot.db.models import User, Subject, TeacherSubject
from bot.db.database import AsyncSessionLocal
from sqlalchemy import select
from bot.utils.auth import check_role


@check_role(['admin'])
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """Админ-меню:
Используйте команды:
/add_bm <tg_id> <full_name>
/add_teacher <tg_id> <full_name> <subject_id>
/add_subject <name> <bm_id>
/list_users
/list_subjects
/del_user <tg_id>
"""
    )


@check_role(['admin'])
async def add_bm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /add_bm <tg_id> <full_name>")
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await update.message.reply_text("tg_id должен быть числом")
        return
    name = " ".join(args[1:])
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == tg_id))
        exists = res.scalar_one_or_none()
        if exists:
            await update.message.reply_text("Пользователь уже существует")
            return
        user = User(id=tg_id, full_name=name, role='bm')
        session.add(user)
        await session.commit()
        await update.message.reply_text(f"БМ добавлен: {name} ({tg_id})")


@check_role(['admin'])
async def add_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Использование: /add_teacher <tg_id> <full_name> <subject_id>")
        return
    try:
        tg_id = int(args[0])
        subject_id = int(args[-1])
    except ValueError:
        await update.message.reply_text("tg_id и subject_id должны быть числами")
        return
    name = " ".join(args[1:-1])
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == tg_id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(id=tg_id, full_name=name, role='teacher')
            session.add(user)
        else:
            user.full_name = name
            user.role = 'teacher'
        # add mapping
        res2 = await session.execute(select(TeacherSubject).where(TeacherSubject.teacher_id == tg_id, TeacherSubject.subject_id == subject_id))
        mapping = res2.scalar_one_or_none()
        if not mapping:
            session.add(TeacherSubject(teacher_id=tg_id, subject_id=subject_id))
        await session.commit()
        await update.message.reply_text(f"Учитель добавлен/обновлён: {name} ({tg_id}), предмет {subject_id}")


@check_role(['admin'])
async def add_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /add_subject <name> <bm_id>")
        return
    try:
        bm_id = int(args[-1])
    except ValueError:
        await update.message.reply_text("bm_id должен быть числом")
        return
    name = " ".join(args[:-1])
    async with AsyncSessionLocal() as session:
        subj = Subject(name=name, bm_id=bm_id)
        session.add(subj)
        await session.commit()
        await update.message.reply_text(f"Предмет добавлен: {name} (id={subj.id})")


@check_role(['admin'])
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User))
        users = res.scalars().all()
        if not users:
            await update.message.reply_text("Пользователей нет")
            return
        lines = [f"{u.id} — {u.full_name} — {u.role}" for u in users]
        await update.message.reply_text("\n".join(lines))


@check_role(['admin'])
async def list_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Subject))
        subs = res.scalars().all()
        if not subs:
            await update.message.reply_text("Предметов нет")
            return
        lines = [f"{s.id} — {s.name} — BM:{s.bm_id}" for s in subs]
        await update.message.reply_text("\n".join(lines))


@check_role(['admin'])
async def del_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Использование: /del_user <tg_id>")
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await update.message.reply_text("tg_id должен быть числом")
        return
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == tg_id))
        u = res.scalar_one_or_none()
        if not u:
            await update.message.reply_text("Пользователь не найден")
            return
        await session.delete(u)
        await session.commit()
        await update.message.reply_text(f"Пользователь {tg_id} удалён")
