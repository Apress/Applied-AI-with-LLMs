from contextlib import closing
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "accounting.db"


# Utility DB
def run_sql(query: str, params: tuple = ()):
    """execute the query in the db"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            cur = conn.execute(query, params)

            if cur.description is not None:
                return cur.fetchall()

            return cur.lastrowid


# Tools
def get_invoices(client: str, period: str):
    """Listing all the invoices of a single client for a certain time"""
    return run_sql(
        "SELECT id, client, date, service, amount FROM invoices WHERE client=? AND date LIKE ?",
        (client, f"{period}%"),
    )


def add_invoice(client: str, date: str, service: str, amount: float):
    """Inserting a new invoice"""
    run_sql(
        "INSERT INTO invoices (client, date, service, amount) VALUES (?, ?, ?, ?)",
        (client, date, service, amount),
    )
    return {
        "status": "ok",
        "client": client,
        "date": date,
        "service": service,
        "amount": amount,
    }


def get_client_stats(client: str, period: str):
    """Shows client stats"""
    return run_sql(
        "SELECT service, COUNT(*) FROM invoices WHERE client=? AND date LIKE ? GROUP BY service",
        (client, f"{period}%"),
    )


def get_top_services(period: str):
    """get the most used services"""
    return run_sql(
        "SELECT service, COUNT(*) FROM invoices WHERE date LIKE ? GROUP BY service ORDER BY COUNT(*) DESC",
        (f"{period}%",),
    )


def get_total_revenue(period: str):
    """Total revenue for a given YYYY-MM period."""
    rows = run_sql(
        "SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE date LIKE ?",
        (f"{period}%",),
    )
    return rows[0][0]


# Dispatcher
TOOL_FUNCTIONS = {
    "get_invoices": get_invoices,
    "add_invoice": add_invoice,
    "get_client_stats": get_client_stats,
    "get_top_services": get_top_services,
    "get_total_revenue": get_total_revenue,
}
