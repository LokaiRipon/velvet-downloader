import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget, QGroupBox, QHBoxLayout, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from downloader import YTDownloader
from ui_new import ModernFormatGrid


class VelvetDownApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Velvet Down - Professional Media Downloader")
        self.setGeometry(150, 100, 750, 600)
        self.setMinimumSize(650, 500)

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
        if url and self.downloader.is_valid_youtube_url(url):
            self.format_grid.show_loading()
            self.downloader.fetch_formats(url)
        else:
            self.format_grid.show_error("Invalid or empty URL")

    def browse_folder(self):
        folder = self.downloader.select_folder()
        if folder:
            self.download_folder = folder
            self.folder_label.setText(folder)

    def reset_to_downloads(self):
        self.download_folder = self.downloads_folder
        self.folder_label.setText(self.downloads_folder)

    def start_download(self):
        if self.selected_format and not self.is_downloading:
            self.downloader.start_download(self.selected_format, self.download_folder)

    def cancel_download(self):
        self.downloader.cancel_download()

    def on_open_file_clicked(self):
        self.downloader.open_downloaded_file()
    
    # ✅ NEW: Public method to update progress from downloader
    def update_download_progress(self, percentage: int, status_text: str):
        """Called by downloader to update UI - runs in main thread"""
        self.progress.setValue(percentage)
        self.status_label.setText(status_text)
        # Force immediate UI update
        self.progress.repaint()
        self.status_label.repaint()