import asyncio
import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot import config
from bot.db.database import init_db, AsyncSessionLocal
from bot.handlers import teacher, admin, bm, submissions
from bot.db.models import User
import sys
from telegram.ext import CommandHandler
from bot.services.scheduler import start_background_scheduler


def ensure_download_dir():
    d = config.DOWNLOADS_DIR
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def main():
    if not config.BOT_TOKEN:
        print("BOT_TOKEN not set. Set environment variable BOT_TOKEN.")
        return

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # /start — route by role
    logger = logging.getLogger(__name__)

    async def main_start(update, context):
        try:
            uid = update.effective_user.id
        except Exception:
            # fallback if no effective_user
            uid = None
        logger.info('Received /start from uid=%s', uid)

        try:
            from bot.db.database import locked_session
            from sqlalchemy import select

            # ensure uid is an int when possible
            try:
                uid = int(uid) if uid is not None else None
            except Exception:
                logger.warning('Could not coerce uid to int: %s', uid)

            async with locked_session() as session:
                # prefer an explicit SELECT to avoid any PK/get edge-cases
                user = None
                for attempt in range(2):
                    try:
                        if uid is None:
                            user = None
                            break
                        res = await session.execute(select(User).where(User.id == uid))
                        user = res.scalar_one_or_none()
                        break
                    except Exception as e:
                        logger.warning('DB read error on select(User): %s; attempt %s', e, attempt)
                        await asyncio.sleep(0.05)
                else:
                    user = None
        except Exception as e:
            logger.exception('Failed to access DB in /start: %s', e)
            try:
                await update.message.reply_text('Внутренняя ошибка сервера. Попробуйте позже.')
            except Exception:
                pass
            return

        if not user:
            await update.message.reply_text("Вы не зарегистрированы. Обратитесь к администратору.")
            return
        if user.role == 'admin':
            await admin.start(update, context)
            return
        if user.role == 'bm':
            await bm.start(update, context)
            return
        if user.role == 'teacher':
            await teacher.start(update, context)
            return
        await update.message.reply_text("Вы не зарегистрированы. Обратитесь к администратору.")

    # Command handlers
    app.add_handler(CommandHandler('start', main_start))
    
    # quick debug: show your Telegram id
    async def whoami(update, context):
        try:
            uid = update.effective_user.id
            name = update.effective_user.full_name
            await update.message.reply_text(f"Ваш Telegram id: {uid}\nИмя: {name}")
        except Exception:
            await update.message.reply_text('Не удалось получить информацию о пользователе')
    app.add_handler(CommandHandler('whoami', whoami))
    app.add_handler(CommandHandler('admin', admin.start))
    app.add_handler(CommandHandler('bm', bm.start))
    # admin CRUD commands
    app.add_handler(CommandHandler('add_bm', admin.add_bm))
    app.add_handler(CommandHandler('add_teacher', admin.add_teacher))
    app.add_handler(CommandHandler('add_subject', admin.add_subject))
    app.add_handler(CommandHandler('list_users', admin.list_users))
    app.add_handler(CommandHandler('list_subjects', admin.list_subjects))
    app.add_handler(CommandHandler('del_user', admin.del_user))
    # submissions viewer for admin / BM
    app.add_handler(submissions.get_handler())
    # BM: newplan conversation
    app.add_handler(bm.build_newplan_handler())
    app.add_handler(bm.build_bm_menu_handler())

    # Document handler for teacher uploads
    app.add_handler(MessageHandler(filters.Document.ALL, teacher.handle_document))
    # Teacher callback handlers (subject / plan selection)
    app.add_handler(CallbackQueryHandler(teacher.subject_cb, pattern=r'^t_sub:'))
    app.add_handler(CallbackQueryHandler(teacher.plan_cb, pattern=r'^t_plan:'))

    # Register a post-init callback to run DB initialization and scheduler inside
    # the application's event loop. Avoid calling `asyncio.run(init_db())` here
    # because that would create asyncpg connections bound to a different loop
    # and lead to "attached to a different loop" errors later.
    def _on_post_init(a):
        a.create_task(init_db())
        # ensure download dir exists in the app loop
        ensure_download_dir()
        # start background scheduler (it will schedule itself safely)
        start_background_scheduler(a)

    try:
        app.post_init(_on_post_init)
    except Exception:
        # best-effort: if post_init isn't available, fall back to creating the
        # task at module-import time (less ideal)
        try:
            app.create_task(init_db())
        except Exception:
            pass

    # Ensure there's an event loop for the application to use (fixes environments
    # where asyncio.get_event_loop() raises because no loop is set).
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Run polling (blocking)
    print("Bot started. Press Ctrl-C to stop.")
    app.run_polling()


if __name__ == '__main__':
    # python-telegram-bot v20 has limited support for Python versions newer than 3.12.
    if sys.version_info >= (3, 13):
        print("ERROR: Detected Python %s.%s. python-telegram-bot v20+ is not fully compatible with Python 3.13+.\n"
              "Please use Python 3.11 or 3.12 (create a venv with that interpreter) and retry.")
        sys.exit(1)
    main()
