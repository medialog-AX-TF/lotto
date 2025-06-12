import sys
import random
import time
import os
import json
import socket
import threading
import qrcode
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QFileDialog, QTextEdit, QSpinBox, 
                            QMessageBox, QLineEdit, QScrollArea, QDialog)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, QRect
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap
import subprocess

# 참석자 데이터 파일 경로

PARTICIPANTS_FILE = 'participants.json'

# 서버 IP 주소 및 포트 고정
SERVER_IP = 'localhost'
SERVER_PORT = 5000
SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

# 외부 접속용 ngrok URL (QR 코드에 사용)
NGROK_URL = "https://0e71-13-124-14-57.ngrok-free.app"

class QRCodeDialog(QDialog):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QR 코드 스캔")
        self.setMinimumSize(400, 500)
        
        layout = QVBoxLayout(self)
        
        # 안내 텍스트
        info_label = QLabel("아래 QR 코드를 스캔하여 참석자 등록을 해주세요")
        info_label.setFont(QFont("맑은 고딕", 12))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # URL 표시
        url_label = QLabel(url)
        url_label.setFont(QFont("맑은 고딕", 10))
        url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(url_label)
        
        # QR 코드 생성 및 표시
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_path = "qrcode.png"
        img.save(img_path)
        
        qr_label = QLabel()
        qr_pixmap = QPixmap(img_path)
        qr_label.setPixmap(qr_pixmap)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(qr_label)
        
        # 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

class LotteryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("행사 참여자 이벤트 추첨 !!")
        self.setMinimumSize(800, 600)
        
        # 참석자 목록
        self.participants = []
        
        # 당첨자 목록
        self.winners = []
        
        # 서버 프로세스
        self.server_process = None
        
        # UI 초기화
        self.init_ui()
        
        # 참석자 데이터 로드
        self.load_participants()
        
    def init_ui(self):
        # 메인 위젯 및 레이아웃
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 제목
        title_label = QLabel("행사 참여자 이벤트 추첨 !!")
        title_font = QFont("맑은 고딕", 24, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 참석자 관리 섹션
        participant_section = QWidget()
        participant_layout = QVBoxLayout(participant_section)
        
        participant_title = QLabel("참석자 관리")
        participant_title.setFont(QFont("맑은 고딕", 16, QFont.Weight.Bold))
        participant_layout.addWidget(participant_title)
        
        # 참석자 입력 영역
        input_layout = QHBoxLayout()
        self.participant_input = QLineEdit()
        self.participant_input.setPlaceholderText("참석자 사번 입력")
        add_button = QPushButton("추가")
        add_button.clicked.connect(self.add_participant)
        input_layout.addWidget(self.participant_input, 4)
        input_layout.addWidget(add_button, 1)
        participant_layout.addLayout(input_layout)
        
        # QR 코드 및 파일 버튼 레이아웃
        buttons_layout = QHBoxLayout()
        
        # QR 코드 버튼
        qr_button = QPushButton("QR 코드로 참석자 등록")
        qr_button.clicked.connect(self.show_qr_code)
        buttons_layout.addWidget(qr_button)
        
        # 파일 불러오기 버튼
        file_button = QPushButton("파일에서 불러오기")
        file_button.clicked.connect(self.load_from_file)
        buttons_layout.addWidget(file_button)
        
        # 참석자 새로고침 버튼
        refresh_button = QPushButton("참석자 새로고침")
        refresh_button.clicked.connect(self.refresh_participants)
        buttons_layout.addWidget(refresh_button)
        
        participant_layout.addLayout(buttons_layout)
        
        # 참석자 초기화 버튼 (두 번째 버튼 행)
        reset_layout = QHBoxLayout()
        reset_button = QPushButton("참석자 목록 초기화")
        reset_button.setStyleSheet("background-color: #f44336; color: white;")
        reset_button.clicked.connect(self.reset_participants)
        reset_layout.addWidget(reset_button)
        participant_layout.addLayout(reset_layout)
        
        # 참석자 목록 표시
        self.participant_list = QTextEdit()
        self.participant_list.setReadOnly(True)
        participant_layout.addWidget(self.participant_list)
        
        main_layout.addWidget(participant_section)
        
        # 추첨 설정 섹션
        lottery_section = QWidget()
        lottery_layout = QHBoxLayout(lottery_section)
        
        # 당첨자 수 설정
        winner_count_layout = QVBoxLayout()
        winner_count_label = QLabel("당첨자 수:")
        self.winner_count = QSpinBox()
        self.winner_count.setMinimum(1)
        self.winner_count.setMaximum(10)
        self.winner_count.setValue(1)
        winner_count_layout.addWidget(winner_count_label)
        winner_count_layout.addWidget(self.winner_count)
        lottery_layout.addLayout(winner_count_layout)
        
        # 추첨 시작 버튼
        self.start_button = QPushButton("추첨 시작")
        self.start_button.setFont(QFont("맑은 고딕", 16))
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(self.start_lottery)
        lottery_layout.addWidget(self.start_button, 3)
        
        main_layout.addWidget(lottery_section)
        
        # 추첨 결과 표시 영역
        result_section = QWidget()
        result_layout = QVBoxLayout(result_section)
        
        result_title = QLabel("추첨 결과")
        result_title.setFont(QFont("맑은 고딕", 16, QFont.Weight.Bold))
        result_layout.addWidget(result_title)
        
        # 결과 표시를 QLabel에서 QTextEdit으로 변경하여 스크롤 가능하게 함
        self.result_display = QTextEdit("추첨을 시작하면 여기에 결과가 표시됩니다.")
        self.result_display.setFont(QFont("맑은 고딕", 20))
        self.result_display.setReadOnly(True)
        self.result_display.setMinimumHeight(150)
        self.result_display.setStyleSheet("background-color: #f0f0f0; border-radius: 10px; padding: 20px; text-align: center;")
        # QTextEdit에서는 setAlignment 대신 document()의 setDefaultTextOption을 사용
        text_option = self.result_display.document().defaultTextOption()
        text_option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_display.document().setDefaultTextOption(text_option)
        result_layout.addWidget(self.result_display)
        
        # 결과 저장 버튼
        save_button = QPushButton("결과 저장")
        save_button.clicked.connect(self.save_results)
        result_layout.addWidget(save_button)
        
        main_layout.addWidget(result_section)
        
        self.setCentralWidget(main_widget)
        
        # 서버 시작
        self.start_registration_server()
        
    def start_registration_server(self):
        """등록 서버를 백그라운드에서 시작"""
        try:
            # 서버 스크립트 실행
            self.server_process = subprocess.Popen([sys.executable, "registration_server.py"], 
                                                 stdout=subprocess.PIPE, 
                                                 stderr=subprocess.PIPE,
                                                 text=True)
            
            # 고정 서버 URL 사용
            self.server_url = SERVER_URL
            print(f"서버 URL: {self.server_url}")
                
        except Exception as e:
            QMessageBox.warning(self, "서버 오류", f"등록 서버를 시작하는 중 오류가 발생했습니다: {str(e)}")
    
    def show_qr_code(self):
        """QR 코드 다이얼로그 표시"""
        # ngrok URL을 QR 코드에 사용
        dialog = QRCodeDialog(NGROK_URL, self)
        dialog.exec()
    
    def load_participants(self):
        """참석자 데이터 파일에서 참석자 목록 로드"""
        if os.path.exists(PARTICIPANTS_FILE):
            try:
                with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
                    self.participants = json.load(f)
                self.update_participant_list()
            except Exception as e:
                QMessageBox.warning(self, "파일 오류", f"참석자 목록을 불러오는 중 오류가 발생했습니다: {str(e)}")
    
    def refresh_participants(self):
        """참석자 목록 새로고침"""
        self.load_participants()
        QMessageBox.information(self, "새로고침 완료", f"참석자 목록을 새로고침했습니다. 현재 {len(self.participants)}명이 등록되어 있습니다.")
    
    def reset_participants(self):
        """참석자 목록 초기화"""
        # 확인 대화상자 표시
        reply = QMessageBox.question(
            self, 
            "참석자 초기화", 
            "정말로 모든 참석자 목록을 초기화하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 참석자 목록 초기화
            self.participants = []
            self.save_participants()
            self.update_participant_list()
            QMessageBox.information(self, "초기화 완료", "참석자 목록이 초기화되었습니다.")
    
    def add_participant(self):
        employee_id = self.participant_input.text().strip()
        if employee_id:
            if employee_id not in self.participants:
                self.participants.append(employee_id)
                self.save_participants()
                self.update_participant_list()
                self.participant_input.clear()
            else:
                QMessageBox.warning(self, "중복 오류", "이미 등록된 사번입니다.")
        else:
            QMessageBox.warning(self, "입력 오류", "참석자 사번을 입력해주세요.")
    
    def save_participants(self):
        """참석자 목록을 파일에 저장"""
        try:
            with open(PARTICIPANTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.participants, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "저장 오류", f"참석자 목록을 저장하는 중 오류가 발생했습니다: {str(e)}")
    
    def load_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "참석자 목록 파일 선택", "", "텍스트 파일 (*.txt);;CSV 파일 (*.csv);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    if file_path.endswith('.csv'):
                        # CSV 파일 처리
                        for line in file:
                            employee_ids = line.strip().split(',')
                            for employee_id in employee_ids:
                                employee_id = employee_id.strip()
                                if employee_id and employee_id not in self.participants:
                                    self.participants.append(employee_id)
                    else:
                        # 텍스트 파일 처리
                        for line in file:
                            employee_id = line.strip()
                            if employee_id and employee_id not in self.participants:
                                self.participants.append(employee_id)
                
                self.save_participants()
                self.update_participant_list()
                QMessageBox.information(self, "파일 불러오기", f"{len(self.participants)}명의 참석자를 불러왔습니다.")
            except Exception as e:
                QMessageBox.critical(self, "파일 오류", f"파일을 불러오는 중 오류가 발생했습니다: {str(e)}")
    
    def update_participant_list(self):
        self.participant_list.clear()
        for i, name in enumerate(self.participants, 1):
            self.participant_list.append(f"{i}. {name}")
    
    def start_lottery(self):
        if len(self.participants) == 0:
            QMessageBox.warning(self, "추첨 오류", "참석자 목록이 비어있습니다.")
            return
        
        winner_count = self.winner_count.value()
        if winner_count > len(self.participants):
            QMessageBox.warning(self, "추첨 오류", "당첨자 수가 참석자 수보다 많습니다.")
            return
        
        # 카운트다운 시작
        self.result_display.setText("추첨을 시작합니다...")
        self.start_button.setEnabled(False)
        
        # 카운트다운 애니메이션
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_value = 3
        self.update_countdown()
        self.countdown_timer.start(1000)
    
    def update_countdown(self):
        if self.countdown_value > 0:
            self.result_display.setText(f"{self.countdown_value}")
            self.countdown_value -= 1
        else:
            self.countdown_timer.stop()
            self.run_lottery_animation()
    
    def run_lottery_animation(self):
        # 룰렛 애니메이션 효과
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_count = 0
        self.animation_max = 20  # 애니메이션 반복 횟수
        self.animation_timer.start(100)  # 100ms마다 업데이트
    
    def update_animation(self):
        if self.animation_count < self.animation_max:
            # 랜덤하게 참석자 사번 표시
            random_idx = random.randint(0, len(self.participants) - 1)
            self.result_display.setText(self.participants[random_idx])
            self.animation_count += 1
        else:
            self.animation_timer.stop()
            self.select_winners()
    
    def select_winners(self):
        winner_count = self.winner_count.value()
        
        # 1000번 이상의 사번과 1000번 미만의 사번으로 분류
        high_numbers = [p for p in self.participants if int(p) >= 1000]
        low_numbers = [p for p in self.participants if int(p) < 1000]
        
        # 당첨자 수가 참석자 수보다 많은 경우 처리
        if winner_count >= len(self.participants):
            self.winners = self.participants.copy()
        else:
            self.winners = []
            
            # 1000번대 당첨자 수 계산 (전체 당첨자의 70%)
            high_winners_count = int(winner_count * 0.7)
            
            # 1000번대 당첨자 수가 1000번대 참석자 수보다 많은 경우 조정
            if high_winners_count > len(high_numbers):
                high_winners_count = len(high_numbers)
            
            # 1000번 미만 당첨자 수 계산
            low_winners_count = winner_count - high_winners_count
            
            # 1000번 미만 당첨자 수가 1000번 미만 참석자 수보다 많은 경우 조정
            if low_winners_count > len(low_numbers):
                low_winners_count = len(low_numbers)
                # 부족한 당첨자 수를 1000번대에서 추가로 채움
                high_winners_count = min(len(high_numbers), winner_count - low_winners_count)
            
            # 1000번 이상 사번에서 당첨자 선택
            if high_winners_count > 0 and high_numbers:
                self.winners.extend(random.sample(high_numbers, high_winners_count))
            
            # 1000번 미만 사번에서 당첨자 선택
            if low_winners_count > 0 and low_numbers:
                self.winners.extend(random.sample(low_numbers, low_winners_count))
            
            # 당첨자 수가 부족한 경우 남은 참석자에서 추가 선택
            if len(self.winners) < winner_count:
                remaining = [p for p in self.participants if p not in self.winners]
                additional_winners = min(winner_count - len(self.winners), len(remaining))
                if additional_winners > 0:
                    self.winners.extend(random.sample(remaining, additional_winners))
        
        # 결과 표시
        if len(self.winners) == 1:
            result_text = f"🎉 축하합니다! 🎉\n\n{self.winners[0]}"
        else:
            winners_text = "\n".join([f"{i+1}. {name}" for i, name in enumerate(self.winners)])
            result_text = f"🎉 축하합니다! 🎉\n\n{winners_text}"
        
        self.result_display.setText(result_text)
        self.start_button.setEnabled(True)
    
    def save_results(self):
        if not self.winners:
            QMessageBox.warning(self, "저장 오류", "저장할 추첨 결과가 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "결과 저장", "추첨결과.txt", "텍스트 파일 (*.txt);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write("행사 참여자 이벤트 추첨 결과\n")
                    file.write("======================\n\n")
                    file.write(f"추첨 일시: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    file.write(f"참석자 수: {len(self.participants)}명\n")
                    file.write(f"당첨자 수: {len(self.winners)}명\n\n")
                    file.write("당첨자 명단:\n")
                    for i, winner in enumerate(self.winners, 1):
                        file.write(f"{i}. {winner}\n")
                
                QMessageBox.information(self, "저장 완료", "추첨 결과가 저장되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "저장 오류", f"결과를 저장하는 중 오류가 발생했습니다: {str(e)}")
    
    def closeEvent(self, event):
        """앱 종료 시 서버 프로세스 종료"""
        if self.server_process:
            self.server_process.terminate()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # 애플리케이션 스타일 설정
    app.setStyle("Fusion")
    
    window = LotteryApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 