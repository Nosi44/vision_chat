from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    # Если новая сессия — очищаем память
    if is_first_message:
        conversation_history = []

    # Формируем контент пользователя
    user_content = [
        {"type": "input_text", "text": prompt}
    ]

    # Добавляем картинку только если она реально есть
    if image_base64:
        user_content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{image_base64}"
        })

    conversation_history.append({
        "role": "user",
        "content": user_content
    })

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=conversation_history
        )

        answer = response.output_text

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
