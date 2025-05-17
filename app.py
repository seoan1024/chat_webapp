from flask import Flask, request, jsonify, render_template
import json, os, difflib
from transformers import AutoModelForCausalLM, PreTrainedTokenizerFast
import torch

app = Flask(__name__)

HISTORY_FILE = "memory.json"
ADMIN_PASSWORD = "seoan1024"
DEFAULT_MEMORY = {
    "안녕": "안녕하세요! 무엇을 도와드릴까요?",
    "오늘 날씨 어때?": "지역마다 다르지만, 대체로 맑거나 흐릴 수 있어요.",
    "고마워": "언제든지요!"
}

if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_MEMORY, f, ensure_ascii=False, indent=2)

with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
    memory = json.load(f)

vocab_list = list(DEFAULT_MEMORY.keys()) + ["정렬", "리스트", "파이썬", "기억", "검색", "챗봇", "날씨", "시간", "감사", "가격"]
last_response = ""

model_name_or_path = "skt/kogpt2-base-v2"
tokenizer = PreTrainedTokenizerFast.from_pretrained(model_name_or_path)

# eos_token 없으면 지정
if tokenizer.eos_token is None:
    tokenizer.eos_token = "</s>"

# pad_token 없으면 eos_token으로 추가
if tokenizer.pad_token is None:
    tokenizer.add_special_tokens({'pad_token': tokenizer.eos_token})

model = AutoModelForCausalLM.from_pretrained(model_name_or_path)
model.resize_token_embeddings(len(tokenizer))

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def correct_typo(user_input):
    return ' '.join([
        difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7)[0] if difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7) else w
        for w in user_input.split()
    ])

def generate_answer(question):
    inputs = tokenizer(question, return_tensors="pt", padding=True).to(device)
    outputs = model.generate(
        **inputs,
        max_length=64,
        do_sample=True,              # 샘플링 활성화
        top_p=0.9,                   # nucleus sampling
        top_k=50,                    # top-k 샘플링
        repetition_penalty=1.2,      # 반복 억제
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
        num_return_sequences=1,
    )
    answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if answer.startswith(question):
        answer = answer[len(question):].strip()
    return answer


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat():
    global last_response
    user_input = request.json['message']

    if user_input.strip() == ADMIN_PASSWORD:
        reply = '\n'.join([f"Q: {q}\nA: {a}" for q, a in memory.items()])
    else:
        corrected = correct_typo(user_input)
        similar_q = None
        for q in memory:
            if difflib.SequenceMatcher(None, corrected, q).ratio() > 0.75:
                similar_q = q
                break
        if similar_q:
            reply = memory[similar_q]
        else:
            reply = generate_answer(corrected)
            memory[corrected] = reply
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)

    last_response = reply
    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
