from flask import Flask, request, jsonify, render_template
import json, os, difflib
from duckduckgo_search import DDGS
from collections import defaultdict

# Flask 애플리케이션
app = Flask(__name__)

# 파일 경로 설정
HISTORY_FILE = "memory.json"
USER_STYLE_FILE = "user_styles.json"
ADMIN_PASSWORD = "seoan1024"
DEFAULT_MEMORY = {
    "안녕": "안녕하세요! 무엇을 도와드릴까요?",
    "오늘 날씨 어때?": "지역마다 다르지만, 대체로 맑거나 흐릴 수 있어요.",
    "고마워": "언제든지요!"
}

# 기본 메모리 파일이 없으면 생성
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_MEMORY, f, ensure_ascii=False, indent=2)

# 메모리 불러오기
with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
    memory = json.load(f)

vocab_list = list(DEFAULT_MEMORY.keys()) + ["정렬", "리스트", "파이썬", "기억", "검색", "챗봇", "날씨", "시간", "감사", "가격"]
last_response = ""

# 오타 교정 함수
def correct_typo(user_input):
    return ' '.join([
        difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7)[0] if difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7) else w
        for w in user_input.split()
    ])

# 비슷한 질문 찾기
def find_similar_question(user_input):
    for q in memory:
        if difflib.SequenceMatcher(None, user_input, q).ratio() > 0.75:
            return q
    return None

# 웹 검색 함수
def search_web(query):
    with DDGS() as ddgs:
        results = list(ddgs.text(query, region='wt-wt', safesearch='Moderate', max_results=1))
        if results:
            body = results[0].get('body', '')
            url = results[0].get('href', '')
            if body:
                return f"{body} (출처: {url})" if url else body
    return ""

# 텍스트 요약 함수
def summarize_text(text):
    sentences = text.split('.')
    important = [s.strip() for s in sentences if len(s.strip()) > 20]
    return '.'.join(important[:2]) + '.' if important else ''

# 사용자 말투 분석 함수
def extract_style(user_input):
    # 입력된 단어 수가 적으면 '친근한' 스타일, 많으면 '형식적인' 스타일로 분류
    if len(user_input.split()) < 5:
        return 'friendly'
    else:
        return 'formal'

# 사용자 스타일 데이터를 저장하는 함수
def save_user_style(user_input, style, filename="user_styles.json"):
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

    with open(filename, 'r', encoding='utf-8') as f:
        styles_data = json.load(f)
    
    user_id = "default_user"  # 사용자의 ID가 있다면 이 부분을 사용자 고유 ID로 변경
    if user_id not in styles_data:
        styles_data[user_id] = defaultdict(list)
    
    styles_data[user_id][style].append(user_input)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(styles_data, f, ensure_ascii=False, indent=2)

# 저장된 스타일 데이터를 불러오는 함수
def load_user_styles(filename="user_styles.json"):
    if not os.path.exists(filename):
        return {}
    
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

# 메모리 저장 함수
def save_memory():
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat():
    global last_response
    user_input = request.json['message']
    
    # 관리자가 입력한 암호 처리
    if user_input.strip() == ADMIN_PASSWORD:
        # 메모리와 사용자 스타일 모두 출력
        with open(USER_STYLE_FILE, 'r', encoding='utf-8') as f:
            user_styles = json.load(f)
        return jsonify({
            "reply": "관리자 모드입니다.\n메모리:\n" + json.dumps(memory, ensure_ascii=False, indent=2) + "\n\n사용자 스타일:\n" + json.dumps(user_styles, ensure_ascii=False, indent=2)
        })
    
    # 사용자의 말투를 분석
    style = extract_style(user_input)
    
    # 말투를 저장
    save_user_style(user_input, style, filename=USER_STYLE_FILE)
    
    # 기존 메모리에서 답변 찾기
    if "요약" in user_input:
        reply = summarize_text(last_response)
    else:
        corrected = correct_typo(user_input)
        similar_q = find_similar_question(corrected)
        if similar_q:
            reply = memory[similar_q]
        else:
            web_info = search_web(corrected)
            summary = summarize_text(web_info) if web_info else "죄송해요, 잘 모르겠어요."
            source = web_info.split(' (출처: ')[-1] if '출처:' in web_info else ''
            
            # 스타일에 맞게 응답
            if style == 'friendly':
                reply = f"안녕하세요! {summary}"
            else:
                reply = f"안녕하세요, {summary}"
            
            if source:
                reply += f"\n\n출처: {source}"
            
            # 새로운 질문과 답변을 메모리에 저장
            memory[corrected] = reply
            save_memory()

    last_response = reply
    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
