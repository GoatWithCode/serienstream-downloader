import sys
import os
import shutil
from urllib.parse import urljoin
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QFileDialog, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFontMetrics
from playwright.sync_api import sync_playwright
import yt_dlp

def find_chrome_path():
    paths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    chrome_path = shutil.which("google-chrome") or shutil.which("chrome") or shutil.which("chromium-browser")
    if chrome_path:
        return chrome_path
    return None

class ExtractorThread(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(bool)  # True = busy, False = done
    result = pyqtSignal(list)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        self.progress.emit(True)
        self.status.emit("🔍 Starting extraction process...")
        iframe_url = self.extract_iframe_url(self.url)
        if not iframe_url:
            self.status.emit("❌ Could not extract iframe URL.")
            self.result.emit([])
            self.progress.emit(False)
            return
        self.status.emit(f"🔗 Found iframe URL: {iframe_url}")
        m3u8_links = self.find_m3u8_links(iframe_url)
        if m3u8_links:
            self.status.emit(f"✅ Found {len(m3u8_links)} m3u8 link(s).")
        else:
            self.status.emit("❌ No m3u8 links found.")
        self.result.emit(m3u8_links)
        self.progress.emit(False)

    def extract_iframe_url(self, s_to_url):
        try:
            with sync_playwright() as p:
                chrome_path = find_chrome_path()
                browser = p.chromium.launch(
                    headless=False,
                    executable_path=chrome_path if chrome_path else None
                )
                context = browser.new_context()
                page = context.new_page()
                page.goto(s_to_url, timeout=60000)
                page.wait_for_selector("iframe", timeout=15000)
                iframe = page.query_selector("iframe")
                if not iframe:
                    browser.close()
                    return None
                relative_src = iframe.get_attribute("src")
                iframe_src = urljoin(page.url, relative_src)
                browser.close()
                return iframe_src
        except Exception as e:
            self.status.emit(f"❌ Error extracting iframe: {e}")
            return None

    def find_m3u8_links(self, url, max_wait_time_ms=120000):
        try:
            with sync_playwright() as p:
                chrome_path = find_chrome_path()
                browser = p.chromium.launch(
                    headless=False,
                    executable_path=chrome_path if chrome_path else None
                )
                page = browser.new_page()

                m3u8_links = set()
                found_link = False

                def on_request(request):
                    nonlocal found_link
                    if ".m3u8" in request.url and not found_link:
                        m3u8_links.add(request.url)
                        found_link = True
                        page.evaluate("window.stop()")

                page.on("request", on_request)
                page.goto(url)

                waited_ms = 0
                interval_ms = 500
                while waited_ms < max_wait_time_ms and not found_link:
                    page.wait_for_timeout(interval_ms)
                    waited_ms += interval_ms

                browser.close()
                return list(m3u8_links)
        except Exception as e:
            self.status.emit(f"❌ Error searching for m3u8 links: {e}")
            return []

class DownloaderThread(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(int)  # percent 0-100
    finished_single = pyqtSignal()

    def __init__(self, url, output):
        super().__init__()
        self.url = url
        self.output = output

    def run(self):
        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                if total and total > 0:
                    percent = int(downloaded * 100 / total)
                    self.progress.emit(percent)
                else:
                    self.progress.emit(50)
            elif d['status'] == 'finished':
                self.progress.emit(100)
                self.status.emit("✅ Download finished!")

        ydl_opts = {
            'format': 'best',
            'outtmpl': self.output,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.status.emit(f"⬇️ Starting download: {self.url}")
                ydl.download([self.url])
        except Exception as e:
            self.status.emit(f"❌ Download error: {e}")
        self.finished_single.emit()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("s.to m3u8 Downloader by G0atWithCode")
        self.resize(700, 400)
        self.layout = QVBoxLayout()

        self.input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter s.to episode URL (e.g. https://s.to/series/...)")
        self.url_input.setMaximumHeight(30)
        self.start_button = QPushButton("Finde m3u8")
        self.input_layout.addWidget(self.url_input)
        self.input_layout.addWidget(self.start_button)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)

        self.button_layout = QHBoxLayout()
        self.download_button = QPushButton("Start all downloads")
        self.download_button.setEnabled(False)
        self.quit_button = QPushButton("Quit")
        self.button_layout.addWidget(self.download_button)
        self.button_layout.addWidget(self.quit_button)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setFixedHeight(20)
        self.status_label.setWordWrap(False)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        self.layout.addLayout(self.input_layout)
        self.layout.addWidget(self.list_widget)
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)

        self.start_button.clicked.connect(self.start_extraction)
        self.download_button.clicked.connect(self.download_all)
        self.quit_button.clicked.connect(self.close)

        self.extractor_thread = None
        self.downloader_thread = None

        self.download_queue = []
        self.current_download_index = 0

        self.download_folder = None  # Download folder

    def set_status(self, text):
        max_width = self.width() - 40
        fm = QFontMetrics(self.status_label.font())
        elided = fm.elidedText(text, Qt.ElideRight, max_width)
        self.status_label.setText(elided)

    def start_extraction(self):
        url = self.url_input.text().strip()
        if not url:
            self.set_status("❌ Please enter a valid URL.")
            return
        if self.extractor_thread and self.extractor_thread.isRunning():
            self.set_status("⚠️ Please wait until the current process finishes.")
            return
        self.download_button.setEnabled(False)
        self.set_status("🔄 Starting extraction process...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(0)
        self.extractor_thread = ExtractorThread(url)
        self.extractor_thread.status.connect(self.set_status)
        self.extractor_thread.result.connect(self.show_results)
        self.extractor_thread.progress.connect(self.handle_extraction_progress)
        self.extractor_thread.start()

    def handle_extraction_progress(self, busy):
        if busy:
            self.progress_bar.setMaximum(0)
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(100)
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(800, lambda: self.progress_bar.setVisible(False))

    def show_results(self, links):
        added = 0
        for link in links:
            if not any(self.list_widget.item(i).text() == link for i in range(self.list_widget.count())):
                self.list_widget.addItem(link)
                added += 1
        if added > 0:
            self.download_button.setEnabled(True)
            self.set_status(f"✅ Added {added} m3u8 link(s) to the list.")
        else:
            self.set_status("⚠️ No new m3u8 links added (may already exist).")

    def download_all(self):
        if self.downloader_thread and self.downloader_thread.isRunning():
            self.set_status("⚠️ Please wait until the current download finishes.")
            return
        count = self.list_widget.count()
        if count == 0:
            self.set_status("❌ No links in the list to download.")
            return

        if not self.download_folder:
            folder = QFileDialog.getExistingDirectory(self, "Choose folder to save videos")
            if not folder:
                self.set_status("❌ No folder chosen. Download cancelled.")
                return
            self.download_folder = folder

        self.download_queue = [self.list_widget.item(i).text() for i in range(count)]
        self.current_download_index = 0

        self.download_next()

    def download_next(self):
        if self.current_download_index >= len(self.download_queue):
            self.set_status("✅ All downloads completed.")
            self.progress_bar.setVisible(False)
            return

        url = self.download_queue[self.current_download_index]

        filename = os.path.join(self.download_folder, f"video_{self.current_download_index + 1}.mp4")

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.set_status(f"⬇️ Starting download {self.current_download_index + 1} of {len(self.download_queue)}")

        self.downloader_thread = DownloaderThread(url, filename)
        self.downloader_thread.status.connect(self.set_status)
        self.downloader_thread.progress.connect(self.progress_bar.setValue)
        self.downloader_thread.finished_single.connect(self.on_single_download_finished)
        self.downloader_thread.start()

    def on_single_download_finished(self):
        self.current_download_index += 1
        self.download_next()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
