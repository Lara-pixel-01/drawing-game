# Multiplayer Drawing Game

A real-time multiplayer drawing game where players draw based on themes and view each other's artwork at the end of the round. Built with Python, PyQt6, sockets and threading.

Features

- Create or join game rooms
- Real-time chat
- Host-controlled game start
- Timed drawing rounds
- Custom drawing canvas with brush size and color picker
- Viewing phase to see all submitted drawings

Tech Stack

- Python
- PyQt6 (GUI)
- Sockets (Networking)
- Threading (Concurrent clients)
- Pickle (Message serialization)

Game Flow

1. Host creates a room and sets max players/drawing time
2. Players join the room
3. Host starts the game
4. Each round, players draw based on a random theme
5. After time ends, all drawings are displayed for viewing
6. Game continues for multiple rounds

How to Run:

1. Install dependencies:
   - pip install PyQt6
2. Run server.py
3. Run gui3.py on a new terminal
