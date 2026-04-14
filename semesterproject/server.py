import socket
from threading import Thread, Timer
import random   
from queue import Queue
from protocol import Message, MessageTransfer, cmd


class Game:
    def __init__(self, room, rounds=3, drawing_time=180): 
        self.room = room 
        self.rounds = rounds 
        self.current_round = 0
        self.drawing_time = drawing_time
        self.themes = self.get_themes()
        self.drawings = {} 
        self.state = "waiting"
        self.viewing_time = 30

    def get_themes(self):
        return [
            "Earth", "Angel", "Food", "Animal", "Space", "Expression", "Horror", "Paranormal",
            "Mythology", "Jellyfish", "Trainstation", "Seasons (Winter etc.)", "Underwater",
            "Free style", "Landscape", "Demonic", "Wizard", "Any Object", 
        ]

    def start_game(self):
        self.current_round = 0
        self.room.broadcast(
            Message(cmd.GAME_START.value, {
                "players": [client.username for client in self.room.clients],
                "total_rounds": self.rounds},
            "Server", None))
        self.start_round()

    def start_round(self):
        self.current_round += 1
        if self.current_round > self.rounds:
            self.end_game()
            return
        self.drawings = {}
        self.state = "drawing"
        theme = random.choice(self.themes)
        self.room.broadcast(
            Message(cmd.GAME_THEME.value, {
                'round': self.current_round,
                'total_rounds': self.rounds,
                'theme': theme,
                'time': self.drawing_time},
            "Server", None))
        Timer(self.drawing_time, self.start_viewing).start()

    def submit_drawing(self, client, drawing_data):
        if self.state == "drawing":
            self.drawings[client.username] = drawing_data
            self.room.broadcast(
                Message(cmd.CHAT.value, f"{client.username} submitted their drawing!", "Server", None)
            )
            if len(self.drawings) == len(self.room.clients):
                self.start_viewing()

    def start_viewing(self):
        if self.state != "drawing":
            return 
        self.state = "viewing"
        viewing_data = {
            'drawings': self.drawings,
            'players': list(self.drawings),
            'viewing_time': self.viewing_time
        }
        self.room.broadcast(Message(cmd.GAME_VIEW.value, viewing_data, "Server", None))
        Timer(self.viewing_time, self.start_round).start()

    def end_game(self):  
        final_results = {
            'drawings': self.drawings,
            'total_rounds': self.rounds
        }
        self.room.broadcast(Message(cmd.GAME_END.value, final_results, "Server", None))
        self.room.game = None


class Room:
    def __init__(self, name, host=None, max_players=6):
        self.name = name
        self.host = host
        self.clients = []
        if host:
            self.clients.append(host)
        self.max_players = max_players
        self.game = None

    def add_client(self, client) -> bool:
        if client in self.clients:
            return True
        if len(self.clients) >= self.max_players:
            return False
        self.clients.append(client)
        if client.current_room != self.name:
            client.current_room = self.name
        return True

    def remove_client(self, client   ):
        if client in self.clients:
            self.clients.remove(client)
            was_host = (client == self.host)
            if was_host and self.clients:
                self.host = self.clients[0]
                room_info = self.get_info()
                self.broadcast(Message(cmd.ROOM_INFO.value, room_info, "Server", None))
            elif not self.clients:
                self.host = None
            return True, was_host
        return False, False

    def broadcast(self, message, except_client=None):
        for client in self.clients[:]:
            if client != except_client:
                try:
                    client.send(message)
                except:
                    self.remove_client(client)

    def get_info(self):
        return {
            'name': self.name,
            'players': [client.username for client in self.clients],
            'player_count': len(self.clients),
            'max_players': self.max_players,
            'host': self.host.username if self.host else None,
            'in_game': self.game is not None
        }


