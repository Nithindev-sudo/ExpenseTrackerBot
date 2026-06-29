import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from llm_parser import init_llm, extract_expense

from db import ExpenseDB
from export import export_data

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)


CONFIG_FILE = Path(__file__).resolve().parent / "config.json"
DB_FILE = os.getenv("DATABASE_URL", str(Path(__file__).resolve().parent / "expenses.db"))

load_dotenv(Path(__file__).resolve().parent / ".env")


def load_bot_config():

    with open(CONFIG_FILE,"r",encoding="utf-8") as f:
        config = json.load(f)
    config["telegram_token"] = os.getenv("TELEGRAM_TOKEN", config.get("telegram_token"))
    config["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", config.get("GROQ_API_KEY"))
    return config



def format_money(value,currency):

    return f"{currency}{int(value):,}"



def get_month_key():

    return datetime.now().strftime("%Y-%m")



async def start_command(update,context):

    await update.message.reply_text(
        "Expense tracker ready.\n\n"
        "Examples:\n"
        "muscle blaze whey 2500\n"
        "uber 300\n"
        "salary 80000"
    )




async def record_message(update:Update,
                         context:ContextTypes.DEFAULT_TYPE):


    text = update.message.text.strip()

    chat_id = update.effective_chat.id


    config = load_bot_config()

    currency=config.get("currency","₹")


    try:

        tx = extract_expense(text)


    except Exception as e:

        await update.message.reply_text(
            f"Could not understand expense: {e}"
        )

        return



    db=ExpenseDB(str(DB_FILE))


    db.add(
        amount=float(tx["amount"]),
        category=tx["category"].lower(),
        note=tx["item_name"],
        type_=tx["type"],
        chat_id=chat_id
    )


    export_data()

    formatted_amount = format_money(tx['amount'],currency)
    message_text = (
        f"Added ✅\n\n"
        f"Item: {tx['item_name']}\n"
        f"Amount: {formatted_amount}\n"
        f"Category: {tx['category']}"
    )
    print(f"[LOG] Sending to Telegram: {message_text!r}")
    print(f"[LOG] Currency: {currency!r}")
    print(f"[LOG] Formatted amount: {formatted_amount!r}")

    await update.message.reply_text(message_text)




async def total_command(update,context):


    config=load_bot_config()

    db=ExpenseDB(str(DB_FILE))


    total=db.month_total(get_month_key())


    await update.message.reply_text(

        f"This month spending: "
        f"{format_money(total,config.get('currency','₹'))}"

    )




async def delete_existing_webhook(application):
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        print("Deleted any existing webhook before polling.")
    except Exception as e:
        print(f"Warning: could not delete webhook before polling: {e}")


def main():


    config=load_bot_config()


    init_llm(
        config.get("GROQ_API_KEY")
    )


    print("Bot running...")
    print("Bot initialised and Debug mode is off.!!...")

    app=ApplicationBuilder().token(
        config["telegram_token"]
    ).post_init(delete_existing_webhook).build()


    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )


    app.add_handler(
        CommandHandler(
            "total",
            total_command
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            record_message
        )
    )


    app.run_polling()



if __name__=="__main__":

    main()
