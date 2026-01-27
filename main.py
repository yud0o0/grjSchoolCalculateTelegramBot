import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ConversationHandler, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logging.getLogger("telegram").setLevel(logging.INFO)

async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    logging.info(f"User {user.first_name} (ID: {user.id}) wrote: {text}")

STEP_1, STEP_2, STEP_3 = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("введи количество уроков: ")
    user = update.effective_user
    logging.info(f"bot in chat with User {user.first_name} (ID: {user.id}) wrote: 'введи количество уроков:' ")
    return STEP_1 

async def LessonsCount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['Lessons'] = range(1, (int(update.message.text) + 1))
    await update.message.reply_text("введи насколько скороченный урок: ")
    logging.info(f"bot in chat with User {user.first_name} (ID: {user.id}) wrote: 'введи насколько скороченный урок:' ")
    return STEP_2

async def LessonsTime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['LessonTime'] = 45 - int(update.message.text)
    await update.message.reply_text("введи насколько скороченная перемена: ")
    logging.info(f"bot in chat with User {user.first_name} (ID: {user.id}) wrote: 'введи насколько скороченная перемена:' ")
    return STEP_3
    
async def MainCalculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Lessons = context.user_data['Lessons']
    LessonTime = context.user_data['LessonTime']
    
    UnlessonTime = 10 - int(update.message.text)
    Time = 8 * 60 + 45
    Massage = ("\nуроки: \n")
    
    for Lesson in Lessons:
        if Lesson != 1:
            if Lesson == 3:
                Time += UnlessonTime + 5
            else:
                Time += UnlessonTime
        
        StartTime = Time
        Time += LessonTime
        EndTime = Time
        
        StartTime1 = int(StartTime / 60)
        StartTime2 = StartTime - StartTime1 * 60
        EndTime1 = int(EndTime / 60)
        EndTime2 = EndTime - EndTime1 * 60
        
        if StartTime2 < 10:
            StartTime2Save = StartTime2
            StartTime2 = "0" + str(StartTime2)
        if EndTime2 < 10:
            EndTime2Save = EndTime2
            EndTime2 = "0" + str(EndTime2)
            
        Massage += (f"{Lesson} — Start: {StartTime1}:{StartTime2} / End: {EndTime1}:{EndTime2}\n")
        
        if isinstance(StartTime2, str):
            StartTime2 = StartTime2Save
        if isinstance(EndTime2, str):
            EndTime2 = EndTime2Save
            
    await update.message.reply_text(Massage)
    logging.info(f"bot in chat with User {user.first_name} (ID: {user.id}) wrote: '{Massage}' ")
    return ConversationHandler.END

if __name__ == '__main__':
    
    token1 = "8394375068:AAHBpixyst2jEo9jh2NUbdIRW58fl7T0EVY"
    app = ApplicationBuilder().token(token1).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STEP_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, LessonsCount)],
            STEP_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, LessonsTime)],
            STEP_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, MainCalculate)]
        },
        fallbacks=[],
    )

app.add_handler(MessageHandler(filters.TEXT, log_message), group=-1)
app.add_handler(conv_handler)
print("Бот запущен...")
app.run_polling()