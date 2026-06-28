import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # type: ignore
    psycopg = None
    dict_row = None

DB_FILE = os.getenv("DATABASE_URL", str(Path(__file__).resolve().parent / "expenses.db"))

SQLITE_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS txns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT,
    type TEXT NOT NULL,
    chat_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
)
"""

POSTGRES_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS txns (
    id SERIAL PRIMARY KEY,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT,
    type TEXT NOT NULL,
    chat_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
)
"""


def _month_bounds(month: Optional[str] = None) -> tuple[str, str]:
    if month is None:
        now = datetime.now()
        month = now.strftime("%Y-%m")
    year, mon = (int(part) for part in month.split("-"))
    if mon == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = mon + 1
    start = f"{year:04d}-{mon:02d}-01"
    end = f"{next_year:04d}-{next_month:02d}-01"
    return start, end


class ExpenseDB:
    def __init__(self, path: str = DB_FILE):
        self.path = path
        self.is_postgres = isinstance(path, str) and path.startswith(("postgres://", "postgresql://"))
        if self.is_postgres:
            if psycopg is None:
                raise ImportError("psycopg is required for PostgreSQL support")
            self.conn = psycopg.connect(self.path)
            self.conn.autocommit = True
            self.placeholder = "%s"
        else:
            self.conn = sqlite3.connect(self.path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.placeholder = "?"
        self._create_table()

    def _cursor(self):
        if self.is_postgres:
            return self.conn.cursor(row_factory=dict_row)
        return self.conn.cursor()

    def _create_table(self) -> None:
        if self.is_postgres:
            with self._cursor() as cursor:
                cursor.execute(POSTGRES_CREATE_TABLE)
        else:
            with self.conn:
                self.conn.executescript(SQLITE_CREATE_TABLE)

    def add(
        self,
        amount: float,
        category: str,
        note: str,
        type_: str,
        chat_id: int,
        date_str: Optional[str] = None,
    ) -> int:
        if date_str is None:
            date_str = date.today().isoformat()
        created_at = datetime.now().isoformat()
        if self.is_postgres:
            sql = (
                f"INSERT INTO txns (date, category, amount, note, \"type\", chat_id, created_at)"
                f" VALUES ({', '.join([self.placeholder] * 7)}) RETURNING id"
            )
            with self._cursor() as cursor:
                cursor.execute(
                    sql,
                    (date_str, category, amount, note, type_, chat_id, created_at),
                )
                row = cursor.fetchone()
            return int(row["id"])

        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO txns (date, category, amount, note, type, chat_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (date_str, category, amount, note, type_, chat_id, created_at),
            )
        return cursor.lastrowid

    def undo_last(self, chat_id: int) -> Optional[Dict[str, object]]:
        type_column = '"type"' if self.is_postgres else "type"
        query = f"SELECT * FROM txns WHERE chat_id = {self.placeholder} ORDER BY created_at DESC LIMIT 1"
        if self.is_postgres:
            with self._cursor() as cursor:
                cursor.execute(query, (chat_id,))
                row = cursor.fetchone()
        else:
            cursor = self.conn.execute(query, (chat_id,))
            row = cursor.fetchone()
        if not row:
            return None
        delete_query = f"DELETE FROM txns WHERE id = {self.placeholder}"
        if self.is_postgres:
            with self._cursor() as cursor:
                cursor.execute(delete_query, (row["id"],))
        else:
            with self.conn:
                self.conn.execute(delete_query, (row["id"],))
        return dict(row)

    def all_rows(self) -> List[Dict[str, object]]:
        query = "SELECT * FROM txns ORDER BY created_at ASC"
        if self.is_postgres:
            with self._cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        else:
            cursor = self.conn.execute(query)
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def rows_for_month(self, month: Optional[str] = None) -> List[Dict[str, object]]:
        start, end = _month_bounds(month)
        query = f"SELECT * FROM txns WHERE date >= {self.placeholder} AND date < {self.placeholder} ORDER BY date ASC, created_at ASC"
        if self.is_postgres:
            with self._cursor() as cursor:
                cursor.execute(query, (start, end))
                rows = cursor.fetchall()
        else:
            cursor = self.conn.execute(query, (start, end))
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def month_total(self, month: Optional[str] = None, include_income: bool = False) -> float:
        start, end = _month_bounds(month)
        type_column = '"type"' if self.is_postgres else "type"
        if include_income:
            query = f"SELECT SUM(amount) as total FROM txns WHERE date >= {self.placeholder} AND date < {self.placeholder}"
            params = (start, end)
        else:
            query = (
                f"SELECT SUM(amount) as total FROM txns WHERE date >= {self.placeholder} AND date < {self.placeholder}"
                f" AND {type_column} != 'income'"
            )
            params = (start, end)
        if self.is_postgres:
            with self._cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()["total"]
        else:
            cursor = self.conn.execute(query, params)
            result = cursor.fetchone()["total"]
        return float(result or 0.0)

    def close(self) -> None:
        self.conn.close()
