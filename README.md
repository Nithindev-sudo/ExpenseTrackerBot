# Expense Tracker

This project includes a Telegram bot and a dashboard backed by a database.

## Local setup

1. Create a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Copy the environment example:
   ```powershell
   copy .env.example .env
   ```
4. Fill `.env` with your `DATABASE_URL`, `TELEGRAM_TOKEN`, and `GROQ_API_KEY`.

## Run locally

- Run the web dashboard/API:
  ```powershell
  python server.py
  ```
- Run the bot:
  ```powershell
  python bot.py
  ```

## Railway deployment

1. Create a new Railway project.
2. Add a PostgreSQL plugin.
3. Set environment variables in Railway:
   - `DATABASE_URL`
   - `TELEGRAM_TOKEN`
   - `GROQ_API_KEY`
4. Use the following services:
   - Web service: `python server.py`
   - Worker service: `python bot.py`

## Notes

- `db.py` now reads `DATABASE_URL` and supports both SQLite and PostgreSQL.
- `dashboard.html` fetches `/api/expenses` and `/api/config`.
- `export.py` also uses `DATABASE_URL` if provided.
