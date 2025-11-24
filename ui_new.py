# ui_new.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QTabWidget,
    QGridLayout, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics

class ModernFormatItem(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, format_data, format_type="video"):
        super().__init__()
        self.format_data = format_data
        self.format_type = format_type
        # Compact card size that fits two lines
        self.setFixedSize(180, 60)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()

    def setup_ui(self):
        # Gradient per type using correct QFrame selector
        bg_gradient = "stop:0 #4c6ef5, stop:1 #7950f2" if self.format_type == 'video' else "stop:0 #2f9e44, stop:1 #2b8a3e"
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, {bg_gradient});
                border-radius: 6px;
                border: 2px solid transparent;
            }}
            QFrame:hover {{
                border-color: rgba(255,255,255,0.35);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 6, 8, 6)

        # Primary line: resolution -> display "1080p" from "1920x1080"
        resolution = str(self.format_data.get("resolution", "Unknown"))
        if self.format_type == "video" and 'x' in resolution:
            try:
                height = resolution.split('x')[1]
                display_text = f"{height}p"
            except:
                display_text = resolution
        else:
            display_text = resolution

        title = QLabel()
        title.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setText(self._elide_text(title, display_text))
        layout.addWidget(title)

        # Secondary line: EXT • SIZE • NOTE
        ext = (self.format_data.get("ext") or "mp4").upper()
        size = self.format_data.get("size_str") or "Unknown"
        note = self.format_data.get("format_note") or ""
        desc_raw = f"{ext} • {size}" + (f" • {note}" if note else "")

        info = QLabel()
        info.setStyleSheet("color: #E0E0E0; font-size: 10px;")
        info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        info.setText(self._elide_text(info, desc_raw))
        layout.addWidget(info)

    def _elide_text(self, label: QLabel, text: str) -> str:
        fm = QFontMetrics(label.font())
        available = max(80, self.width() - 16)
        return fm.elidedText(text, Qt.TextElideMode.ElideRight, available)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.format_data)
        super().mousePressEvent(event)


class ModernFormatGrid(QWidget):
    format_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent  # type: ignore
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Loading label
        self.loading_label = QLabel("")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.loading_label)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        # Video tab (scrollable)
        self.video_scroll = QScrollArea()
        self.video_scroll.setWidgetResizable(True)
        self.video_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.video_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.video_widget = QWidget()
        self.video_layout = QGridLayout()
        self.video_layout.setContentsMargins(12, 12, 12, 12)
        self.video_layout.setHorizontalSpacing(6)
        self.video_layout.setVerticalSpacing(6)
        self.video_widget.setLayout(self.video_layout)
        self.video_scroll.setWidget(self.video_widget)

        # Audio tab (scrollable)
        self.audio_scroll = QScrollArea()
        self.audio_scroll.setWidgetResizable(True)
        self.audio_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.audio_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.audio_widget = QWidget()
        self.audio_layout = QGridLayout()
        self.audio_layout.setContentsMargins(12, 12, 12, 12)
        self.audio_layout.setHorizontalSpacing(6)
        self.audio_layout.setVerticalSpacing(6)
        self.audio_widget.setLayout(self.audio_layout)
        self.audio_scroll.setWidget(self.audio_widget)

        self.tabs.addTab(self.video_scroll, "🎥 Video")
        self.tabs.addTab(self.audio_scroll, "🎵 Audio")
        root.addWidget(self.tabs)

        # Hide tabs until content arrives
        self.tabs.hide()

    def show_loading(self):
        self.loading_label.setText("🔄 Fetching available formats...")
        self.loading_label.show()
        self.tabs.hide()

    def show_error(self, message):
        self.loading_label.setText(f"❌ {message}")
        self.loading_label.show()
        self.tabs.hide()

    def show_formats(self, video_formats, audio_formats):
        self.loading_label.hide()
        self.tabs.show()

        # Clear previous items
        for layout in (self.video_layout, self.audio_layout):
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget() # type: ignore
                if w is not None:
                    w.deleteLater()

        # Populate video formats (2 per row for density)
        if video_formats:
            for i, fmt in enumerate(video_formats):
                item = ModernFormatItem(fmt, "video")
                item.clicked.connect(self.on_format_selected)
                self.video_layout.addWidget(item, i // 2, i % 2)
        else:
            empty = QLabel("No video formats available.")
            empty.setStyleSheet("color: #CCCCCC;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_layout.addWidget(empty, 0, 0)

        # Populate audio formats (2 per row)
        if audio_formats:
            for i, fmt in enumerate(audio_formats):
                item = ModernFormatItem(fmt, "audio")
                item.clicked.connect(self.on_format_selected)
                self.audio_layout.addWidget(item, i // 2, i % 2)
        else:
            empty = QLabel("No audio formats available.")
            empty.setStyleSheet("color: #CCCCCC;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.audio_layout.addWidget(empty, 0, 0)

        # Keep grid visually open
        self.video_layout.setRowStretch((len(video_formats) + 2) // 2, 1)
        self.audio_layout.setRowStretch((len(audio_formats) + 2) // 2, 1)

        # Reflow after population
        self.video_widget.update()
        self.audio_widget.update()

    def on_format_selected(self, format_data):
        if hasattr(self.parent, "selected_format"):
            self.parent.selected_format = format_data  # type: ignore
        if hasattr(self.parent, "start_download"):
            self.parent.start_download()  # type: ignore