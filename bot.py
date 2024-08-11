import os
import logging
import sqlite3
import time
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import schedule

# Configure logging
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the bot
TOKEN = os.getenv('6639976850:AAGFEmV6O4jqJ7uIhwHDCj33W0Me2X2OZV0')
GROUP_CHAT_ID = os.getenv('-1002249122120')
application = Application.builder().token(TOKEN).build()
bot = Bot(token=TOKEN)

# Connect to SQLite database
db_path = os.getenv('DATABASE_PATH', 'visa_data.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

# Create tables if not exist
cursor.execute('''CREATE TABLE IF NOT EXISTS visa_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    status TEXT,
    consulate TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    question TEXT,
    consulate TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)''')

# Command Handlers
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Use /help to see available commands.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/report - Show latest monthly report\n"
        "/ask [question] - Log a question\n"
        "/stats - Show daily analysis\n"
        "/history [month/year] - Show past reports"
    )

async def ask_question(update: Update, context: CallbackContext):
    question = ' '.join(context.args)
    user_id = update.message.from_user.id
    
    if not question:
        await update.message.reply_text("Please provide a question.")
        return

    consulate = 'Unknown'
    for keyword in ['Mumbai', 'Hyderabad', 'Chennai', 'Delhi', 'Kolkata']:
        if keyword.lower() in question.lower():
            consulate = keyword
            break

    # Check if the question was already logged this month
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute('SELECT COUNT(*) FROM questions WHERE user_id = ? AND strftime("%Y-%m", timestamp) = ?', (user_id, current_month))
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO questions (user_id, question, consulate) VALUES (?, ?, ?)', (user_id, question, consulate))
        conn.commit()
        await update.message.reply_text("Question logged.")
    else:
        await update.message.reply_text("You have already asked a question this month.")

async def report(update: Update, context: CallbackContext):
    current_month = datetime.now().strftime('%Y-%m')
    message = f"Monthly Report for {current_month}:\n\n"
    
    for consulate in ['Mumbai', 'Hyderabad', 'Chennai', 'Delhi', 'Kolkata']:
        cursor.execute('SELECT COUNT(*) FROM visa_data WHERE consulate = ? AND strftime("%Y-%m", timestamp) = ?', (consulate, current_month))
        approved = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM visa_data WHERE consulate = ? AND status = "Rejected" AND strftime("%Y-%m", timestamp) = ?', (consulate, current_month))
        rejected = cursor.fetchone()[0]
        message += f"{consulate} - Approved: {approved}, Rejected: {rejected}\n"
    
    message += "\nQuestions Asked This Month:\n"
    for consulate in ['Mumbai', 'Hyderabad', 'Chennai', 'Delhi', 'Kolkata']:
        message += f"\n{consulate} Consulate Questions:\n"
        cursor.execute('SELECT question FROM questions WHERE consulate = ? AND strftime("%Y-%m", timestamp) = ?', (consulate, current_month))
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                message += f"- {row[0]}\n"
        else:
            message += "No questions asked this month.\n"
    
    await update.message.reply_text(message)

async def stats(update: Update, context: CallbackContext):
    await update.message.reply_text("This feature is under development.")

async def history(update: Update, context: CallbackContext):
    await update.message.reply_text("This feature is under development.")

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    status = 'Unknown'
    consulate = 'Unknown'
    user_id = update.message.from_user.id
    
    # Determine visa status
    if 'approved' in text:
        status = 'Approved'
    elif 'rejected' in text:
        status = 'Rejected'
    
    # Determine consulate
    for keyword in ['mumbai', 'hyderabad', 'chennai', 'delhi', 'kolkata']:
        if keyword in text:
            consulate = keyword.capitalize()
            break

    # Check if both status and consulate were identified
    if status != 'Unknown' and consulate != 'Unknown':
        # Check if the message was already analyzed this month
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('SELECT COUNT(*) FROM visa_data WHERE user_id = ? AND strftime("%Y-%m", timestamp) = ?', (user_id, current_month))
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO visa_data (user_id, status, consulate) VALUES (?, ?, ?)', (user_id, status, consulate))
            conn.commit()

async def daily_summary():
    try:
        message = "Daily Visa Analysis:\n\n"
        
        cursor.execute('SELECT consulate, status, COUNT(*) FROM visa_data WHERE DATE(timestamp) = DATE("now") GROUP BY consulate, status')
        rows = cursor.fetchall()
        
        for row in rows:
            consulate, status, count = row
            message += f"{consulate} - {status}: {count}\n"
        
        await bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"Error in daily_summary: {e}")

async def daily_question_summary():
    try:
        message = "Daily Question Summary:\n\n"
        
        for consulate in ['Mumbai', 'Hyderabad', 'Chennai', 'Delhi', 'Kolkata']:
            message += f"Questions for {consulate} consulate:\n"
            cursor.execute('SELECT question FROM questions WHERE consulate = ? AND DATE(timestamp) = DATE("now")', (consulate,))
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    message += f"- {row[0]}\n"
            else:
                message += "No questions asked today.\n"
        
        await bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"Error in daily_question_summary: {e}")

# Set up command handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('help', help_command))
application.add_handler(CommandHandler('ask', ask_question))
application.add_handler(CommandHandler('report', report))
application.add_handler(CommandHandler('stats', stats))
application.add_handler(CommandHandler('history', history))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Schedule daily summaries
schedule.every().day.at("13:00").do(lambda: asyncio.run(daily_summary()))  # 1:00 PM UTC
schedule.every().day.at("13:30").do(lambda: asyncio.run(daily_question_summary()))  # 1:30 PM UTC

# Start the bot
async def run_bot():
    await application.start()
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

if __name__ == '__main__':
    import asyncio
    asyncio.run(run_bot())
