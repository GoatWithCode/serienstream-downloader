📺 s.to m3u8 Downloader by G0atWithCode
A desktop GUI tool to extract and download .m3u8 video streams from s.to. It uses Playwright together with your locally installed Google Chrome browser to analyze embedded players, and yt-dlp to download the actual video files.

⚙️ Features
Input any episode URL from s.to

Extracts the embedded iframe video player URL

Monitors network traffic to detect .m3u8 stream URLs

Downloads videos as .mp4 using yt-dlp

Simple and user-friendly PyQt5 GUI

Dependencies (Install with pip):

pip install PyQt5 playwright yt-dlp
playwright install

✅ Note: This tool uses your locally installed Google Chrome instead of Playwright's internal browser. Make sure Chrome is installed on your system.

Supported Chrome paths:

Windows:
C:\Program Files\Google\Chrome\Application\chrome.exe

C:\Program Files (x86)\Google\Chrome\Application\chrome.exe

📝 How to Use
Enter the episode URL
Paste the s.to episode link (e.g. https://s.to/serie/stream/...) and click "Finde m3u8".

View results
Any found .m3u8 links will be shown in the list below.

Start downloads
Click "Start all downloads", choose a target folder, and the videos will be downloaded as .mp4.

howto video: https://c.gmx.net/@329938113155568689/lk4SKqMffEvTyqRA1Zuf4A/ROOT/ROOT

Pyinstaller
pyinstaller --onefile --windowed main.py

You can download the Binary here: https://c.gmx.net/@329938113155568689/V4J8XxQBHK3rK8gnKfrfRw

