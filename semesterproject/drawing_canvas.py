import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import base64

class DrawingCanvas(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: white; border: 2px solid #B55CC0; border-radius: 8px;")
        self.setMinimumSize(800, 600)
        self.pixmap = QPixmap(800, 600)
        self.pixmap.fill(Qt.GlobalColor.white)
        self.setPixmap(self.pixmap)
        
        self.last_point = QPoint()
        self.drawing = False 
        self.pen_color = QColor(Qt.GlobalColor.black)
        self.pen_width = 5
        self.current_tool = "brush"
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            
    def mouseMoveEvent(self, event):
        if self.drawing and (event.buttons() & Qt.MouseButton.LeftButton):
            painter = QPainter(self.pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            if self.current_tool == "brush":
                painter.setPen(QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            else:  
                painter.setPen(QPen(Qt.GlobalColor.white, self.pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.setPixmap(self.pixmap)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            
    def clear(self):
        self.pixmap.fill(Qt.GlobalColor.white)
        self.setPixmap(self.pixmap)
        
    def set_pen_color(self, color):
        self.pen_color = color
        
    def set_pen_width(self, width):
        self.pen_width = width
        
    def set_tool(self, tool):
        self.current_tool = tool
        
    def get_data(self):
        try:
            qimage = self.pixmap.toImage()
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
            qimage.save(buffer, "PNG")
            data = buffer.data()
            base64_data = base64.b64encode(data).decode('utf-8')
            return base64_data
        except Exception:
            return None

class DrawingGUI(QMainWindow):
    def __init__(self, parent, game_data):
        super().__init__(parent)
        self.parent = parent
        self.game_data = game_data
        self.time_left = game_data.get('time', 180)
        self.theme = game_data.get('theme', 'Unknown')
        self.round = game_data.get('round', 1)
        self.total_rounds = game_data.get('total_rounds', 3)
        self.canvas = DrawingCanvas()
        
        self.setup_ui()
        self.start_timer()
        
    def setup_ui(self):
        self.setWindowTitle(f"Drawing Canvas - Round {self.round}/{self.total_rounds}")
        self.setFixedSize(1000, 800)
        self.setStyleSheet("background: #2D2B55; color: white;")
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setup_tools_panel()
        layout.addWidget(self.tools_widget)
        self.setup_canvas_area()
        layout.addWidget(self.canvas_widget)
        
    def setup_tools_panel(self):
        self.tools_widget = QWidget()
        self.tools_widget.setFixedWidth(200)
        self.tools_widget.setStyleSheet("""
            background: #1E1B3B; 
            border: 2px solid #B55CC0; 
            border-radius: 10px; 
            padding: 15px;
        """)
        
        layout = QVBoxLayout(self.tools_widget)
        layout.setSpacing(15)

        title = QLabel("🎨 Drawing Tools")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #B55CC0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)

        tools_label = QLabel("Tools:")
        tools_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(tools_label)

        tools_buttons_layout = QHBoxLayout()
        
        brush_btn = QPushButton("🖌️ Brush")
        brush_btn.setCheckable(True)
        brush_btn.setChecked(True)
        brush_btn.setStyleSheet("""
            QPushButton {
                background: #B55CC0; 
                color: white; 
                border: none; 
                border-radius: 5px; 
                padding: 8px;
            }
            QPushButton:checked {
                background: #9A4AA5; 
                border: 2px solid white;
            }
            QPushButton:hover { background: #9A4AA5; }
        """)
        brush_btn.clicked.connect(lambda: self.canvas.set_tool("brush"))
        
        eraser_btn = QPushButton("🧽 Eraser")
        eraser_btn.setCheckable(True)
        eraser_btn.setStyleSheet("""
            QPushButton {
                background: #666; 
                color: white; 
                border: none; 
                border-radius: 5px; 
                padding: 8px;
            }
            QPushButton:checked {
                background: #555; 
                border: 2px solid white;
            }
            QPushButton:hover { background: #555; }
        """)
        eraser_btn.clicked.connect(lambda: self.canvas.set_tool("eraser"))
        
        tools_buttons_layout.addWidget(brush_btn)
        tools_buttons_layout.addWidget(eraser_btn)
        layout.addLayout(tools_buttons_layout)

        brush_btn.toggled.connect(lambda checked: eraser_btn.setChecked(not checked))
        eraser_btn.toggled.connect(lambda checked: brush_btn.setChecked(not checked))
        
        layout.addSpacing(10)
    
        colors_label = QLabel("Colors:")
        colors_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(colors_label)
    
        self.current_color_display = QLabel()
        self.current_color_display.setFixedSize(60, 60)
        self.current_color_display.setStyleSheet(f"""
            background: {self.canvas.pen_color.name()};
            border: 3px solid white;
            border-radius: 30px;
        """)
        self.current_color_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_color_display.setToolTip(f"Current color: {self.canvas.pen_color.name()}")
        layout.addWidget(self.current_color_display)
        
        color_picker_btn = QPushButton("🎨 Open Color Picker")
        color_picker_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { 
                background: #1976D2; 
                border: 1px solid white;
            }
        """)
        color_picker_btn.clicked.connect(self.open_color_picker)
        layout.addWidget(color_picker_btn)
        
        layout.addSpacing(10)
        
        size_label = QLabel("Brush Size:")
        size_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(size_label)
        
        size_buttons_layout = QHBoxLayout()
        sizes = [("S", 3), ("M", 8), ("L", 15), ("XL", 25)]
        
        for size_name, size in sizes:
            btn = QPushButton(size_name)
            btn.setFixedSize(35, 35)
            btn.setStyleSheet("""
                QPushButton {
                    background: #B55CC0; 
                    color: white; 
                    border: none; 
                    border-radius: 17px;
                    font-weight: bold;
                }
                QPushButton:hover { background: #9A4AA5; }
            """)
            btn.clicked.connect(lambda _, s=size: self.canvas.set_pen_width(s))
            size_buttons_layout.addWidget(btn)
            
        layout.addLayout(size_buttons_layout)
        
        layout.addSpacing(20)
        
        clear_btn = QPushButton("🔄 Clear Canvas")
        clear_btn.setStyleSheet("""
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
        clear_btn.clicked.connect(self.canvas.clear)
        layout.addWidget(clear_btn)
        
        submit_btn = QPushButton("✅ Submit Drawing")
        submit_btn.setStyleSheet("""
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
        submit_btn.clicked.connect(self.submit)
        layout.addWidget(submit_btn)
        
        layout.addStretch()
        
    def open_color_picker(self):
        color = QColorDialog.getColor(
            self.canvas.pen_color, 
            self, 
            "Choose Drawing Color",
            QColorDialog.ColorDialogOption.DontUseNativeDialog
        )
        
        if color.isValid():
            self.canvas.set_pen_color(color)
            self.current_color_display.setStyleSheet(f"""
                background: {color.name()};
                border: 3px solid white;
                border-radius: 30px;
            """)
            self.current_color_display.setToolTip(f"Current color: {color.name()}")
        
    def setup_canvas_area(self):
        self.canvas_widget = QWidget()
        
        layout = QVBoxLayout(self.canvas_widget)
        layout.setSpacing(15)

        info_layout = QHBoxLayout()
        
        theme_label = QLabel(f"🎨 Theme: {self.theme}")
        theme_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #B55CC0;")
        info_layout.addWidget(theme_label)
        
        round_label = QLabel(f"📘 Round: {self.round}/{self.total_rounds}")
        round_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF9800;")
        info_layout.addWidget(round_label)
        
        self.timer_label = QLabel(f"⏰ Time: {self.format_time(self.time_left)}")
        self.timer_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF9800;")
        info_layout.addWidget(self.timer_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        layout.addWidget(self.canvas)
    
    def format_time(self, seconds):
        if seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def start_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
    def update_timer(self):
        self.time_left -= 1
        self.timer_label.setText(f"⏰ Time: {self.format_time(self.time_left)}")
        
        if self.time_left <= 0:
            self.timer.stop()
            self.submit()
            
    def submit(self):
        try:
            self.timer.stop()
            drawing_data = self.canvas.get_data()
            if drawing_data and getattr(self.parent, 'client_thread', None):
                self.parent.client_thread.client.submit_drawing(drawing_data)
        except Exception:
            pass
        finally:
            self.close()
                
    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()

class ViewingScreen(QMainWindow):
    def __init__(self, parent, viewing_data):
        super().__init__(parent)
        self.parent = parent
        self.viewing_data = viewing_data
        self.current_drawing_index = 0
        self.drawings = viewing_data.get('drawings', {})
        self.players = list(self.drawings.keys())  

        self.time_left = viewing_data.get('viewing_time', 15)
        
        self.setup_ui()
        self.start_timer()
        self.show_current_drawing()
        
    def setup_ui(self):
        self.setWindowTitle(f"Viewing Drawings - {len(self.players)} Submissions")
        self.setFixedSize(800, 700)
        self.setStyleSheet("background: #2D2B55; color: white;")
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        info_layout = QHBoxLayout()
        self.drawing_info = QLabel("")
        self.drawing_info.setStyleSheet("font-size: 16px; font-weight: bold; color: #B55CC0;")
        info_layout.addWidget(self.drawing_info)
        
        self.timer_label = QLabel(f"⏰ Time: {self.time_left}s")
        self.timer_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF9800;")
        info_layout.addWidget(self.timer_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        self.drawing_label = QLabel()
        self.drawing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drawing_label.setStyleSheet("""
            background: white; 
            border: 2px solid #B55CC0; 
            border-radius: 8px;
            min-height: 500px;
        """)
        self.drawing_label.setMinimumSize(600, 500)
        layout.addWidget(self.drawing_label)

        if len(self.players) > 1:
            nav_layout = QHBoxLayout()
            self.prev_btn = QPushButton("◀ Previous")
            self.prev_btn.setStyleSheet("""
                QPushButton {
                    background: #2196F3; 
                    color: white; 
                    border: none; 
                    border-radius: 5px; 
                    padding: 10px;
                }
                QPushButton:hover { background: #1976D2; }
                QPushButton:disabled { background: #666; }
            """)
            self.prev_btn.clicked.connect(self.previous_drawing)
            nav_layout.addWidget(self.prev_btn)
            nav_layout.addStretch()
            self.next_btn = QPushButton("Next ▶")
            self.next_btn.setStyleSheet("""
                QPushButton {
                    background: #4CAF50; 
                    color: white; 
                    border: none; 
                    border-radius: 5px; 
                    padding: 10px;
                }
                QPushButton:hover { background: #45A049; }
                QPushButton:disabled { background: #666; }
            """)
            self.next_btn.clicked.connect(self.next_drawing)
            nav_layout.addWidget(self.next_btn)
            layout.addLayout(nav_layout)
        
    def start_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
    def update_timer(self):
        self.time_left -= 1
        self.timer_label.setText(f"⏰ Time: {self.time_left}s")
        if self.time_left <= 0:
            self.timer.stop()
            self.close()
            
    def show_current_drawing(self):
        if not self.players or self.current_drawing_index >= len(self.players):
            self.drawing_label.setText("No drawings to display")
            return
            
        player = self.players[self.current_drawing_index]
        drawing_data = self.drawings.get(player)
        self.drawing_info.setText(f"Drawing by {player} ({self.current_drawing_index + 1}/{len(self.players)})")
        
        if hasattr(self, 'prev_btn') and hasattr(self, 'next_btn'):
            self.prev_btn.setEnabled(self.current_drawing_index > 0)
            self.next_btn.setEnabled(self.current_drawing_index < len(self.players) - 1)
        
        if drawing_data:
            try:
                image_data = base64.b64decode(drawing_data)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                scaled_pixmap = pixmap.scaled(
                    self.drawing_label.width() - 20, 
                    self.drawing_label.height() - 20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.drawing_label.setPixmap(scaled_pixmap)
            except Exception:
                self.drawing_label.setText("Error loading drawing")
        else:
            self.drawing_label.setText(f"No drawing submitted by {player}")
            
    def previous_drawing(self):
        if self.current_drawing_index > 0:
            self.current_drawing_index -= 1
            self.show_current_drawing()
            
    def next_drawing(self):
        if self.current_drawing_index < len(self.players) - 1:
            self.current_drawing_index += 1
            self.show_current_drawing()
            
    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()