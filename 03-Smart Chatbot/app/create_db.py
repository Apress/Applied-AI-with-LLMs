from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "accounting.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client TEXT,
    date TEXT,
    service TEXT,
    amount REAL
)
""")

sample_data = [
    ("Mario Rossi", "2024-01-10", "Consulenza fiscale", 500.0),
    ("Mario Rossi", "2024-03-15", "Dichiarazione redditi", 300.0),
    ("Mario Rossi", "2024-06-20", "Revisione contabile", 450.0),
    ("Luca Bianchi", "2024-02-05", "Consulenza fiscale", 800.0),
    ("Maria Verdi", "2024-07-12", "Consulenza aziendale", 1200.0),
]

cur.executemany("INSERT INTO invoices (client, date, service, amount) VALUES (?, ?, ?, ?)", sample_data)
conn.commit()
conn.close()

print("Database accounting.db created and populated (examples data)")
