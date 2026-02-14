from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import sqlite3
import os

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_FILE = "chats.db"


# ==========================
# ИНИЦИАЛИЗАЦИЯ БД
# ==========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            image TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ==========================
# ГЛАВНАЯ СТРАНИЦА
# ==========================
@app.route("/")
def home():
    return render_template("index.html")


# ==========================
# ПОЛУЧИТЬ СПИСОК ЧАТОВ
# ==========================
@app.route("/api/chats", methods=["GET"])
def get_chats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT id, title FROM chats ORDER BY id DESC")
    chats = [{"id": row[0], "title": row[1]} for row in c.fetchall()]

    conn.close()
    return jsonify(chats)


# ==========================
# СОЗДАТЬ НОВЫЙ ЧАТ
# ==========================
@app.route("/api/chats", methods=["POST"])
def create_chat():
    data = request.json
    title = data.get("title", "Новый чат")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("INSERT INTO chats (title) VALUES (?)", (title,))
    chat_id = c.lastrowid

    conn.commit()
    conn.close()

    return jsonify({"chat_id": chat_id})


# ==========================
# ПОЛУЧИТЬ СООБЩЕНИЯ ЧАТА
# ==========================
@app.route("/api/messages/<int:chat_id>", methods=["GET"])
def get_messages(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT role, content, image
        FROM messages
        WHERE chat_id=?
        ORDER BY id ASC
    """, (chat_id,))

    messages = []
    for role, content, image in c.fetchall():
        messages.append({
            "role": role,
            "content": content,
            "image": image
        })

    conn.close()
    return jsonify(messages)


# ==========================
# ОТПРАВКА СООБЩЕНИЯ
# ==========================
@app.route("/api/send", methods=["POST"])
def send_message():

    data = request.json
    chat_id = data.get("chat_id")
    content = data.get("content")
    image = data.get("image")

    if not chat_id:
        return jsonify({"error": "Нет chat_id"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # --- Сохраняем сообщение пользователя ---
    c.execute("""
        INSERT INTO messages (chat_id, role, content, image)
        VALUES (?, ?, ?, ?)
    """, (chat_id, "user", content, image))

    conn.commit()

    # --- Получаем всю историю ---
    c.execute("""
        SELECT role, content, image
        FROM messages
        WHERE chat_id=?
        ORDER BY id ASC
    """, (chat_id,))

    history = c.fetchall()

    openai_messages = []

    for role, msg_content, msg_image in history:

        message_content = []

        # ВАЖНО: проверяем is not None, а не if content
        if msg_content is not None:
            message_content.append({
                "type": "input_text",
                "text": msg_content
            })

        if msg_image:
            message_content.append({
                "type": "input_image",
                "image_url": f"data:image/png;base64,{msg_image}"
            })

        openai_messages.append({
            "role": role,
            "content": message_content
        })

    # --- Запрос к OpenAI ---
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=openai_messages
        )

        answer = response.output_text

    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

    # --- Сохраняем ответ ассистента ---
    c.execute("""
        INSERT INTO messages (chat_id, role, content, image)
        VALUES (?, ?, ?, NULL)
    """, (chat_id, "assistant", answer))

    conn.commit()
    conn.close()

    return jsonify({"answer": answer})


# ==========================
# ЗАПУСК
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
