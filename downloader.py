import sys
import os
import re
import json
import tempfile
import glob
import shutil
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QTextEdit
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

# ✅ Import yt-dlp Python API directly
import yt_dlp


class FormatFetchThread(QThread):
    """Background thread for fetching formats"""
    finished = pyqtSignal(dict)  # Emits format data
    error = pyqtSignal(str)  # Emits error message
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'no_playlist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
                info = ydl.extract_info(self.url, download=False)
                self.finished.emit(info)
        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    """Background thread for downloading"""
    progress = pyqtSignal(str)  # Emits progress line
    finished_signal = pyqtSignal(int, str)  # exit_code, file_path
    error = pyqtSignal(str)
    
    def __init__(self, url, format_code, output_path, temp_dir, is_audio):
        super().__init__()
        self.url = url
        self.format_code = format_code
        self.output_path = output_path
        self.temp_dir = temp_dir
        self.is_audio = is_audio
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def progress_hook(self, d):
        """Called by yt-dlp during download"""
        if self._cancelled:
            raise yt_dlp.utils.DownloadCancelled() # type: ignore
        
        status = d.get('status')
        if status == 'downloading':
            pct = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', '').strip()
            eta = d.get('_eta_str', '').strip()
            total = d.get('_total_bytes_str', '?')
            line = f"[download] {pct} of {total} at {speed} ETA {eta}"
            self.progress.emit(line)
        elif status == 'finished':
            self.progress.emit("[download] 100%")
            self.progress.emit("[download] Download completed. Processing...")
        elif status == 'error':
            self.progress.emit(f"[ERROR] {d.get('error', 'Unknown error')}")
    
    def run(self):
        try:
            ydl_opts = {
                'format': self.format_code,
                'outtmpl': self.output_path,
                'no_playlist': True,
                'quiet': False,
                'no_warnings': True,
                'progress_hooks': [self.progress_hook],
            }
            
            # If format needs merging, specify output format
            if '+' in self.format_code or self.is_audio:
                ydl_opts['merge_output_format'] = 'mp4'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
                ydl.download([self.url])
            
            # Find the downloaded file
            candidates = [
                f for f in os.listdir(self.temp_dir)
                if not f.endswith(('.part', '.ytdl', '.tmp', '.temp'))
            ]
            
            if candidates:
                # Sort by size, get largest
                files_with_size = []
                for name in candidates:
                    path = os.path.join(self.temp_dir, name)
                    try:
                        size = os.path.getsize(path)
                        files_with_size.append((size, path))
                    except:
                        continue
                
                if files_with_size:
                    files_with_size.sort(reverse=True)
                    final_path = files_with_size[0][1]
                    self.finished_signal.emit(0, final_path)
                else:
                    self.error.emit("No valid output file found")
            else:
                self.error.emit("No output file found after download")
                
        except yt_dlp.utils.DownloadCancelled: # type: ignore
            self.finished_signal.emit(1, "")  # Cancelled
        except Exception as e:
            self.error.emit(str(e))