class RoomController:
    def __init__(self):
        self.rooms = {}
        self.rooms['lobby'] = Room('lobby', None, 100)

    def create_room(self, host, room_name, max_players=6, drawing_time=180):
        if room_name in self.rooms:
            return False
        room = Room(room_name, host, max_players)
        room.drawing_time = drawing_time
        self.rooms[room_name] = room
        host.current_room = room_name
        return True

    def join_room(self, client, room_name):
        if room_name not in self.rooms:
            return False
        room = self.rooms[room_name]

        if client in room.clients:
            return True

        if client.current_room and client.current_room != room_name:
            self.leave_current_room(client)

        if room.add_client(client):
            client.current_room = room_name
            room_info = room.get_info()
            room.broadcast(Message(cmd.ROOM_INFO.value, room_info, "Server", None))
            room.broadcast(Message(cmd.CHAT.value, f"{client.username} joined the room", "Server", None))
            self.broadcast_lobby_update()
            return True
        return False

    def leave_current_room(self, client):
        if not client.current_room or client.current_room not in self.rooms:
            client.current_room = 'lobby'
            if client not in self.rooms['lobby'].clients:
                self.rooms['lobby'].add_client(client)
            return False

        room_name = client.current_room
        if room_name == 'lobby':
            return False

        room = self.rooms[room_name]
        removed, was_host = room.remove_client(client)
        if removed:
            if client not in self.rooms['lobby'].clients:
                self.rooms['lobby'].add_client(client)
            client.current_room = 'lobby'
            room.broadcast(Message(cmd.CHAT.value, f"{client.username} left the room", "Server", None))
            if len(room.clients) == 0:
                del self.rooms[room_name]
            self.broadcast_lobby_update()
            return True
        return False

    def broadcast_lobby_update(self):
        rooms_info = self.get_available_rooms()
        lobby_msg = Message(cmd.LOBBY_LIST.value, rooms_info, "Server", None)
        for client in self.rooms['lobby'].clients:
            try:
                client.send(lobby_msg)
            except:
                pass


    def get_available_rooms(self):
        rooms_info = []
        for name, room in self.rooms.items():
            if name != 'lobby':
                rooms_info.append(room.get_info())
        return rooms_info


class ClientHandler(Thread):
    def __init__(self, sock, addr, msg_queue, room_controller):
        super().__init__()
        self.sock = sock
        self.addr = addr
        self.msg_queue = msg_queue
        self.room_controller = room_controller
        self.transport = MessageTransfer(sock)
        self.username = None
        self.current_room = None
        self.daemon = True

    def run(self):
        welcome_msg = Message(cmd.CONNECT.value, "Connected to Drawing Game Server", "Server", None)
        self.send(welcome_msg)
        try:
            while True:
                msg = self.transport.receive_msg()
                if not msg:
                    break
                if msg.type == cmd.SIGNUP.value:
                    self.msg_queue.put((msg, self))
                else:
                    self.msg_queue.put((msg, self))
        except Exception:
            pass
        finally:
            self.disconnect()

    def send(self, msg):
        try:
            return self.transport.send_msg(msg)
        except Exception:
            self.disconnect()
            return False

    def disconnect(self):
        self.room_controller.leave_current_room(self)
        try:
            self.sock.close()
        except:
            pass


