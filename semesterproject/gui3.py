import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from client import Client
from drawing_canvas import DrawingGUI, ViewingScreen


class ClientThread(QThread):
    message_received = pyqtSignal(object)
    disconnected = pyqtSignal(str)
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.client = None
        self.running = True
    
    def run(self):
        try:
            self.client = Client(self.host, self.port)
            self.client.on_message_received = lambda msg: self.message_received.emit(msg)
            self.client.on_disconnected = lambda reason: self.disconnected.emit(reason)
            self.client.start()
            while self.running:
                QThread.msleep(100)
        except Exception as e:
            self.disconnected.emit(str(e))
    
    def stop(self):
        self.running = False
        if self.client:
            self.client.disconnect()


class DrawingGame(QMainWindow):
    def __init__(self):
        super().__init__()
        self.username = None
        self.current_room = None
        self.is_host = False
        self.client_thread = None
        self.rooms = []
        
        self.setup_ui()
        self.setup_client()
        self.show_username_dialog()
    
    def setup_ui(self):
        self.setWindowTitle("Drawing Game")
        self.setFixedSize(1000, 700)
        self.setStyleSheet("background: #2D2B55; color: white;")
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        self.setup_chat_area()
        layout.addWidget(self.chat_widget)

        self.setup_controls_area()
        layout.addWidget(self.controls_widget)
    
    def setup_chat_area(self):
        self.chat_widget = QWidget()
        self.chat_widget.setFixedWidth(600)
        
        layout = QVBoxLayout(self.chat_widget)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            background: #1E1B3B; 
            color: white; 
            border: 2px solid #B55CC0; 
            border-radius: 10px; 
            padding: 10px;
        """)
        layout.addWidget(self.chat_display)
        
        chat_input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message...")
        self.chat_input.setStyleSheet("""
            background: #1E1B3B; 
            color: white; 
            border: 2px solid #B55CC0; 
            border-radius: 5px; 
            padding: 8px;
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        chat_input_layout.addWidget(self.chat_input)
        
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("""
            QPushButton {
                background: #B55CC0; 
                color: white; 
                border: none; 
                border-radius: 5px; 
                padding: 8px 15px;
            }
            QPushButton:hover { background: #9A4AA5; }
        """)
        send_btn.clicked.connect(self.send_chat_message)
        chat_input_layout.addWidget(send_btn)
        
        layout.addLayout(chat_input_layout)
    
    def setup_controls_area(self):
        self.controls_widget = QWidget()
        self.controls_widget.setFixedWidth(300)
        
        layout = QVBoxLayout(self.controls_widget)
        layout.setSpacing(15)
        user_label = QLabel("User: Not connected")
        user_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #B55CC0;")
        layout.addWidget(user_label)
        self.user_label = user_label
        room_label = QLabel("Room: Lobby")
        room_label.setStyleSheet("font-size: 14px; color: #B55CC0;")
        layout.addWidget(room_label)
        self.room_label = room_label
        
        layout.addSpacing(20)

        create_btn = QPushButton("Create Room")
        create_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 12px; 
                font-size: 14px;
            }
            QPushButton:hover { background: #45A049; }
        """)
        create_btn.clicked.connect(self.show_create_room_dialog)
        layout.addWidget(create_btn)
        
        join_btn = QPushButton("Join Room")
        join_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 12px; 
                font-size: 14px;
            }
            QPushButton:hover { background: #1976D2; }
        """)
        join_btn.clicked.connect(self.show_join_room_dialog)
        layout.addWidget(join_btn)

        self.start_btn = QPushButton("Start Game")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #FF9800; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 12px; 
                font-size: 14px;
            }
            QPushButton:hover { background: #F57C00; }
            QPushButton:disabled { background: #666; }
        """)
        self.start_btn.clicked.connect(self.start_game)
        self.start_btn.hide()
        layout.addWidget(self.start_btn)

        self.leave_btn = QPushButton("Leave Room")
        self.leave_btn.setStyleSheet("""
            QPushButton {
                background: #F44336; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 12px; 
                font-size: 14px;
            }
            QPushButton:hover { background: #D32F2F; }
        """)
        self.leave_btn.clicked.connect(self.leave_room)
        self.leave_btn.hide()
        layout.addWidget(self.leave_btn)

        players_label = QLabel("Players in Room:")
        players_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(players_label)
        
        self.players_list = QListWidget()
        self.players_list.setStyleSheet("""
            background: #1E1B3B; 
            color: white; 
            border: 2px solid #B55CC0; 
            border-radius: 8px;
        """)
        layout.addWidget(self.players_list)
        
        layout.addStretch()
    
    def setup_client(self):
        self.client_thread = ClientThread('127.0.0.1', 9000)
        self.client_thread.message_received.connect(self.handle_message)
        self.client_thread.disconnected.connect(self.handle_disconnect)
        self.client_thread.start()
    
    def show_username_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Enter Username")
        dialog.setFixedSize(300, 150)
        dialog.setStyleSheet("background: #2D2B55; color: white;")
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Choose your username:"))
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username...")
        self.username_input.setStyleSheet("background: white; color: black; padding: 5px;")
        layout.addWidget(self.username_input)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet("background: #B55CC0; color: white; padding: 8px;")
        ok_btn.clicked.connect(lambda: self.handle_username_submit(dialog))
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def handle_username_submit(self, dialog):
        username = self.username_input.text().strip()
        if username and len(username) >= 2:
            self.client_thread.client.signup(username)
            dialog.close()
        else:
            QMessageBox.warning(self, "Error", "Username must be at least 2 characters")
    
    def show_create_room_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Room")
        dialog.setFixedSize(300, 250)
        dialog.setStyleSheet("background: #2D2B55; color: white;")
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Room Name:"))
        room_name_input = QLineEdit()
        room_name_input.setStyleSheet("background: white; color: black; padding: 5px;")
        layout.addWidget(room_name_input)
        
        layout.addWidget(QLabel("Max Players:"))
        players_combo = QComboBox()
        players_combo.addItems(["2", "3", "4", "5", "6"])
        players_combo.setStyleSheet("background: white; color: black;")
        layout.addWidget(players_combo)
        
        layout.addWidget(QLabel("Drawing Time:"))
        time_combo = QComboBox()
        time_options = [
            ("1 minute", 60),
            ("3 minutes", 180),
            ("5 minutes", 300),
            ("10 minutes", 600),
            ("30 minutes", 1800),
            ("1 hour", 3600),
            ("5 hours", 18000)
        ]
        for display_text, seconds in time_options:
            time_combo.addItem(display_text, seconds)
        time_combo.setCurrentIndex(1)
        time_combo.setStyleSheet("background: white; color: black;")
        layout.addWidget(time_combo)
        
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
        create_btn.setStyleSheet("background: #4CAF50; color: white; padding: 8px;")
        create_btn.clicked.connect(lambda: self.create_room(
            room_name_input.text().strip(), 
            int(players_combo.currentText()),
            time_combo.currentData(),
            dialog
        ))
        btn_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background: #666; color: white; padding: 8px;")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec()

    def create_room(self, name, max_players, drawing_time, dialog):
        if not name:
            QMessageBox.warning(self, "Error", "Room name cannot be empty")
            return
        
        self.client_thread.client.create_room(name, max_players, drawing_time)
        dialog.close()
        
    
    def show_join_room_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Join Room")
        dialog.setFixedSize(400, 300)
        dialog.setStyleSheet("background: #2D2B55; color: white;")
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Available Rooms:"))
        
        self.rooms_list = QListWidget()
        self.rooms_list.setStyleSheet("background: white; color: black;")
        layout.addWidget(self.rooms_list)

        btn_layout = QHBoxLayout()
        join_btn = QPushButton("Join Selected")
        join_btn.setStyleSheet("background: #4CAF50; color: white; padding: 8px;")
        join_btn.clicked.connect(lambda: self.join_selected_room(dialog))
        btn_layout.addWidget(join_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background: #666; color: white; padding: 8px;")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.refresh_rooms()
        dialog.exec()
    
    def refresh_rooms(self):
        if self.client_thread and self.client_thread.client:
            self.client_thread.client.request_room_list()
    
    def join_selected_room(self, dialog):
        selected = self.rooms_list.currentItem()
        if selected:
            room_name = selected.text().split(" (")[0]
            self.client_thread.client.join_room(room_name)
            dialog.close()
        else:
            QMessageBox.warning(self, "Error", "Please select a room")
    
    def start_game(self):
        if self.client_thread and self.client_thread.client:
            self.client_thread.client.start_game()
    
    def leave_room(self):
        if self.client_thread and self.client_thread.client:
            self.client_thread.client.leave_room()
    
    def return_to_lobby(self):
        self.current_room = None
        self.is_host = False
        self.room_label.setText("Room: Lobby")
        self.start_btn.hide()
        self.leave_btn.hide()
        self.players_list.clear()
        self.chat_display.clear()
        self.add_chat_message("Returned to lobby")
        self.refresh_rooms()
    
    def send_chat_message(self):
        msg = self.chat_input.text().strip()
        if msg and self.client_thread and self.client_thread.client:
            self.client_thread.client.send_chat_message(msg)
            self.chat_input.clear()
    
    def add_chat_message(self, text):
        self.chat_display.append(text)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def handle_message(self, msg):
        msg_type = msg.type.lower() if hasattr(msg.type, 'lower') else msg.type
        
        if msg_type == "chat":
            self.add_chat_message(msg.data)
        
        elif msg_type == "signup_success":
            self.username = msg.target
            self.user_label.setText(f"User: {self.username}")
            self.add_chat_message(f"Welcome {self.username}!")

        elif msg_type == "lobby_list":
            self.rooms = msg.data
            if hasattr(self, 'rooms_list') and self.rooms_list is not None:
                try:
                    self.rooms_list.clear()
                    for room in msg.data:
                        room_text = f"{room['name']} ({room['player_count']}/{room['max_players']})"
                        if room['in_game']:
                            room_text += " 🎮"
                        self.rooms_list.addItem(room_text)
                except RuntimeError:
                    self.rooms_list = None
        
        elif msg_type == "lobby_create":
            self.add_chat_message(f"Created room: {msg.data}")
        
        elif msg_type == "lobby_join":
            self.add_chat_message(f"Joined room: {msg.data}")
            self.current_room = msg.data
            self.room_label.setText(f"Room: {self.current_room}")
            self.start_btn.show()
            self.leave_btn.show()
            self.chat_display.clear()
        
        elif msg_type == "room_info":
            if isinstance(msg.data, dict):
                players = msg.data.get('players', [])
                host_name = msg.data.get('host')
                
                self.players_list.clear()
                for player in players:
                    item_text = player
                    if player == host_name:
                        item_text += " 👑" 
                    self.players_list.addItem(item_text)

                self.is_host = (host_name == self.username)
                self.start_btn.setEnabled(self.is_host and len(players) >= 2)
                if self.is_host:
                    self.start_btn.setToolTip("Start the game")
                else:
                    self.start_btn.setToolTip("Only the host can start the game")
        
        elif msg_type == "game_start":
            self.add_chat_message("Game started! Get ready to draw...")
        
        elif msg_type == "game_view":
            self.add_chat_message("Viewing phase started! Showing all drawings...")
            self.show_viewing_screen(msg.data)
        
        elif msg_type == "game_theme":
            self.add_chat_message(f"Drawing round started! Theme: {msg.data.get('theme', 'Unknown')}")
            self.show_drawing_screen(msg.data)
        
        elif msg_type == "lobby_leave":
            self.add_chat_message(msg.data)
            if "left" in msg.data.lower():
                self.return_to_lobby()
        
        elif msg_type == "error":
            QMessageBox.warning(self, "Error", msg.data)
            self.add_chat_message(f"Error: {msg.data}")
    
    def show_drawing_screen(self, game_data):
        try:
            self.drawing_gui = DrawingGUI(self, game_data)
            self.drawing_gui.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load drawing: {e}")

    def show_viewing_screen(self, viewing_data):
        try:
            self.viewing_gui = ViewingScreen(self, viewing_data)
            self.viewing_gui.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load viewing screen: {e}")
    
    def handle_disconnect(self, reason):
        self.add_chat_message(f"Disconnected: {reason}")
        QMessageBox.critical(self, "Disconnected", f"Connection lost: {reason}")
    
    def closeEvent(self, event):
        if self.client_thread:
            self.client_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DrawingGame()
    window.show()
    sys.exit(app.exec())