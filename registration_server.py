from flask import Flask, request, render_template_string, redirect, url_for
import os
import socket
import json



app = Flask(__name__)

# 참석자 데이터 파일 경로
PARTICIPANTS_FILE = 'participants.json'

# 서버 IP 주소 고정
SERVER_IP = 'localhost'
SERVER_PORT = 5000

# 참석자 목록을 불러오는 함수
def load_participants():
    if os.path.exists(PARTICIPANTS_FILE):
        try:
            with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

# 참석자 목록을 저장하는 함수
def save_participants(participants):
    with open(PARTICIPANTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(participants, f, ensure_ascii=False, indent=2)

# HTML 템플릿
REGISTRATION_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>행사 참여자 이벤트 등록</title>
    <style>
        body {
            font-family: 'Malgun Gothic', sans-serif;
            max-width: 500px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }
        button:hover {
            background-color: #45a049;
        }
        .success {
            color: #4CAF50;
            margin-top: 20px;
            font-weight: bold;
        }
        .error {
            color: #f44336;
            margin-top: 20px;
            font-weight: bold;
        }
        .participants {
            margin-top: 30px;
            text-align: left;
        }
        .participants h2 {
            font-size: 18px;
            margin-bottom: 10px;
        }
        .participants ul {
            list-style-type: none;
            padding: 0;
        }
        .participants li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .reset-button {
            background-color: #f44336;
            margin-top: 20px;
        }
        .reset-button:hover {
            background-color: #d32f2f;
        }
        .admin-section {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
    </style>
</head>
<body>
    <h1>행사 참여자 이벤트 등록</h1>
    
    {% if success %}
    <p class="success">{{ success }}</p>
    {% endif %}
    
    {% if error %}
    <p class="error">{{ error }}</p>
    {% endif %}
    
    <form method="post" action="{{ url_for('register') }}">
        <div class="form-group">
            <input type="text" name="name" placeholder="사번을 입력하세요" required>
        </div>
        <button type="submit">등록하기</button>
    </form>
    
    <div class="participants">
        <h2>현재 참석자 목록 ({{ participants|length }}명)</h2>
        <ul>
            {% for participant in participants %}
            <li>{{ participant }}</li>
            {% endfor %}
        </ul>
    </div>
    
    <div class="admin-section">
        <h2>관리자 기능</h2>
        <form method="post" action="{{ url_for('reset') }}" onsubmit="return confirm('정말로 모든 참석자 목록을 초기화하시겠습니까?');">
            <button type="submit" class="reset-button">참석자 목록 초기화</button>
        </form>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    participants = load_participants()
    return render_template_string(
        REGISTRATION_TEMPLATE, 
        participants=participants,
        success=request.args.get('success'),
        error=request.args.get('error')
    )

@app.route('/register', methods=['POST'])
def register():
    employee_id = request.form.get('name', '').strip()
    if employee_id:
        participants = load_participants()
        if employee_id not in participants:
            participants.append(employee_id)
            save_participants(participants)
            return redirect(url_for('index', success=f'사번 {employee_id} 등록이 완료되었습니다!'))
        else:
            return redirect(url_for('index', success=f'사번 {employee_id}은(는) 이미 등록되어 있습니다.'))
    return redirect(url_for('index'))

@app.route('/reset', methods=['POST'])
def reset():
    """참석자 목록 초기화"""
    save_participants([])
    return redirect(url_for('index', success='참석자 목록이 초기화되었습니다.'))

def get_local_ip():
    try:
        # 로컬 IP 주소 가져오기
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == '__main__':
    port = SERVER_PORT
    print(f"서버가 시작되었습니다. 다음 주소로 접속하세요:")
    print(f"http://{SERVER_IP}:{port}")
    app.run(host=SERVER_IP, port=port, debug=True) 