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

    if not prompt and not image_base64:
        return jsonify({"error": "Пустой запрос"}), 400

    # ===============================
    # 🎨 КЛЮЧЕВЫЕ СЛОВА ДЛЯ ГЕНЕРАЦИИ
    # ===============================
    generation_keywords = [
        "нарисуй",
        "создай изображение",
        "сгенерируй",
        "draw",
        "generate image",
        "create image"
    ]

    is_generation_request = False

    if prompt:
        lower_prompt = prompt.lower()
        for word in generation_keywords:
            if word in lower_prompt:
                is_generation_request = True
                break

    # ===============================
    # 🖌 РЕДАКТИРОВАНИЕ КАРТИНКИ
    # (если есть image + текст)
    # ===============================
    if image_base64 and prompt:
        try:
            img = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                image=image_base64,
                size="512x512"
            )

            new_image = img.data[0].b64_json

            return jsonify({
                "generated_image": new_image
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ===============================
    # 🎨 ГЕНЕРАЦИЯ С НУЛЯ
    # ===============================
    if is_generation_request and not image_base64:
        try:
            img = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="512x512"
            )

            new_image = img.data[0].b64_json

            return jsonify({
                "generated_image": new_image
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ===============================
    # 🧠 ОБЫЧНЫЙ ЧАТ / VISION
    # ===============================
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
