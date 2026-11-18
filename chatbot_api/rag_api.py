from flask import Flask, request, jsonify
from rag_core import rag_pipeline

app = Flask(__name__)

# Pydantic model is not directly used in Flask in the same way,
# we'll handle JSON directly.

@app.route("/ask", methods=["POST"])
def ask_question():
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' in request body"}), 400
    
    question_text = data["question"]
    response = rag_pipeline(question_text)
    return jsonify({"question": question_text, "answer": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
    