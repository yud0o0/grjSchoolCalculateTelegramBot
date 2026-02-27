import os
import sys
import pytz
import logging
import asyncio
import datetime as dt
from aiohttp import web 
from schedule import SCA
from telegram import Update
from telegram.ext import ApplicationBuilder, ConversationHandler, MessageHandler, CommandHandler, filters, ContextTypes

tz = pytz.timezone('Europe/Kyiv')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logging.getLogger("httpx").setLevel(logging.WARNING)

def get_lesson_name(i, school_class, day):
    sc_data = SCA.get(school_class)
    wday = sc_data.get(day)
    return wday[i-1]

async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user = update.effective_user
    text = update.message.text
    logging.info(f"User {user.first_name} (ID: {user.id}) wrote: {text}")

async def SendMessage(update: Update, text: str, markdown=False):
    parse_mode = "MarkdownV2" if markdown else None
    await update.message.reply_text(text, parse_mode=parse_mode)
    
    user = update.effective_user
    chat = update.effective_chat
    chat_info = f"{chat.type} '{chat.title}'" if chat.title else chat.type
    logging.info(f"Bot to {chat_info} (User: {user.first_name}): '{text}'")

STEP_1, STEP_2, STEP_3, STEP_4 = range(4)

async def start_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, is_tomorrow: bool, is_custom: bool):
    context.user_data['day'] = is_tomorrow
    context.user_data['custom'] = is_custom
    chat = update.effective_chat
    
    if chat.type in ["group", "supergroup"] and chat.title and chat.title[0].isdigit():
        school_class = int(chat.title[0])
        context.user_data['SchoolClass'] = school_class
        
        await SendMessage(update, f"Класс {school_class} определен по названию группы.")
        
        sc_data = SCA.get(school_class)
        day = (dt.datetime.now(tz).weekday() + (1 if is_tomorrow else 0)) % 7
        if day in [5, 6]: day = 0
        
        wday = sc_data.get(day)
        context.user_data['Lessons'] = len(wday)
        await SendMessage(update, "Количество уроков подтянуто.")

        if is_custom:
            await SendMessage(update, "Введи насколько сокращен урок (мин):")
            return STEP_3
        else:
            return await MainCalculate(update, context)
            
    await SendMessage(update, "Введи свой класс:")
    return STEP_1

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_logic(update, context, is_tomorrow=False, is_custom=False)

async def ctoday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_logic(update, context, is_tomorrow=False, is_custom=True)

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_logic(update, context, is_tomorrow=True, is_custom=False)

async def ctomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_logic(update, context, is_tomorrow=True, is_custom=True)

async def SchoolClass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        await SendMessage(update, "Неверный формат. Введи число.")
        return STEP_1
    
    val = int(text)
    if val > 9:
        await SendMessage(update, "Нету класса выше 9-го. Попробуй еще раз.")
        return STEP_1
    
    context.user_data['SchoolClass'] = val
    if val != 0:
        sc_data = SCA.get(val)
        day = (dt.datetime.now(tz).weekday() + (1 if context.user_data.get('day') else 0)) % 7
        if day in [5, 6]: day = 0
        
        wday = sc_data.get(day)
        context.user_data['Lessons'] = len(wday)
        await SendMessage(update, "Количество уроков подтянуто из расписания.")
        if context.user_data['custom']:
            await SendMessage(update, "Введи насколько сокращен урок (мин):")
            return STEP_3
        else:
            return await MainCalculate(update, context)
    else:
        await SendMessage(update, "Введи количество уроков:")
        return STEP_2

async def LessonsCount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit() or int(update.message.text) == 0:
        await SendMessage(update, "Введи корректное количество уроков.")
        return STEP_2
    context.user_data['Lessons'] = int(update.message.text)
    if context.user_data['custom']:
        await SendMessage(update, "Введи насколько сокращен урок (мин):")
        return STEP_3
    else:
        return await MainCalculate(update, context)

async def LessonsTime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await SendMessage(update, "Введи число.")
        return STEP_3
    context.user_data['LessonTime'] = int(update.message.text)
    await SendMessage(update, "Введи насколько сокращена перемена (мин):")
    return STEP_4

async def MainCalculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_custom = context.user_data['custom']
    if is_custom and not update.message.text.isdigit():
        await SendMessage(update, "Введи число.")
        return STEP_4
    
    if is_custom:
        un_break = 10 - int(update.message.text)
        lesson_dur = 45 - context.user_data['LessonTime']
    else:
        un_break = 10
        lesson_dur = 45
    
    total_lessons = context.user_data['Lessons']
    current_time = 8 * 60 + 45 
    
    is_tomorrow = context.user_data.get('day', False)
    day = (dt.datetime.now(tz).weekday() + (1 if is_tomorrow else 0)) % 7
    if day in [5, 6]: day = 0
    
    msg = "```\nУроки " + ("на завтра" if is_tomorrow else "на сегодня") + ":\n"
    
    for i in range(1, total_lessons + 1):
        if i != 1:
            current_time += (un_break + 5) if i == 2 and is_custom or i == 4 else  un_break 
        
        start_ts = current_time
        current_time += lesson_dur
        end_ts = current_time
        
        s_h, s_m = divmod(start_ts, 60)
        e_h, e_m = divmod(end_ts, 60)
        
        l_name = ""
        if context.user_data['SchoolClass'] != 0:
            l_name = f") {get_lesson_name(i, context.user_data['SchoolClass'], day)}"
            
        msg += f"{i}{l_name} — {s_h:02}:{s_m:02} / {e_h:02}:{e_m:02}\n"

    msg += "```"
    await SendMessage(update, msg, True)
    return ConversationHandler.END

async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    token = os.getenv("TOKEN")
    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('today', today), CommandHandler('customtoday', ctoday), CommandHandler('tomorrow', tomorrow), CommandHandler('customtomorrow', ctomorrow)],
        states={
            STEP_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, SchoolClass)],
            STEP_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, LessonsCount)],
            STEP_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, LessonsTime)],
            STEP_4: [MessageHandler(filters.TEXT & ~filters.COMMAND, MainCalculate)]
        },
        fallbacks=[],
    )

    app.add_handler(MessageHandler(filters.TEXT, log_message), group=-1)
    app.add_handler(conv_handler)

    server = web.Application()
    server.router.add_get("/", handle)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass