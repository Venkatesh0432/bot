from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import sqlite3
import schedule
import time
from datetime import datetime

# Initialize the bot
TOKEN = '6639976850:AAGFEmV6O4jqJ7uIhwHDCj33W0Me2X2OZV0
'
GROUP_CHAT_ID = '-1002249122120'
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
bot = Bot(token=TOKEN)

# Connect to SQLite database
conn = sqlite3.connect('visa_data.db', check_same_thread=False)
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
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome! Use /help to see available commands.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/report - Show latest monthly report\n"
        "/ask [question] - Log a question\n"
        "/stats - Show daily analysis\n"
        "/history [month/year] - Show past reports"
    )

def ask_question(update: Update, context: CallbackContext):
    question = ' '.join(context.args)
    user_id = update.message.from_user.id
    
    if not question:
        update.message.reply_text("Please provide a question.")
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
        update.message.reply_text("Question logged.")
    else:
        update.message.reply_text("You have already asked a question this month.")

def report(update: Update, context: CallbackContext):
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
    
    update.message.reply_text(message)

def stats(update: Update, context: CallbackContext):
    update.message.reply_text("This feature is under development.")

def history(update: Update, context: CallbackContext):
    update.message.reply_text("This feature is under development.")

def handle_message(update: Update, context: CallbackContext):
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

def daily_summary():
    now = datetime.now()
    message = "Daily Visa Analysis:\n\n"
    
    cursor.execute('SELECT consulate, status, COUNT(*) FROM visa_data WHERE DATE(timestamp) = DATE("now") GROUP BY consulate, status')
    rows = cursor.fetchall()
    
    for row in rows:
        consulate, status, count = row
        message += f"{consulate} - {status}: {count}\n"
    
    bot.send_message(chat_id=GROUP_CHAT_ID, text=message)

def daily_question_summary():
    now = datetime.now()
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
    
    bot.send_message(chat_id=GROUP_CHAT_ID, text=message)

# Set up command handlers
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help_command))
dispatcher.add_handler(CommandHandler('ask', ask_question))
dispatcher.add_handler(CommandHandler('report', report))
dispatcher.add_handler(CommandHandler('stats', stats))
dispatcher.add_handler(CommandHandler('history', history))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Schedule daily summaries
schedule.every().day.at("13:00").do(daily_summary)  # 6:30 PM IST is 13:00 UTC
schedule.every().day.at("13:00").do(daily_question_summary)  # 6:30 PM IST is 13:00 UTC

# Start the bot
def run_bot():
    updater.start_polling()
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    run_bot()





