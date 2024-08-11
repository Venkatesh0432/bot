import logging
import sqlite3
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Bot credentials
TOKEN = "6639976850:AAGFEmV6O4jqJ7uIhwHDCj33W0Me2X2OZV0"
GROUP_CHAT_ID = "-1002249122120"

# Initialize the bot
application = Application.builder().token(TOKEN).build()

# Connect to SQLite database
conn = sqlite3.connect('visa_data.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables if not exist
cursor.executescript('''
    CREATE TABLE IF NOT EXISTS visa_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        status TEXT,
        consulate TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question TEXT,
        consulate TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
''')
conn.commit()

async def start(update: Update, context):
    await update.message.reply_text("Welcome! Use /help to see available commands.")

async def help_command(update: Update, context):
    await update.message.reply_text(
        "/start - Start the bot\n/help - Show help\n/report - Show latest monthly report\n"
        "/ask [question] - Log a question\n/stats - Show daily analysis\n"
        "/history [month/year] - Show past reports"
    )

async def ask_question(update: Update, context):
    question = ' '.join(context.args)
    user_id = update.message.from_user.id
    
    if not question:
        await update.message.reply_text("Please provide a question.")
        return

    consulate = next((keyword for keyword in ['Mumbai', 'Hyderabad', 'Chennai', 'Delhi', 'Kolkata'] if keyword.lower() in question.lower()), 'Unknown')

    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute('SELECT COUNT(*) FROM questions WHERE user_id = ? AND strftime("%Y-%m", timestamp) = ?', (user_id, current_month))
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO questions (user_id, question, consulate) VALUES (?, ?, ?)', (user_id, question, consulate))
        conn.commit()
        await update.message.reply_text("Question logged.")
    else:
        await update.message.reply_text("You have already asked a question this month.")

async def report(update: Update, context):
    current_month = datetime.now().strftime('%Y-%m')
    message = f"Monthly Report for {current_month}:\n\n"
    
    for consulate in ['Mumbai', 'Hyderabad', 'Chennai', 'Delhi', 'Kolkata']:
        cursor.execute('SELECT status, COUNT(*) FROM visa_data WHERE consulate = ? AND strftime("%Y-%m", timestamp) = ? GROUP BY status', (consulate, current_month))
        results = dict(cursor.fetchall())
        approved = results.get('Approved', 0)
        rejected = results.get('Rejected', 0)
        message += f"{consulate} - Approved: {approved}, Rejected: {rejected}\n"
    
    message += "\nQuestions Asked This Month:\n"
    cursor.execute('SELECT consulate, question FROM questions WHERE strftime("%Y-%m", timestamp) = ? ORDER BY consulate', (current_month,))
    questions = cursor.fetchall()
    current_consulate = None
    for consulate, question in questions:
        if consulate != current_consulate:
            message += f"\n{consulate} Consulate Questions:\n"
            current_consulate = consulate
        message += f"- {question}\n"
    
    await update.message.reply_text(message)

async def stats(update: Update, context):
    await update.message.reply_text("This feature is under development.")

async def history(update: Update, context):
    await update.message.reply_text("This feature is under development.")

async def handle_message(update: Update, context):
    text = update.message.text.lower()
    status = 'Approved' if 'approved' in text else 'Rejected' if 'rejected' in text else 'Unknown'
    consulate = next((keyword.capitalize() for keyword in ['mumbai', 'hyderabad', 'chennai', 'delhi', 'kolkata'] if keyword in text), 'Unknown')
    user_id = update.message.from_user.id

    if status != 'Unknown' and consulate != 'Unknown':
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('SELECT COUNT(*) FROM visa_data WHERE user_id = ? AND strftime("%Y-%m", timestamp) = ?', (user_id, current_month))
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO visa_data (user_id, status, consulate) VALUES (?, ?, ?)', (user_id, status, consulate))
            conn.commit()

def main():
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('ask', ask_question))
    application.add_handler(CommandHandler('report', report))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('history', history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
