from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from bot.db.database import AsyncSessionLocal
from bot.db.models import Subject, User, WeeklyPlan, TeacherSubject, SlideSubmission
from datetime import datetime
from sqlalchemy import select
from bot.utils.auth import check_role

# ConversationHandler күйлері
SUBJECT, TEACHER, WEEK_LABEL, LESSON_DATE, TOPIC, DEADLINE, CONFIRM = range(7)


# ─────────────────────────────────────────
# /start  →  БМ Басты мәзірі
# ─────────────────────────────────────────
@check_role(['bm'])
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Жаңа апталық жоспар", callback_data="bm_newplan")],
        [InlineKeyboardButton("👨‍🏫 Менің мұғалімдерім", callback_data="bm_teachers")],
        [InlineKeyboardButton("📚 Менің пәндерім", callback_data="bm_subjects")],
        [InlineKeyboardButton("📋 Тапсырмалар тізімі", callback_data="bm_plans")],
        [InlineKeyboardButton("📤 Жүктелген слайдтар", callback_data="bm_submissions")],
    ]
    await update.message.reply_text(
        "👋 БМ мәзірі. Не жасаймыз?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─────────────────────────────────────────
# Callback router
# ─────────────────────────────────────────
async def bm_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "bm_teachers":
        await show_teachers(query, context)
    elif data == "bm_subjects":
        await show_subjects(query, context)
    elif data == "bm_plans":
        await show_plans(query, context)
    elif data == "bm_submissions":
        await show_submissions(query, context)
    elif data == "bm_menu":
        await back_to_menu(query, context)
    elif data.startswith("bm_edit_teacher:"):
        await edit_teacher_menu(query, context)
    elif data.startswith("bm_edit_plan:"):
        await edit_plan_menu(query, context)
    elif data.startswith("bm_del_plan:"):
        await delete_plan(query, context)


# ─────────────────────────────────────────
# Басты мәзірге оралу
# ─────────────────────────────────────────
async def back_to_menu(query, context):
    keyboard = [
        [InlineKeyboardButton("📅 Жаңа апталық жоспар", callback_data="bm_newplan")],
        [InlineKeyboardButton("👨‍🏫 Менің мұғалімдерім", callback_data="bm_teachers")],
        [InlineKeyboardButton("📚 Менің пәндерім", callback_data="bm_subjects")],
        [InlineKeyboardButton("📋 Тапсырмалар тізімі", callback_data="bm_plans")],
        [InlineKeyboardButton("📤 Жүктелген слайдтар", callback_data="bm_submissions")],
    ]
    await query.edit_message_text(
        "👋 БМ мәзірі. Не жасаймыз?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─────────────────────────────────────────
# 👨‍🏫 Мұғалімдер тізімі
# ─────────────────────────────────────────
async def show_teachers(query, context):
    user_id = query.from_user.id
    async with AsyncSessionLocal() as session:
        # БМ-ге тиісті пәндерді таб
        res = await session.execute(select(Subject).where(Subject.bm_id == user_id))
        subjects = res.scalars().all()
        subj_ids = [s.id for s in subjects]

        if not subj_ids:
            await query.edit_message_text("📭 Сізге тиіс пәндер жоқ.")
            return

        # Сол пәндердегі мұғалімдерді таб
        res2 = await session.execute(
            select(TeacherSubject).where(TeacherSubject.subject_id.in_(subj_ids))
        )
        mappings = res2.scalars().all()
        teacher_ids = list({m.teacher_id for m in mappings})

        if not teacher_ids:
            await query.edit_message_text("📭 Мұғалімдер тіркелмеген.")
            return

        res3 = await session.execute(select(User).where(User.id.in_(teacher_ids)))
        teachers = res3.scalars().all()

        # Әр мұғалімнің пәндерін жина
        subj_map = {s.id: s.name for s in subjects}
        teacher_subj = {}
        for m in mappings:
            teacher_subj.setdefault(m.teacher_id, []).append(subj_map.get(m.subject_id, "?"))

    lines = ["👨‍🏫 *Менің мұғалімдерім:*\n"]
    keyboard = []
    for t in teachers:
        subj_names = ", ".join(teacher_subj.get(t.id, []))
        lines.append(f"• {t.full_name} — {subj_names}\n  `ID: {t.id}`")
        keyboard.append([InlineKeyboardButton(
            f"✏️ {t.full_name}", callback_data=f"bm_edit_teacher:{t.id}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Артқа", callback_data="bm_menu")])
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# 📚 Пәндер тізімі
# ─────────────────────────────────────────
async def show_subjects(query, context):
    user_id = query.from_user.id
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Subject).where(Subject.bm_id == user_id))
        subjects = res.scalars().all()

    if not subjects:
        keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="bm_menu")]]
        await query.edit_message_text(
            "📭 Сізге тиіс пәндер жоқ.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    lines = ["📚 *Менің пәндерім:*\n"]
    for s in subjects:
        lines.append(f"• {s.name} (ID: {s.id})")

    keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="bm_menu")]]
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# 📋 Тапсырмалар (WeeklyPlan) тізімі
# ─────────────────────────────────────────
async def show_plans(query, context):
    user_id = query.from_user.id
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Subject).where(Subject.bm_id == user_id))
        subjects = res.scalars().all()
        subj_ids = [s.id for s in subjects]
        subj_map = {s.id: s.name for s in subjects}

        if not subj_ids:
            await query.edit_message_text("📭 Пәндер жоқ.")
            return

        res2 = await session.execute(
            select(WeeklyPlan).where(WeeklyPlan.subject_id.in_(subj_ids))
            .order_by(WeeklyPlan.deadline.desc())
        )
        plans = res2.scalars().all()

        # Мұғалім аттарын жина
        teacher_ids = list({p.teacher_id for p in plans})
        teacher_map = {}
        if teacher_ids:
            res3 = await session.execute(select(User).where(User.id.in_(teacher_ids)))
            for t in res3.scalars().all():
                teacher_map[t.id] = t.full_name

        # Слайд статустарын жина
        plan_ids = [p.id for p in plans]
        sub_map = {}
        if plan_ids:
            res4 = await session.execute(
                select(SlideSubmission).where(SlideSubmission.plan_id.in_(plan_ids))
            )
            for s in res4.scalars().all():
                # Соңғысын сақта
                if s.plan_id not in sub_map or s.uploaded_at > sub_map[s.plan_id].uploaded_at:
                    sub_map[s.plan_id] = s

    if not plans:
        keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="bm_menu")]]
        await query.edit_message_text(
            "📭 Жоспарлар жоқ.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    STATUS_EMOJI = {
        "passed": "✅",
        "failed": "❌",
        "pending": "⏳",
        "error": "⚠️",
        None: "📭",
    }

    keyboard = []
    lines = ["📋 *Тапсырмалар тізімі:*\n"]
    for p in plans[:20]:  # макс 20
        sub = sub_map.get(p.id)
        st = sub.ai_check_status if sub else None
        emoji = STATUS_EMOJI.get(st, "📭")
        t_name = teacher_map.get(p.teacher_id, str(p.teacher_id))
        subj_name = subj_map.get(p.subject_id, "?")
        deadline_str = p.deadline.strftime("%d.%m %H:%M")
        lines.append(f"{emoji} {p.week_label} | {subj_name} | {t_name} | {p.topic[:20]} | {deadline_str}")
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {p.week_label} — {p.topic[:25]}",
            callback_data=f"bm_edit_plan:{p.id}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Артқа", callback_data="bm_menu")])
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# 📤 Жүктелген слайдтар
# ─────────────────────────────────────────
async def show_submissions(query, context):
    user_id = query.from_user.id
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Subject).where(Subject.bm_id == user_id))
        subjects = res.scalars().all()
        subj_ids = [s.id for s in subjects]

        if not subj_ids:
            await query.edit_message_text("📭 Пәндер жоқ.")
            return

        res2 = await session.execute(
            select(WeeklyPlan.id).where(WeeklyPlan.subject_id.in_(subj_ids))
        )
        plan_ids = [r[0] for r in res2.fetchall()]

        if not plan_ids:
            keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="bm_menu")]]
            await query.edit_message_text(
                "📭 Жоспарлар жоқ.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        res3 = await session.execute(
            select(SlideSubmission)
            .where(SlideSubmission.plan_id.in_(plan_ids))
            .order_by(SlideSubmission.uploaded_at.desc())
            .limit(20)
        )
        subs = res3.scalars().all()

        teacher_ids = list({s.teacher_id for s in subs})
        teacher_map = {}
        if teacher_ids:
            res4 = await session.execute(select(User).where(User.id.in_(teacher_ids)))
            for t in res4.scalars().all():
                teacher_map[t.id] = t.full_name

    if not subs:
        keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="bm_menu")]]
        await query.edit_message_text(
            "📭 Жүктелген слайдтар жоқ.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    STATUS_EMOJI = {"passed": "✅", "failed": "❌", "pending": "⏳", "error": "⚠️"}
    lines = ["📤 *Жүктелген слайдтар (соңғы 20):*\n"]
    for s in subs:
        emoji = STATUS_EMOJI.get(s.ai_check_status, "❓")
        t_name = teacher_map.get(s.teacher_id, str(s.teacher_id))
        date_str = s.uploaded_at.strftime("%d.%m %H:%M") if s.uploaded_at else "?"
        lines.append(f"{emoji} {t_name} | {s.file_name or 'файл'} | {date_str}")

    keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="bm_menu")]]
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# ✏️ Мұғалімді өңдеу мәзірі
# ─────────────────────────────────────────
async def edit_teacher_menu(query, context):
    teacher_id = int(query.data.split(":", 1)[1])
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == teacher_id))
        t = res.scalar_one_or_none()
    if not t:
        await query.edit_message_text("Мұғалім табылмады.")
        return

    keyboard = [
        [InlineKeyboardButton("🔙 Артқа", callback_data="bm_teachers")],
    ]
    await query.edit_message_text(
        f"👨‍🏫 *{t.full_name}*\nTelegram ID: `{t.id}`\n\n"
        f"Мұғалімді өңдеу немесе өшіру үшін /admin командасы арқылы әкімшіге хабарласыңыз.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# ✏️ Жоспарды өңдеу / өшіру мәзірі
# ─────────────────────────────────────────
async def edit_plan_menu(query, context):
    plan_id = int(query.data.split(":", 1)[1])
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(WeeklyPlan).where(WeeklyPlan.id == plan_id))
        p = res.scalar_one_or_none()
    if not p:
        await query.edit_message_text("Жоспар табылмады.")
        return

    keyboard = [
        [InlineKeyboardButton("🗑 Жоспарды өшіру", callback_data=f"bm_del_plan:{plan_id}")],
        [InlineKeyboardButton("🔙 Артқа", callback_data="bm_plans")],
    ]
    await query.edit_message_text(
        f"📋 *Жоспар #{plan_id}*\n"
        f"Апта: {p.week_label}\n"
        f"Тақырып: {p.topic}\n"
        f"Күні: {p.lesson_date}\n"
        f"Дедлайн: {p.deadline.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def delete_plan(query, context):
    plan_id = int(query.data.split(":", 1)[1])
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(WeeklyPlan).where(WeeklyPlan.id == plan_id))
        p = res.scalar_one_or_none()
        if not p:
            await query.edit_message_text("Жоспар табылмады.")
            return
        await session.delete(p)
        await session.commit()

    keyboard = [[InlineKeyboardButton("🔙 Тізімге оралу", callback_data="bm_plans")]]
    await query.edit_message_text(
        f"🗑 Жоспар #{plan_id} өшірілді.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─────────────────────────────────────────
# 📅 Жаңа жоспар — ConversationHandler
# ─────────────────────────────────────────
@check_role(['bm'])
async def newplan_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Subject).where(Subject.bm_id == user_id))
        subjects = res.scalars().all()
    if not subjects:
        await update.message.reply_text("Сізге тиіс пәндер жоқ.")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(s.name, callback_data=f"select_subject:{s.id}")] for s in subjects
    ]
    await update.message.reply_text("Пәнді таңдаңыз:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SUBJECT


async def newplan_subject_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sid = int(query.data.split(':', 1)[1])
    context.user_data['subject_id'] = sid
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(TeacherSubject).where(TeacherSubject.subject_id == sid))
        mappings = res.scalars().all()
        teacher_ids = [m.teacher_id for m in mappings]
        if not teacher_ids:
            await query.edit_message_text("Бұл пәнге мұғалім тіркелмеген.")
            return ConversationHandler.END
        res2 = await session.execute(select(User).where(User.id.in_(teacher_ids)))
        teachers = res2.scalars().all()
    keyboard = [[InlineKeyboardButton(t.full_name, callback_data=f"select_teacher:{t.id}")] for t in teachers]
    await query.edit_message_text("Мұғалімді таңдаңыз:", reply_markup=InlineKeyboardMarkup(keyboard))
    return TEACHER


