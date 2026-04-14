import pickle
from enum import Enum
from datetime import datetime

class cmd(Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    SIGNUP = "sign_up"
    SIGNUP_SUCCESS = "signup_success"
    SIGNUP_ERROR = "signup_error"
    LOBBY_CREATE = "lobby_create"
    LOBBY_JOIN = "lobby_join"
    LOBBY_LEAVE = "lobby_leave"
    LOBBY_LIST = "lobby_list"
    GAME_START = "game_start"
    GAME_THEME = "game_theme"
    GAME_SUBMIT = "game_submit"
    GAME_VIEW = "game_view"
    GAME_END = "game_end"
    CHAT = "chat"
    ERROR = "error"
    ROOM_INFO ="room_info"
    
class Message:
    def __init__(self, msg_type, data=None, from_user=None, target=None):
        self.type = msg_type
        self.data = data
        self.from_user = from_user
        self.target = target
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self):
        return {
            'type': self.type,
            'data': self.data,
            'from_user': self.from_user,
            'target': self.target,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, dct):
        return cls(
            dct['type'], 
            dct.get('data'), 
            dct.get('from_user'), 
            dct.get('target')
        )

class MessageTransfer:
    def __init__(self, sock):
        self.sock = sock
    
    def send_msg(self, msg):
        try:
            msg_bytes = pickle.dumps(msg.to_dict())
            length = len(msg_bytes)
            header = f"{length:010d}".encode('utf-8')
            self.sock.sendall(header + msg_bytes)
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def receive_msg(self):
        try:
            header = b''
            while len(header) < 10:
                chunk = self.sock.recv(10 - len(header))
                if not chunk:
                    return None
                header += chunk
            
            length = int(header.decode('utf-8'))
            
            data = b''
            while len(data) < length:
                chunk = self.sock.recv(min(4096, length - len(data)))
                if not chunk:
                    return None
                data += chunk
            
            return Message.from_dict(pickle.loads(data))
            
        except Exception as error:
            print(f"Receive error: {error}")
            return None