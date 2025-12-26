# FocusGuard

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google)
![Cross Platform](https://img.shields.io/badge/Platform-Windows%20|%20Mac%20|%20Linux-lightgrey)

## Problem Statement

Knowledge workers lose hours daily to distraction from social media, news, and entertainment sites. Browser extensions help but can be bypassed; time-tracking apps only report after the damage is done. Real-time intervention is needed at the moment of distraction.

## Solution

A cross-platform background agent that monitors active window titles and uses AI to detect when you've strayed from productive work, providing immediate gentle reminders.

## Methodology

- **Window Monitoring** — Polls active window title across all platforms
- **AI Classification** — Google Gemini analyzes if content relates to current work context
- **Smart Alerts** — Non-intrusive notifications when distraction detected
- **Privacy-First** — Only window titles sent to API; no screenshots or content capture

## Results

- Works across Windows, macOS, and Linux
- Minimal resource usage (<50MB RAM)
- Customizable work context definitions
- No sensitive data stored externally

## Privacy

- Only window titles are analyzed (not content)
- No screenshots or keylogging
- API calls contain minimal metadata
- Full source available for audit

## Usage

```bash
pip install -r requirements.txt
python focusguard.py --context "Python development"
```

## Future Improvements

- Add Pomodoro timer integration with automatic focus sessions
- Implement offline mode with local ML model for privacy-sensitive users

---

[Rudra Tiwari](https://github.com/Rudra-Tiwari-codes)