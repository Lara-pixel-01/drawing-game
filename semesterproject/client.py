import socket
import threading
from protocol import Message, MessageTransfer, cmd

class Client:
    def __init__(self, host='127.0.0.1', port=9000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.transport = MessageTransfer(self.sock)
        self.username = None
        self.current_room = None
        self.running = True
        
        self.on_disconnected = None
        self.on_message_received = None
        self.on_lobby_list_updated = None
        
    def start(self):
        self.network_thread = threading.Thread(target=self._network_loop, daemon=True)
        self.network_thread.start()
    
    def _network_loop(self):
        while self.running: 
            try:
                msg = self.transport.receive_msg()
                if not msg:
                    self._handle_disconnect()
                    break
                    
                self._handle_message(msg)
                
            except Exception as error:
                print(f"Network error: {error}")
                self._handle_disconnect()
                break
    
    def _handle_message(self, msg):
        if msg.type == cmd.SIGNUP_SUCCESS.value:
            self.username = msg.target
            
        elif msg.type == cmd.LOBBY_LIST.value:
            if self.on_lobby_list_updated:
                self.on_lobby_list_updated(msg.data)

        if self.on_message_received:
            self.on_message_received(msg)
    
    def _handle_disconnect(self):
        self.running = False
        if self.on_disconnected:
            self.on_disconnected("Disconnected from server")
    
    def signup(self, username):
        self.send(Message(cmd.SIGNUP.value, username, self.username, None))
    
    def create_room(self, room_name, max_players=6, drawing_time=180):
        data = {
            'name': room_name,
            'max_players': max_players,
            'drawing_time': drawing_time
        }
        self.send(Message(cmd.LOBBY_CREATE.value, data, self.username, None))
    
    def join_room(self, room_name):
        data = {'name': room_name}
        self.send(Message(cmd.LOBBY_JOIN.value, data, self.username, None))
    
    def leave_room(self):
        self.send(Message(cmd.LOBBY_LEAVE.value, None, self.username, None))
    
    def request_room_list(self):
        self.send(Message(cmd.LOBBY_LIST.value, None, self.username, None))
    
    def send_chat_message(self, message):
        self.send(Message(cmd.CHAT.value, message, self.username, None))
    
    def start_game(self):
        self.send(Message(cmd.GAME_START.value, None, self.username, None))
    
    def submit_drawing(self, drawing_data):
        self.send(Message(cmd.GAME_SUBMIT.value, drawing_data, self.username, None))
    
    def send(self, msg):
        if self.running:
            try:
                return self.transport.send_msg(msg)
            except Exception as error:
                print(f"Send error: {error}")
                self._handle_disconnect()
        return False
    
    def disconnect(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass