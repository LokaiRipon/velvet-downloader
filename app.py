import os
import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget, QGroupBox, QHBoxLayout, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from downloader import YTDownloader
from ui_new import ModernFormatGrid

logger = logging.getLogger(__name__)


class VelvetDownApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Velvet Down - Professional Media Downloader")
        self.setGeometry(150, 100, 600, 600)
        self.setMinimumSize(650, 500)
        self.setMaximumSize(800, 800)
        
        # ✅ Set window icon for title bar and taskbar
        self._set_window_icon()
        self._set_taskbar_icon()

        logger.info("Initializing VelvetDown application")
        
        self.downloader = YTDownloader(self)
        self.downloader.parent = self  # ✅ Critical for progress updates
        self.selected_format = None
        self.is_downloading = False

        # Central layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(24)
        layout.setContentsMargins(30, 25, 30, 25)

        # --- Header ---
        header = QLabel("🎬 Velvet Down\nProfessional Media Downloader")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(header)

        # --- URL Input ---
        url_card = QGroupBox("🔎 Video URL")
        url_layout = QVBoxLayout(url_card)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste your YouTube, TikTok, Instagram, or other video URL here...")
        self.url_input.setMinimumHeight(50)
        url_layout.addWidget(self.url_input)
        layout.addWidget(url_card)

        # --- Format Grid ---
        self.format_grid = ModernFormatGrid(self)
        layout.addWidget(self.format_grid)

        # --- Download Settings ---
        settings_card = QGroupBox("⚙️ Download Settings")
        settings_layout = QVBoxLayout(settings_card)

        self.downloads_folder = str(Path.home() / "Downloads")
        self.download_folder = self.downloads_folder
        self.folder_label = QLabel(self.downloads_folder)
        settings_layout.addWidget(self.folder_label)

        btns = QHBoxLayout()
        self.browse_btn = QPushButton("📁 Browse")
        self.reset_btn = QPushButton("↩️ Reset")
        btns.addWidget(self.browse_btn)
        btns.addWidget(self.reset_btn)
        settings_layout.addLayout(btns)
        layout.addWidget(settings_card)

        # --- Progress Section ---
        progress_card = QGroupBox("📊 Download Progress")
        progress_layout = QVBoxLayout(progress_card)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)  # ✅ Show percentage text
        progress_layout.addWidget(self.progress)

        self.status_label = QLabel("🚀 Ready to download")
        progress_layout.addWidget(self.status_label)

        self.cancel_btn = QPushButton("🛑 Cancel Download")
        self.cancel_btn.setVisible(False)
        progress_layout.addWidget(self.cancel_btn)

        self.open_file_btn = QPushButton("📂 Open File")
        self.open_file_btn.setVisible(False)
        self.open_file_btn.clicked.connect(self.on_open_file_clicked)
        progress_layout.addWidget(self.open_file_btn)

        layout.addWidget(progress_card)

        # --- Connections ---
        self.url_input.textChanged.connect(self.on_url_changed)
        self.browse_btn.clicked.connect(self.browse_folder)
        self.reset_btn.clicked.connect(self.reset_to_downloads)
        self.cancel_btn.clicked.connect(self.cancel_download)

    # --- Methods ---
    def on_url_changed(self):
        url = self.url_input.text().strip()
        if url:
            # Check network connectivity first
            if not self.downloader.is_connected():
                self.format_grid.show_error("🌐 No internet connection detected")
                logger.warning("Network connectivity check failed")
                return
            
            if self.downloader.is_valid_youtube_url(url):
                self.format_grid.show_loading()
                logger.info(f"Fetching formats for URL: {url[:50]}...")
                self.downloader.fetch_formats(url)
            else:
                self.format_grid.show_error("❌ Invalid URL format")
                logger.warning(f"Invalid URL provided: {url}")
        else:
            self.format_grid.show_error("Invalid or empty URL")

    def browse_folder(self):
        folder = self.downloader.select_folder()
        if folder:
            self.download_folder = folder
            self.folder_label.setText(folder)
            logger.info(f"Download folder changed to: {folder}")

    def reset_to_downloads(self):
        self.download_folder = self.downloads_folder
        self.folder_label.setText(self.downloads_folder)
        logger.info("Download folder reset to default")

    def start_download(self):
        if self.selected_format and not self.is_downloading:
            logger.info(f"Starting download with format: {self.selected_format.get('format_code')}")
            self.downloader.start_download(self.selected_format, self.download_folder)

    def cancel_download(self):
        logger.info("Download cancelled by user")
        self.downloader.cancel_download()

    def on_open_file_clicked(self):
        logger.info("Opening downloaded file")
        self.downloader.open_downloaded_file()
    
    # ✅ Public method to update progress from downloader
    def update_download_progress(self, percentage: int, status_text: str):
        """Called by downloader to update UI - runs in main thread"""
        self.progress.setValue(percentage)
        self.status_label.setText(status_text)
        # Force immediate UI update
        self.progress.repaint()
        self.status_label.repaint()

    def _set_window_icon(self):
        """Set the window icon for title bar and taskbar"""
        icon_paths = [
            "icon.ico",  # Current directory
            os.path.join(os.path.dirname(__file__), "icon.ico"),  # Script directory
            os.path.join(Path.cwd(), "icon.ico"),  # Working directory
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    icon = QIcon(icon_path)
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        logger.info(f"✅ Window icon loaded: {icon_path}")
                        return
                except Exception as e:
                    logger.warning(f"Could not load icon from {icon_path}: {str(e)}")
        
        logger.warning("⚠️ icon.ico not found. Window will use default icon.")
    
    def _set_taskbar_icon(self):
        """Set the taskbar icon on Windows using icon.ico"""
        try:
            import ctypes
            import platform
            
            if platform.system() != 'Windows':
                logger.debug("Not on Windows, skipping taskbar icon setup")
                return
            
            # Find icon.ico path
            icon_paths = [
                "icon.ico",
                os.path.join(os.path.dirname(__file__), "icon.ico"),
                os.path.join(Path.cwd(), "icon.ico"),
            ]
            
            icon_path = None
            for path in icon_paths:
                if os.path.exists(path):
                    icon_path = os.path.abspath(path)
                    break
            
            if not icon_path:
                logger.warning("⚠️ icon.ico not found for taskbar icon")
                return
            
            # Set app user model ID for Windows 7+ taskbar grouping
            myappid = 'velvetdown.app.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            
            # Set the icon on the window (which the OS uses for taskbar)
            icon = QIcon(icon_path)
            if not icon.isNull():
                self.setWindowIcon(icon)
                logger.info(f"✅ Taskbar icon set from: {icon_path}")
            else:
                logger.warning("⚠️ Failed to load icon for taskbar")
                
        except Exception as e:
            logger.debug(f"Taskbar icon setup failed: {str(e)}")
    
    def closeEvent(self, event):
        """Clean up when application closes"""
        logger.info("Application closing, cleaning up resources")
        self.downloader.cleanup_processes()
        event.accept()