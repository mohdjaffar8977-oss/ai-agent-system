import sqlite3

conn = sqlite3.connect("agency.db")
rows = conn.execute(
    "SELECT q.id, c.name, q.customer_number, q.reason, q.created_at "
    "FROM human_queue q LEFT JOIN clients c ON c.client_id = q.client_id "
    "WHERE q.resolved = 0 ORDER BY q.id"
).fetchall()
conn.close()

if not rows:
    print("Queue khali hai.")
for qid, name, number, reason, created in rows:
    masked = number[:3] + "xxxxx" + number[-3:]
    print(f"#{qid} | {name} | {masked} | {reason} | {created}")
print(f"Total khuli: {len(rows)}")
