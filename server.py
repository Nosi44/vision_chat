from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== Глобальная память чата =====
conversation_history = []


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():

    global conversation_history

    data = request.json
    prompt = data.get("prompt")
    image_base64 = data.get("image")
    is_first_message = data.get("first", False)

    # Если это первое сообщение — очищаем память
    if is_first_message:
        conversation_history = []

        # Добавляем картинку только один раз
        conversation_history.append({
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{image_base64}"
                }
            ]
        })
    else:
        # Добавляем только текст
        conversation_history.append({
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt}
            ]
        })

    # Отправляем всю историю в OpenAI
    response = client.responses.create(
        model="gpt-4.1-mini",  # mini быстрее и дешевле
        input=conversation_history
    )

    answer = response.output_text

    # Добавляем ответ ассистента в память
    conversation_history.append({
        "role": "assistant",
        "content": [
            {"type": "output_text", "text": answer}
        ]
    })

    return jsonify({"answer": answer})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