class MessageHandler(Thread):
    def __init__(self, msg_queue, room_controller):
        super().__init__()
        self.msg_queue = msg_queue
        self.room_controller = room_controller
        self.daemon = True

    def run(self):
        while True:
            msg, sender = self.msg_queue.get()
            self.handle_message(msg, sender)

    def handle_message(self, msg, sender):
        if msg.type == cmd.SIGNUP.value:
            self.handle_signup(msg, sender)
        elif msg.type == cmd.LOBBY_CREATE.value:
            self.handle_lobby_create(msg, sender)
        elif msg.type == cmd.LOBBY_JOIN.value:
            self.handle_lobby_join(msg, sender)
        elif msg.type == cmd.LOBBY_LEAVE.value:
            self.handle_lobby_leave(sender)
        elif msg.type == cmd.LOBBY_LIST.value:
            self.handle_lobby_list(sender)
        elif msg.type == cmd.CHAT.value:
            self.handle_chat(msg, sender)
        elif msg.type == cmd.GAME_START.value:
            self.handle_game_start(sender)
        elif msg.type == cmd.GAME_SUBMIT.value:
            self.handle_game_submit(msg, sender)


    def handle_signup(self, msg, sender):
        username = msg.data
        for room in self.room_controller.rooms.values():
            for client in room.clients:
                if client != sender and client.username == username.strip():
                    sender.send(Message(cmd.SIGNUP_ERROR.value, "Username taken", "Server", None))
                    return
                
        sender.username = username.strip()
        sender.current_room = 'lobby'
        self.room_controller.rooms['lobby'].add_client(sender)
        sender.send(Message(cmd.SIGNUP_SUCCESS.value, f"Welcome {sender.username}!", "Server", sender.username))
        rooms_info = self.room_controller.get_available_rooms() 
        sender.send(Message(cmd.LOBBY_LIST.value, rooms_info, "Server", None))
        current_room = self.room_controller.rooms.get(sender.current_room)
        if current_room:
            current_room.broadcast(Message(cmd.CHAT.value, f"{sender.username} joined", "Server", None))

    def handle_lobby_create(self, msg, sender):
        try:
            lobby_data = msg.data
            name = lobby_data['name']
            max_players = lobby_data.get('max_players', 6)
            drawing_time = lobby_data.get('drawing_time', 180)
            
            if self.room_controller.create_room(sender, name, max_players, drawing_time):
                sender.send(Message(cmd.LOBBY_CREATE.value, f"Created {name}", "Server", sender.username))
                room_info = self.room_controller.rooms[name].get_info()
                self.room_controller.rooms[name].broadcast(Message(cmd.ROOM_INFO.value, room_info, "Server", None))
                self.room_controller.rooms[name].broadcast(Message(cmd.CHAT.value, f"{sender.username} created the room", "Server", None))

                self.room_controller.broadcast_lobby_update()
            else:
                sender.send(Message(cmd.ERROR.value, "Room name exists", "Server", sender.username))
        except Exception:
            sender.send(Message(cmd.ERROR.value, "Invalid create data", "Server", sender.username))

    def handle_lobby_join(self, msg, sender):
        try:
            join_data = msg.data
            room_name = join_data['name']
            if self.room_controller.join_room(sender, room_name):
                sender.send(Message(cmd.LOBBY_JOIN.value, f"Joined {room_name}", "Server", sender.username))
                self.room_controller.broadcast_lobby_update()
            else:
                sender.send(Message(cmd.ERROR.value, f"Cannot join {room_name}", "Server", sender.username))
        except:
            sender.send(Message(cmd.ERROR.value, "Invalid join data", "Server", sender.username))

    def handle_lobby_leave(self, sender):
        if sender.current_room and sender.current_room != 'lobby':
            self.room_controller.leave_current_room(sender)
            sender.send(Message(cmd.LOBBY_LEAVE.value, "Left room", "Server", sender.username))
        else:
            sender.send(Message(cmd.LOBBY_LEAVE.value, "Not in a room", "Server", sender.username))

    def handle_lobby_list(self, sender):
        self.room_controller.broadcast_lobby_update()

    def handle_chat(self, msg, sender):
        if sender.current_room and sender.current_room in self.room_controller.rooms:
            room = self.room_controller.rooms[sender.current_room]
            room.broadcast(
                Message(cmd.CHAT.value, f"{sender.username}: {msg.data}", sender.username, None),
                except_client=None
            )

    def handle_game_start(self, sender):
        if sender.current_room and sender.current_room in self.room_controller.rooms:
            room = self.room_controller.rooms[sender.current_room]
            if room.host == sender and not room.game and len(room.clients) >= 2:
                drawing_time = getattr(room, 'drawing_time', 180)
                room.game = Game(room, rounds=3, drawing_time=drawing_time)
                room.game.start_game()
            else:
                error_msg = "Cannot start game: "
                if room.host != sender:
                    error_msg += "Only host can start the game"
                elif room.game:
                    error_msg += "Game already in progress"
                elif len(room.clients) < 2:
                    error_msg += "Need at least 2 players to start"
                sender.send(Message(cmd.ERROR.value, error_msg, "Server", sender.username))
        else:
            error_msg = "Not in a valid room"
            sender.send(Message(cmd.ERROR.value, error_msg, "Server", sender.username))

    def handle_game_submit(self, msg, sender):
        if sender.current_room in self.room_controller.rooms:
            room = self.room_controller.rooms[sender.current_room]
            if room.game:
                room.game.submit_drawing(sender, msg.data)


class Server(Thread):
    def __init__(self, address='127.0.0.1', port=9000):
        super().__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((address, port))
        self.sock.listen()
        self.msg_queue = Queue()
        self.room_controller = RoomController()
        self.broadcaster = MessageHandler(self.msg_queue, self.room_controller)
        self.broadcaster.start()

    def run(self):
        while True:
            try:
                client_sock, client_addr = self.sock.accept()
                client_handler = ClientHandler(client_sock, client_addr, self.msg_queue, self.room_controller)
                client_handler.start()
            except Exception as error:
                break

if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        pass