from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_FILE = "chats.db"


# =========================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ
# =========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# ГЛАВНАЯ СТРАНИЦА
# =========================
@app.route("/")
def home():
    return render_template("index.html")


# =========================
# СОЗДАТЬ НОВЫЙ ЧАТ
# =========================
@app.route("/api/create_chat", methods=["POST"])
def create_chat():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO chats (created_at) VALUES (?)", (now,))
    chat_id = c.lastrowid

    conn.commit()
    conn.close()

    return jsonify({"chat_id": chat_id})


# =========================
# ПОЛУЧИТЬ СПИСОК ЧАТОВ
# =========================
@app.route("/api/get_chats")
def get_chats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT id, created_at FROM chats ORDER BY id DESC")
    chats = c.fetchall()

    conn.close()

    return jsonify([
        {"id": chat[0], "created_at": chat[1]}
        for chat in chats
    ])


# =========================
# ПОЛУЧИТЬ СООБЩЕНИЯ ЧАТА
# =========================
@app.route("/api/get_messages/<int:chat_id>")
def get_messages(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT role, content FROM messages
        WHERE chat_id=?
        ORDER BY id ASC
    """, (chat_id,))

    messages = c.fetchall()
    conn.close()

    return jsonify([
        {"role": m[0], "content": m[1]}
        for m in messages
    ])


# =========================
# ОТПРАВКА СООБЩЕНИЯ
# =========================
@app.route("/api/send_message", methods=["POST"])
def send_message():

    data = request.json
    chat_id = data.get("chat_id")
    prompt = data.get("prompt")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    now = datetime.utcnow().isoformat()

    # сохраняем сообщение пользователя
    c.execute("""
        INSERT INTO messages (chat_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """, (chat_id, "user", prompt, now))

    conn.commit()

    # получаем историю чата
    c.execute("""
        SELECT role, content FROM messages
        WHERE chat_id=?
        ORDER BY id ASC
    """, (chat_id,))

    history = c.fetchall()

    # готовим историю для OpenAI
    openai_messages = []
    for role, content in history:
        openai_messages.append({
            "role": role,
            "content": [{"type": "input_text", "text": content}]
        })

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=openai_messages
    )

    answer = response.output_text

    # сохраняем ответ ассистента
    c.execute("""
        INSERT INTO messages (chat_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """, (chat_id, "assistant", answer, now))

    conn.commit()
    conn.close()

    return jsonify({"answer": answer})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
