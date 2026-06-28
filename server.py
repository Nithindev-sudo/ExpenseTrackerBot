import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from db import ExpenseDB

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


def load_config() -> dict:
    with CONFIG_FILE.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    return {
        "currency": config.get("currency", "₹"),
        "monthlyBudget": config.get("monthlyBudget", 0),
        "budgets": config.get("budgets", {}),
    }


@app.route("/api/expenses")
def api_expenses():
    chat_id = request.args.get("chat_id")
    db = ExpenseDB()
    rows = db.all_rows()
    if chat_id is not None:
        rows = [row for row in rows if str(row["chat_id"]) == str(chat_id)]
    payload = [
        {
            "id": row["id"],
            "date": row["date"],
            "category": row["category"],
            "amount": float(row["amount"]),
            "note": row["note"],
            "type": row["type"],
            "chat_id": row["chat_id"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return jsonify(payload)


@app.route("/api/config")
def api_config():
    return jsonify(load_config())


@app.route("/dashboard")
def dashboard():
    return send_from_directory(str(BASE_DIR), "dashboard.html")


@app.route("/")
def index():
    return dashboard()


@app.route("/<path:path>")
def static_files(path: str):
    return send_from_directory(str(BASE_DIR), path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
