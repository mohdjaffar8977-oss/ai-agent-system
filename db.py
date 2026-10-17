import sqlite3

DB_NAME = "agency.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            client_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            phone_number_id TEXT,
            ai_pause_hours INTEGER DEFAULT 24
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            customer_number TEXT NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            client_id INTEGER NOT NULL,
            customer_number TEXT NOT NULL,
            ai_paused_until TEXT,
            PRIMARY KEY (client_id, customer_number)
        )
    """)
    conn.commit()
    conn.close()

def add_fake_clients():
    conn = get_connection()
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    if count == 0:
        cur.execute(
            "INSERT INTO clients (name, system_prompt) VALUES (?, ?)",
            ("Test Kapde Ki Dukaan", "You are a polite assistant for a clothing shop. Reply briefly in Hindi/Hinglish."),
        )
        cur.execute(
            "INSERT INTO clients (name, system_prompt) VALUES (?, ?)",
            ("Test Clinic", "You are a polite assistant for a clinic. Reply briefly in Hindi/Hinglish. Never give medical advice."),
        )
        conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    add_fake_clients()
    conn = get_connection()
    for row in conn.execute("SELECT client_id, name FROM clients"):
        print(row["client_id"], row["name"])
    conn.close()

def get_client_by_id(client_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
    client = cursor.fetchone()
    conn.close()
    return dict(client) if client else None


def get_client_by_phone_number_id(phone_number_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE phone_number_id = ?", (phone_number_id,))
    client = cursor.fetchone()
    conn.close()
    return dict(client) if client else None


def save_message(client_id, customer_number, role, text):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (client_id, customer_number, role, text) VALUES (?, ?, ?, ?)",
        (client_id, customer_number, role, text),
    )
    conn.commit()
    conn.close()


def is_ai_paused(client_id, customer_number):
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ai_paused_until FROM conversations WHERE client_id = ? AND customer_number = ?",
        (client_id, customer_number),
    )
    row = cursor.fetchone()
    conn.close()
    if not row or not row["ai_paused_until"]:
        return False
    try:
        return datetime.fromisoformat(row["ai_paused_until"]) > datetime.now()
    except ValueError:
        return False


def pause_client_ai(client_id, minutes=5):
    from datetime import datetime, timedelta
    until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clients SET ai_error_paused_until = ? WHERE client_id = ?",
        (until, client_id),
    )
    conn.commit()
    conn.close()


def is_client_ai_paused(client_id):
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ai_error_paused_until FROM clients WHERE client_id = ?",
        (client_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row or not row["ai_error_paused_until"]:
        return False
    try:
        return datetime.fromisoformat(row["ai_error_paused_until"]) > datetime.now()
    except ValueError:
        return False
