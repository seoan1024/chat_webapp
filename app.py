import json
import difflib
from collections import defaultdict

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

# 오타 교정 함수
def correct_typo(user_input, vocab_list):
    return ' '.join([
        difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7)[0] if difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7) else w
        for w in user_input.split()
    ])

# 비슷한 질문 찾기 함수
def find_similar_question(user_input, memory):
    for q in memory:
        if difflib.SequenceMatcher(None, user_input, q).ratio() > 0.75:
            return q
    return None

# 사용자 말투 분석 함수
def extract_style(user_input):
    # 입력된 단어 수가 적으면 '친근한' 스타일, 많으면 '형식적인' 스타일로 분류
    if len(user_input.split()) < 5:
        return 'friendly'
    else:
        return 'formal'
