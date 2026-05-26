import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.db.database import AsyncSessionLocal
from bot.db.models import User, Subject, TeacherSubject, WeeklyPlan, SlideSubmission
from bot.utils.slide_parser import parse_file
from bot.services.ai_checker import check_presentation, format_ai_result
from telegram.error import BadRequest
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user or user.role != 'teacher':
            await update.message.reply_text('Вы не зарегистрированы как учитель.')
            return
        res2 = await session.execute(select(TeacherSubject).where(TeacherSubject.teacher_id == user_id))
        mappings = res2.scalars().all()
        subj_ids = [m.subject_id for m in mappings]
        if not subj_ids:
            await update.message.reply_text('У вас нет назначенных предметов.')
            return
        res3 = await session.execute(select(Subject).where(Subject.id.in_(subj_ids)))
        subjects = res3.scalars().all()

    keyboard = [[InlineKeyboardButton(s.name, callback_data=f"t_sub:{s.id}")] for s in subjects]
    await update.message.reply_text('Ваши предметы:', reply_markup=InlineKeyboardMarkup(keyboard))


async def subject_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith('t_sub:'):
        await query.answer('Неверный запрос', show_alert=True)
        return
    subject_id = int(data.split(':', 1)[1])
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(WeeklyPlan).where(
                WeeklyPlan.teacher_id == user_id,
                WeeklyPlan.subject_id == subject_id
            )
        )
        plans = res.scalars().all()
    if not plans:
        await query.edit_message_text('Нет планов для выбранного предмета.')
        return
    keyboard = []
    for p in plans:
        async with AsyncSessionLocal() as session:
            res2 = await session.execute(
                select(SlideSubmission)
                .where(SlideSubmission.plan_id == p.id)
                .order_by(SlideSubmission.uploaded_at.desc())
            )
            sub = res2.scalars().first()
        status = sub.ai_check_status if sub else 'not uploaded'
        btn_text = f"{p.week_label} — {p.topic} ({p.lesson_date}) [{status}]"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"t_plan:{p.id}")])
    await query.edit_message_text('Выберите план:', reply_markup=InlineKeyboardMarkup(keyboard))


async def plan_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith('t_plan:'):
        await query.answer('Неверный запрос', show_alert=True)
        return
    plan_id = int(data.split(':', 1)[1])
    context.user_data['selected_plan'] = plan_id
    await query.edit_message_text('План выбран. Пожалуйста, загрузите файл (.pptx или .pdf).')


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    doc = msg.document
    if not doc:
        await msg.reply_text('Отправьте .pptx или .pdf файл.')
        return

    plan_id = context.user_data.get('selected_plan')
    if not plan_id:
        await msg.reply_text('Сначала выберите план (через /start).')
        return

    file_id = doc.file_id
    fname = doc.file_name or 'upload'
    download_dir = os.path.join(os.getcwd(), '.downloads')
    os.makedirs(download_dir, exist_ok=True)
    dest = os.path.join(download_dir, f"{plan_id}_{fname}")

    # --- Файлды жүктеу ---
    try:
        f = await context.bot.get_file(file_id)
        await f.download_to_drive(dest)
    except BadRequest:
        await msg.reply_text('Ошибка: файл слишком большой (<50MB). Уменьшите размер и попробуйте снова.')
        return
    except Exception as e:
        await msg.reply_text(f'Ошибка при загрузке файла: {e}')
        return

    await msg.reply_text('📥 Файл принят. Идёт проверка, подождите...')

    # --- DB-ге pending статусымен сақтау ---
    async with AsyncSessionLocal() as session:
        sub = SlideSubmission(
            plan_id=plan_id,
            teacher_id=update.effective_user.id,
            file_id=file_id,
            file_name=fname,
            ai_check_status='pending'
        )
        session.add(sub)
        await session.commit()
        submission_id = sub.id

    # --- Слайд мәтінін парсинг ---
    try:
        slide_text = await asyncio.to_thread(parse_file, dest)
    except Exception as e:
        logger.exception('Parsing error for submission %s', submission_id)
        await msg.reply_text(f'Ошибка при разборе файла: {e}')
        return

    if not slide_text or slide_text.strip() == '':
        logger.warning('Empty parsed text for submission %s', submission_id)
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(SlideSubmission).where(SlideSubmission.id == submission_id))
            s = res.scalar_one_or_none()
            if s:
                s.ai_check_result = {'error': 'parsed_text_empty'}
                s.ai_check_status = 'error'
                await session.commit()
        await msg.reply_text(
            '⚠️ Файл принят, но текст не найден.\n'
            'Возможно, презентация содержит только изображения.\n'
            'Пожалуйста, добавьте текст на слайды и загрузите заново.'
        )
        return

    # --- AI тексеру ---
    try:
        ai_result = await asyncio.to_thread(check_presentation, slide_text)
    except Exception as e:
        logger.exception('AI checker error for submission %s', submission_id)
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(SlideSubmission).where(SlideSubmission.id == submission_id))
            s = res.scalar_one_or_none()
            if s:
                s.ai_check_result = {'error': str(e)}
                s.ai_check_status = 'error'
                await session.commit()
        await msg.reply_text(f'❌ Ошибка AI-проверки: {e}')
        return

    # --- Статусты анықтау ---
    if isinstance(ai_result, dict) and ai_result.get('overall_status') == 'PASSED':
        status = 'passed'
    else:
        status = 'failed'

    # --- DB-ге нәтижені сақтау ---
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(SlideSubmission).where(SlideSubmission.id == submission_id))
        s = res.scalar_one_or_none()
        if s:
            s.ai_check_result = ai_result
            s.ai_check_status = status
            await session.commit()

    # --- Мұғалімге әдемі нәтиже жіберу ---
    result_text = format_ai_result(ai_result)
    await msg.reply_text(result_text)