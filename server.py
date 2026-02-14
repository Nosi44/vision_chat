from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Память текущей сессии (временная, но нам важна только отправка контекста)
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

    message_content = []

    if prompt:
        message_content.append({
            "type": "input_text",
            "text": prompt
        })

    if image_base64:
        message_content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{image_base64}"
        })

    conversation_history.append({
        "role": "user",
        "content": message_content
    })

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=conversation_history
        )

        answer = response.output_text

        conversation_history.append({
            "role": "assistant",
            "content": [
                {"type": "output_text", "text": answer}
            ]
        })

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)