async def newplan_teacher_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = int(query.data.split(':', 1)[1])
    context.user_data['teacher_id'] = tid
    await query.edit_message_text("Апта нөмірін енгізіңіз (мысалы: 4-апта):")
    return WEEK_LABEL


async def newplan_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['week_label'] = update.message.text.strip()
    await update.message.reply_text("ПС күнін енгізіңіз (YYYY-MM-DD форматында):")
    return LESSON_DATE


async def newplan_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    try:
        d = datetime.strptime(txt, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text("Қате формат. YYYY-MM-DD форматын пайдаланыңыз:")
        return LESSON_DATE
    context.user_data['lesson_date'] = d
    await update.message.reply_text("Сабақ тақырыбын енгізіңіз:")
    return TOPIC


async def newplan_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['topic'] = update.message.text.strip()
    await update.message.reply_text("Слайд жүктеу дедлайнын енгізіңіз (YYYY-MM-DD HH:MM):")
    return DEADLINE


async def newplan_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    try:
        dt = datetime.strptime(txt, "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Қате формат. YYYY-MM-DD HH:MM форматын пайдаланыңыз:")
        return DEADLINE
    context.user_data['deadline'] = dt
    data = context.user_data
    summary = (
        f"✅ Растаңыз:\n"
        f"Пән ID: {data['subject_id']}\n"
        f"Мұғалім ID: {data['teacher_id']}\n"
        f"Апта: {data['week_label']}\n"
        f"ПС күні: {data['lesson_date']}\n"
        f"Тақырып: {data['topic']}\n"
        f"Дедлайн: {data['deadline']}\n\n"
        f"/confirm немесе /cancel"
    )
    await update.message.reply_text(summary)
    return CONFIRM


async def newplan_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    async with AsyncSessionLocal() as session:
        plan = WeeklyPlan(
            subject_id=data['subject_id'],
            teacher_id=data['teacher_id'],
            week_label=data['week_label'],
            lesson_date=data['lesson_date'],
            topic=data['topic'],
            deadline=data['deadline'],
            created_by=update.effective_user.id,
        )
        session.add(plan)
        await session.commit()
    await update.message.reply_text("✅ Апталық жоспар сақталды!")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Операция тоқтатылды.")
    return ConversationHandler.END


# ─────────────────────────────────────────
# bm_newplan callback — conversation-ға кіру
# ─────────────────────────────────────────
async def bm_newplan_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline кнопка арқылы жаңа жоспар ConversationHandler-ге кіру."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Subject).where(Subject.bm_id == user_id))
        subjects = res.scalars().all()
    if not subjects:
        await query.edit_message_text("Сізге тиіс пәндер жоқ.")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(s.name, callback_data=f"select_subject:{s.id}")] for s in subjects
    ]
    await query.edit_message_text("Пәнді таңдаңыз:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SUBJECT


def build_newplan_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler('newplan', newplan_start),
            CallbackQueryHandler(bm_newplan_entry, pattern=r'^bm_newplan$'),
        ],
        states={
            SUBJECT:     [CallbackQueryHandler(newplan_subject_cb, pattern=r'^select_subject:')],
            TEACHER:     [CallbackQueryHandler(newplan_teacher_cb, pattern=r'^select_teacher:')],
            WEEK_LABEL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, newplan_week)],
            LESSON_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, newplan_date)],
            TOPIC:       [MessageHandler(filters.TEXT & ~filters.COMMAND, newplan_topic)],
            DEADLINE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, newplan_deadline)],
            CONFIRM:     [
                CommandHandler('confirm', newplan_confirm),
                CommandHandler('cancel', cancel)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )


def build_bm_menu_handler():
    """БМ мәзірінің барлық callback-тарын өңдейді."""
    return CallbackQueryHandler(
        bm_menu_cb,
        pattern=r'^(bm_teachers|bm_subjects|bm_plans|bm_submissions|bm_menu|bm_edit_teacher:\d+|bm_edit_plan:\d+|bm_del_plan:\d+)$'
    )