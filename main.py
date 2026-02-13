from schedule import SCA
import os
import pytz
import datetime as dt
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ConversationHandler, MessageHandler, CommandHandler, filters, ContextTypes

tz = pytz.timezone('Europe/Kyiv')

def lessonname(i, schoolclass, day):
	SC=SCA.get(schoolclass)
	wday=SC.get(day)
	lesson=wday[i-1]
	return(lesson)
	

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

STEP_1, STEP_2, STEP_3, STEP_4 = range(4)
async def SendMessage(update: Update, text: str, markdown=False):
	if markdown:
		await update.message.reply_text(text, parse_mode="MarkdownV2")
	else:
		await update.message.reply_text(text)
	user = update.effective_user
	logging.info(f"bot in chat with User {user.first_name} (ID: {user.id}) wrote: '{text}'")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
	context.user_data['day']=False
	await SendMessage(update, "введи свой класс: ")
	return STEP_1 
async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
	context.user_data['day']=True
	await SendMessage(update, "введи свой класс: ")
	return STEP_1 
	
async def SchoolClass(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if not update.message.text.isdigit():
		await SendMessage(update, "неверный тип данных, попробуйте ещё раз.")
		return STEP_1
	elif int(update.message.text)>9:
		await SendMessage(update, "нету класса выше 9го, попробуйте ещё раз.")
		return STEP_1
	#пока что все классы заптолнены но может понадобится потом оставлю пока False
	elif False: 
		await SendMessage(update, "WIP, try 0 Class.") 
		return STEP_1
	else:
		context.user_data['SchoolClass']=int(update.message.text)
		if int(update.message.text)!=0:
			SC=SCA.get(int(update.message.text))
			day = (dt.datetime.now(tz).weekday() + (1 if context.user_data['day'] else 0)) % 7
			if day in [5,6]:
				day=0
			wday=SC.get(day)
			context.user_data['Lessons']=len(wday)
			await SendMessage(update, "введи насколько скороченный урок: ")
			return STEP_3
		else:
			await SendMessage(update, "введи количество уроков: ")
			return STEP_2

async def LessonsCount(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if not update.message.text.isdigit():
		await SendMessage(update, "неверный тип данных, попробуйте ещё раз.")
		return STEP_2
	elif int(update.message.text)==0:
		await SendMessage(update, "извините, но нельзя выбрать 0 уроков, попробуйте ещё раз.")
		return STEP_2
	else:
		context.user_data['Lessons']=int(update.message.text)
		await SendMessage(update, "введи насколько скороченный урок: ")
		return STEP_3

async def LessonsTime(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if not update.message.text.isdigit():
		await SendMessage(update, "неверный тип данных, попробуйте ещё раз.")
		return STEP_3
	else:
		context.user_data['LessonTime']=int(update.message.text)
		await SendMessage(update, "введи насколько скороченная перемена: ")
		return STEP_4

async def MainCalculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if not update.message.text.isdigit():
		await SendMessage(update, "неверный тип данных, попробуйте ещё раз.")
		return STEP_4
	UnlessonTime = 10 - int(update.message.text)
	Lessons = range(1, context.user_data['Lessons'] + 1)
	LessonTime = 45 - context.user_data['LessonTime']
	Time = 8 * 60 + 45
	day = (dt.datetime.now(tz).weekday() + (1 if context.user_data['day'] else 0)) % 7
	Message = ("\n ```Уроки \n")
	if day in [5,6]:
		day=0
		Message+=("на понедельник:\n")
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
			
		if context.user_data['SchoolClass']==0:
			lessoname=""
		else:
			lessoname=")"+lessonname(Lesson, context.user_data['SchoolClass'], day)
			
		Message += (f"{Lesson}{lessoname} — S: {StartTime1}:{StartTime2} / E: {EndTime1}:{EndTime2}\n")

		if isinstance(StartTime2, str):
			StartTime2 = StartTime2Save
		if isinstance(EndTime2, str):
			EndTime2 = EndTime2Save

	Message+=(f"```\n")
	await SendMessage(update, Message, True)
	return ConversationHandler.END

if __name__ == '__main__':

	TOKEN = os.getenv("TOKEN")
	print("TOKEN=",TOKEN)
	app = ApplicationBuilder().token(TOKEN).build()

	conv_handler = ConversationHandler(
		entry_points=[
		CommandHandler('today', today),
		CommandHandler('tomorrow', tomorrow)
		],
		states={
			STEP_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, SchoolClass)],						STEP_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, LessonsCount)],
			STEP_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, LessonsTime)],
			STEP_4: [MessageHandler(filters.TEXT & ~filters.COMMAND, MainCalculate)]
		},
		fallbacks=[],
	)

app.add_handler(MessageHandler(filters.TEXT, log_message), group=-1)
app.add_handler(conv_handler)
print("Бот запущен...")
app.run_polling()