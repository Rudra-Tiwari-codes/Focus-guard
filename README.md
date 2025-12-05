# FocusGuard

FocusGuard is a simple cross-platform Python utility that uses Google Gemini (Vision) to monitor your primary screen and enforce strict study focus for FAANG interview prep.

Features
- Periodically captures the primary monitor (every 60s by default).
- Sends the screenshot to Google Gemini for fast classification.
- If the AI judges the screen as distracted, a full-screen red penalty overlay locks the screen for 30 seconds.
- Uses `mss` for fast screenshots and `tkinter` for the overlay UI.

Requirements
- Python 3.8+
- Windows, macOS, and many Linux distros supported (penalty overlay behavior can vary by platform).

Installation

1. Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # PowerShell on Windows
# or on cmd.exe: .\.venv\Scripts\activate
# or on macOS/Linux: source .venv/bin/activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. (Optional) If `pip` installs `google-generativeai` fail, try `google-genai` — your environment may need a different package name depending on availability.

FocusGuard — quick start

1) Install

```powershell
pip install -r requirements.txt
```

2) Set API key

```powershell
Copy-Item .env.example .env
notepad .env
# or for session: $env:GEMINI_API_KEY = "your-key-here"
```

3) Run

```powershell
python focus_guard.py
```

Defaults: 60s check, 30s penalty. Screenshots are sent to Google Gemini — avoid sensitive content.