class YTDownloader:
    def __init__(self, parent):
        self.parent = parent
        self.current_url = None

        # Progress tracking
        self.last_progress_update = 0
        self.current_progress = 0

        # Downloaded file info
        self.last_downloaded_file = None
        self.last_format_type = None
        self.download_folder = None
        self.temp_download_folder = None

        # Phases
        self.is_downloading_phase = True
        self.is_merging_phase = False
        
        # Threads
        self.format_thread: Optional[FormatFetchThread] = None
        self.download_thread: Optional[DownloadThread] = None

    def is_valid_youtube_url(self, url):
        pattern = r'^https?://(www\.)?(youtube\.com|youtu\.be)/.+$'
        return bool(re.match(pattern, url))

    def select_folder(self):
        return QFileDialog.getExistingDirectory(self.parent, "Choose Download Folder")

    # ---------- Format fetching ----------
    def fetch_formats(self, url):
        self.current_url = url
        self.parent.format_grid.show_loading()
        self.parent.status_label.setText("⏳ Fetching formats...")

        self.format_thread = FormatFetchThread(url)
        self.format_thread.finished.connect(self.on_formats_fetched)
        self.format_thread.error.connect(self.on_format_error)
        self.format_thread.start()

    def on_format_error(self, error_msg):
        self.parent.format_grid.show_error(f"❌ {error_msg}")
        self.parent.status_label.setText("❌ Failed to fetch formats")

    def on_formats_fetched(self, data):
        try:
            formats = data.get('formats', [])
            video_formats = []
            audio_only_by_ext = {}

            for fmt in formats:
                acodec = fmt.get('acodec')
                vcodec = fmt.get('vcodec')
                has_audio = bool(acodec and acodec != 'none')
                has_video = bool(vcodec and vcodec != 'none')
                protocol = fmt.get('protocol')

                filesize = fmt.get('filesize', 0) or fmt.get('filesize_approx', 0)
                size_bytes = filesize if isinstance(filesize, int) else 0
                size_str = f"{size_bytes / (1024**2):.2f}MiB" if size_bytes else "N/A"

                if has_audio and has_video:
                    resolution = fmt.get('resolution', 'unknown')
                    video_formats.append({
                        "format_code": fmt.get('format_id', 'unknown'),
                        "ext": fmt.get('ext', 'unknown'),
                        "resolution": resolution,
                        "filesize": filesize,
                        "size_str": size_str,
                        "size_bytes": size_bytes,
                        "format_note": fmt.get('format_note', ''),
                        "vcodec": vcodec or '',
                        "acodec": acodec or '',
                    })
                elif has_audio and not has_video:
                    ext = (fmt.get('ext') or '').lower()
                    format_id = fmt.get('format_id', '')
                    if '-drc' in format_id.lower():
                        continue
                    preferred_audio_exts = ["mp3", "m4a", "webm", "aac"]
                    if ext in preferred_audio_exts and (protocol == 'https' or protocol is None):
                        keep = ext not in audio_only_by_ext or size_bytes > audio_only_by_ext[ext]['size_bytes']
                        if keep:
                            audio_only_by_ext[ext] = {
                                "format_code": fmt.get('format_id', 'unknown'),
                                "ext": ext,
                                "resolution": "Audio",
                                "filesize": filesize,
                                "size_str": size_str,
                                "size_bytes": size_bytes,
                                "format_note": fmt.get('format_note', ''),
                                "vcodec": vcodec or '',
                                "acodec": acodec or '',
                            }

            # Filter for target resolutions
            target_resolutions = {'144p': 144, '480p': 480, '720p': 720, '1080p': 1080}
            filtered_formats = {}
            for fmt in video_formats:
                res_str = fmt['resolution']
                if 'x' in res_str:
                    try:
                        _, height = map(int, res_str.split('x'))
                        for res_name, target_h in target_resolutions.items():
                            if height == target_h:
                                current = filtered_formats.get(res_name)
                                if current is None or fmt['size_bytes'] > current['size_bytes']:
                                    filtered_formats[res_name] = fmt
                    except:
                        continue

            ordered_resolutions = ['1080p', '720p', '480p', '144p']
            final_formats = [filtered_formats[r] for r in ordered_resolutions if r in filtered_formats]

            self.parent.format_grid.show_formats(final_formats, list(audio_only_by_ext.values()))
            self.parent.status_label.setText("✅ Formats loaded! Click to download.")

        except Exception as e:
            self.parent.format_grid.show_error(f"❌ Error parsing formats: {str(e)}")

    # ---------- Download flow ----------
    def start_download(self, fmt, folder):
        self.parent.is_downloading = True
        self.parent.url_input.setEnabled(False)
        self.parent.browse_btn.setEnabled(False)
        self.parent.cancel_btn.setVisible(True)
        self.parent.status_label.setText("Starting download...")
        self.parent.progress.setValue(0)
        if hasattr(self.parent, 'open_file_btn'):
            self.parent.open_file_btn.setVisible(False)

        self.is_downloading_phase = True
        self.is_merging_phase = False
        self.download_folder = folder

        safe_temp_root = os.path.join(os.path.expanduser("~"), "Downloads", "VelvetTemp")
        os.makedirs(safe_temp_root, exist_ok=True)
        self.temp_download_folder = tempfile.mkdtemp(prefix="velvet_down_", dir=safe_temp_root)

        format_code = fmt["format_code"]
        resolution = fmt.get('resolution', 'Unknown')
        self.last_format_type = 'audio' if resolution == 'Audio' else 'video'
        
        output_template = os.path.join(self.temp_download_folder, "%(title)s.%(ext)s")

        self.download_thread = DownloadThread(
            self.current_url,
            format_code,
            output_template,
            self.temp_download_folder,
            self.last_format_type == 'audio'
        )
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def update_progress(self, line):
        import time

        if "[ffmpeg]" in line or "Merging formats" in line or "Processing" in line:
            if not self.is_merging_phase:
                self.is_merging_phase = True
                self.is_downloading_phase = False
                self.parent.progress.setValue(100)
                self.parent.status_label.setText("🔄 Merging...")
                QApplication.processEvents()
            return

        match = re.search(r'(\d+(?:\.\d+)?)%', line)
        if match:
            try:
                pct = float(match.group(1))
                if self.is_downloading_phase:
                    actual_progress = int(pct)
                    status_text = f"⬇️ Downloading... {int(pct)}%"
                    
                    current_time = time.time()
                    if current_time - self.last_progress_update > 0.1:
                        self.parent.progress.setValue(min(actual_progress, 100))
                        self.parent.status_label.setText(status_text)
                        QApplication.processEvents()
                        self.last_progress_update = current_time
            except:
                pass

    def on_download_error(self, error_msg):
        self._cleanup_temp()
        self._reset_ui()
        self.parent.status_label.setText(f"❌ Download failed: {error_msg}")

    def download_finished(self, exit_code, temp_file_path):
        self._reset_ui()

        if exit_code == 0 and temp_file_path and os.path.isfile(temp_file_path):
            try:
                filename = os.path.basename(temp_file_path)
                final_path = os.path.join(self.download_folder, filename) # type: ignore
                shutil.move(temp_file_path, final_path)
                self._grant_full_control_windows(final_path)
                
                self.last_downloaded_file = final_path
                self.parent.progress.setValue(100)
                self.parent.status_label.setText("✅ Download completed!")
                
                if hasattr(self.parent, 'open_file_btn'):
                    self.parent.open_file_btn.setVisible(True)
                    file_type = "Video" if self.last_format_type == 'video' else "Audio"
                    self.parent.open_file_btn.setText(f"📂 Open {file_type}")
                    
                self._cleanup_temp()
            except Exception as e:
                self.parent.status_label.setText("⚠️ File move failed")
                self._cleanup_temp()
        else:
            self.parent.progress.setValue(0)
            self.parent.status_label.setText("⚠️ Download finished but no file produced")
            self._cleanup_temp()

    def _reset_ui(self):
        self.parent.is_downloading = False
        self.parent.url_input.setEnabled(True)
        self.parent.browse_btn.setEnabled(True)
        self.parent.cancel_btn.setVisible(False)

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.wait(3000)
        self._reset_ui()
        self.parent.status_label.setText("❌ Download cancelled")
        self.parent.progress.setValue(0)
        self._cleanup_temp()

    def open_downloaded_file(self):
        if not self.last_downloaded_file or not os.path.exists(self.last_downloaded_file):
            QMessageBox.warning(self.parent, "No File", "No downloaded file to open.")
            return
        try:
            import platform, subprocess
            system = platform.system()
            if system == 'Windows':
                os.startfile(self.last_downloaded_file)
            elif system == 'Darwin':
                subprocess.run(['open', self.last_downloaded_file])
            else:
                subprocess.run(['xdg-open', self.last_downloaded_file])
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Could not open file:\n{str(e)}")

    def cleanup_processes(self):
        if self.format_thread and self.format_thread.isRunning():
            self.format_thread.terminate()
            self.format_thread.wait(1000)
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.wait(1000)

    # ---------- Helpers ----------
    def _cleanup_temp(self):
        if self.temp_download_folder and os.path.exists(self.temp_download_folder):
            try:
                shutil.rmtree(self.temp_download_folder)
            except:
                pass

    def _grant_full_control_windows(self, file_path):
        if os.name != 'nt':
            return
        try:
            import win32security, ntsecuritycon as con, win32api
            user = win32api.GetUserName()
            domain = win32api.GetComputerName()
            try:
                sid, _, _ = win32security.LookupAccountName(None, f"{domain}\\{user}")
            except:
                sid, _, _ = win32security.LookupAccountName(None, user)
            sd = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, sid)
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION, sd)
        except:
            pass

    def log_message(self, text):
        print(text)

    def create_log_panel(self):
        log = QTextEdit()
        log.setReadOnly(True)
        log.setMaximumHeight(100)
        return log