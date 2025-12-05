import os
import io
import time
import threading
from datetime import datetime
from typing import Optional

# Screenshot library (faster than pyautogui/PIL ImageGrab) # Found this on an article lol
import mss
import mss.tools

# Google Gemini AI
import google.generativeai as genai
from PIL import Image

# Optional: load environment variables from a .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # If python-dotenv is not installed, we'll still read from the environment
    pass

# GUI for penalty overlay
import tkinter as tk
from tkinter import font as tkfont

# Video playback
import cv2
from PIL import ImageTk

# Audio playback
import subprocess

# Path to the penalty video (relative to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PENALTY_VIDEO_PATH = os.path.join(SCRIPT_DIR, "Video-900.mp4")

# API key is loaded from the environment. You can create a `.env` file with
# `GEMINI_API_KEY=your-key` (we attempt to load it via python-dotenv).
API_KEY = os.environ.get("GEMINI_API_KEY")

# Monitoring interval in seconds (30s for testing)
CHECK_INTERVAL = 40

# Penalty duration in seconds
PENALTY_DURATION = 30

# Gemini model to use (default for the free API keys)
GEMINI_MODEL = "gemini-2.0-flash"

# VISION PROMPT

ANALYSIS_PROMPT = """
You are a study supervisor AI for a highly productive student.
Determine if the screen shows PRODUCTIVE coding work or DISTRACTED behavior.

PRODUCTIVE (SAFE) - mark as SAFE if ANY of these are visible:
- Code editors: VS Code, PyCharm, IntelliJ, Sublime, Vim, Neovim, terminals with code
- LeetCode, NeetCode, HackerRank, CodeSignal, Codeforces, AtCoder
- StackOverflow, GeeksForGeeks, GitHub, GitLab, Bitbucket
- Technical docs: MDN, Python docs, Java docs, cppreference, DevDocs
- PDF textbooks, technical papers, Notion notes about coding
- Any window showing source code, even partially visible
- YouTube IF it shows code/programming tutorial (code visible on screen)
- ChatGPT/Claude IF discussing code or technical problems

SPLIT-SCREEN RULES (IMPORTANT):
- If screen is split and ONE side has code/LeetCode/productive content = SAFE
- Half LeetCode + half YouTube = SAFE (benefit of the doubt)
- Half code editor + half anything = SAFE
- Only mark DISTRACTED if NO coding content is visible anywhere

DISTRACTED (NOT SAFE) - ONLY if NO productive content visible:
- Pure entertainment: Netflix, Disney+, Twitch streams (non-coding)
- Social media feeds: Twitter/X, Instagram, TikTok, Facebook
- Reddit front page or non-programming subreddits
- YouTube showing gaming, vlogs, music videos (no code)
- Shopping sites, news sites, sports
- Video games

IMPORTANT: Default to SAFE if you see ANY code, terminal, or technical content.
Only mark DISTRACTED if the ENTIRE screen is entertainment/social media.

Respond with exactly one word:
- SAFE
- DISTRACTED
"""

# PENALTY OVERLAY CLASS

class PenaltyOverlay:
    """Full-screen overlay with video background, audio, and text overlay."""

    def __init__(self, duration: int = PENALTY_DURATION):
        self.duration = duration
        self.remaining = duration
        self.root = None
        self.timer_label = None
        self.video_label = None
        self.cap = None
        self.is_active = False
        self.loop_count = 0
        self.max_loops = 4
        self.audio_process = None  # subprocess for audio playback

    def _block_close(self):
        """Prevent the window from being closed."""
        return "break"

    def _start_audio(self):
        """Start audio playback using Windows Media Player via subprocess."""
        try:
            # Use PowerShell to play audio in background (works on Windows)
            # wmplayer plays audio from video files
            self.audio_process = subprocess.Popen(
                ['powershell', '-WindowStyle', 'Hidden', '-Command',
                 f'Add-Type -AssemblyName presentationCore; $player = New-Object System.Windows.Media.MediaPlayer; $player.Open("{PENALTY_VIDEO_PATH}"); $player.Play(); Start-Sleep -Seconds {self.duration + 5}'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            print(f"[WARNING] Could not start audio: {e}")

    def _stop_audio(self):
        """Stop audio playback."""
        if self.audio_process:
            try:
                self.audio_process.terminate()
                self.audio_process = None
            except Exception:
                pass

    def _update_timer(self):
        """Update the countdown timer."""
        if not self.root or not self.timer_label:
            return
        if self.remaining > 0:
            try:
                self.timer_label.config(text=f"{self.remaining}s")
            except tk.TclError:
                return
            self.remaining -= 1
            self.root.after(1000, self._update_timer)
        else:
            self._close_overlay()

    def _update_video(self):
        """Update the video frame."""
        if not self.root or not self.cap or not self.is_active:
            return

        ret, frame = self.cap.read()
        if not ret:
            # Video ended, loop or stop
            self.loop_count += 1
            if self.loop_count < self.max_loops:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return
            else:
                # Finished all loops
                return

        # Convert BGR to RGB and resize to screen
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        frame = cv2.resize(frame, (screen_w, screen_h))

        # Convert to PhotoImage
        img = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image=img)

        try:
            self.video_label.config(image=photo)
            self.video_label.image = photo  # Keep reference
        except tk.TclError:
            return

        # Schedule next frame (~30fps)
        self.root.after(33, self._update_video)

    def _close_overlay(self):
        """Close the overlay window and stop audio."""
        self.is_active = False
        # Stop audio
        self._stop_audio()
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None

    def _force_focus(self):
        """Keep the window on top and focused."""
        if self.root and self.is_active:
            try:
                self.root.lift()
                self.root.focus_force()
                self.root.attributes('-topmost', True)
                self.root.after(100, self._force_focus)
            except tk.TclError:
                pass

    def show(self):
        """Display the penalty overlay with video background and audio."""
        self.is_active = True
        self.remaining = self.duration
        self.loop_count = 0

        # Create root window
        self.root = tk.Tk()
        self.root.title("")
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Try to make transparent (Windows)
        try:
            self.root.attributes('-transparentcolor', 'black')
            self.root.configure(bg='black')
        except Exception:
            self.root.configure(bg='#1a1a1a')  # Fallback dark bg

        # Block close
        self.root.protocol("WM_DELETE_WINDOW", self._block_close)
        self.root.bind('<Alt-F4>', lambda e: 'break')
        self.root.bind('<Escape>', lambda e: 'break')

        # Video background label
        self.video_label = tk.Label(self.root, bg='black')
        self.video_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Text overlay frame
        text_frame = tk.Frame(self.root, bg='#1a1a1a')
        text_frame.place(relx=0.5, rely=0.5, anchor='center')

        # Use Consolas for a clean look
        title_font = tkfont.Font(family='Consolas', size=48, weight='bold')
        msg_font = tkfont.Font(family='Consolas', size=26)
        timer_font = tkfont.Font(family='Consolas', size=36, weight='bold')

        # Title
        title_label = tk.Label(
            text_frame,
            text="DISTRACTION DETECTED",
            font=title_font,
            bg='#1a1a1a',
            fg='#ff4444'
        )
        title_label.pack(pady=(0, 12))

        # Message
        msg_label = tk.Label(
            text_frame,
            text="Get back to LeetCode.",
            font=msg_font,
            bg='#1a1a1a',
            fg='white'
        )
        msg_label.pack(pady=(0, 20))

        # Timer
        self.timer_label = tk.Label(
            text_frame,
            text=f"{self.duration}s",
            font=timer_font,
            bg='#1a1a1a',
            fg='#ffcc00'
        )
        self.timer_label.pack()

        # Open video and start audio
        if os.path.exists(PENALTY_VIDEO_PATH):
            self.cap = cv2.VideoCapture(PENALTY_VIDEO_PATH)
            self.root.after(10, self._update_video)
            # Play audio using subprocess (Windows Media Player)
            self._start_audio()
        else:
            print(f"[WARNING] Video not found: {PENALTY_VIDEO_PATH}")

        # Start timer and focus loop
        self.root.after(1000, self._update_timer)
        self.root.after(100, self._force_focus)

        try:
            self.root.grab_set_global()
        except tk.TclError:
            pass

        self.root.mainloop()


# Screenshot

def capture_screenshot() -> bytes:
    """
    Capture a screenshot of the primary monitor using mss.
    Returns the screenshot as PNG bytes.
    """
    with mss.mss() as sct:
        # Capture the primary monitor (monitor 1, as 0 is "all monitors")
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        
        # Convert to PNG bytes
        png_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
        
        return png_bytes


def screenshot_to_pil(png_bytes: bytes) -> Image.Image:
    """Convert PNG bytes to PIL Image for Gemini API."""
    return Image.open(io.BytesIO(png_bytes))

# Gemini

class GeminiAnalyzer:
    """Handles communication with the Google Gemini API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the Gemini client."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
    
    def analyze_screenshot(self, image: Image.Image) -> str:
        """
        Send screenshot to Gemini for analysis.
        Returns: "SAFE" or "DISTRACTED: LOCK IN KING"
        """
        try:
            response = self.model.generate_content(
                [ANALYSIS_PROMPT, image],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for consistent results
                    max_output_tokens=50,  # We only need a short response
                )
            )
            
            result = response.text.strip().upper()
            
            # Validate response
            if "DISTRACTED" in result:
                return "DISTRACTED"
            elif "SAFE" in result:
                return "SAFE"
            else:
                # If response is unclear, default to SAFE to avoid false positives
                print(f"[WARNING] Unclear response: {result}. Defaulting to SAFE.")
                return "SAFE"
                
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")


# Guard Class

class FocusGuard:
    """Main application class that orchestrates monitoring and enforcement.

    You may provide the Gemini API key directly when creating the instance
    (recommended for programmatic use or tests) by calling
    `FocusGuard(api_key='...')`. If not provided the code will use the
    `API_KEY` loaded from the environment or `.env`.
    """
    def __init__(self, api_key: Optional[str] = None):
        # Prefer the API key passed to the instance; fall back to the env var.
        self.api_key = api_key or API_KEY
        self.analyzer = None
        self.running = False
        self.penalty_active = False
        
        # Metrics tracking
        self.session_start = datetime.now()
        self.total_checks = 0
        self.safe_checks = 0
        self.distracted_checks = 0
        self.total_penalty_time = 0  # seconds
        self.longest_focus_streak = 0
        self.current_focus_streak = 0
        self.focus_streaks = []
        
        self._initialize_analyzer()

    def _initialize_analyzer(self):
        """Initialize the Gemini analyzer using the instance API key."""
        if not self.api_key:
            print("=" * 60)
            print("ERROR: Gemini API key not provided to FocusGuard")
            print("=" * 60)
            print("\nOptions:")
            print("1. Pass the API key when creating FocusGuard: FocusGuard(api_key='...')")
            print("2. Set the environment variable GEMINI_API_KEY or create a .env file")
            print("\nGet your API key from: https://makersuite.google.com/app/apikey")
            print("=" * 60)
            # Exit the program
            raise SystemExit(1)

        # Initialize the Gemini analyzer with the provided key
        self.analyzer = GeminiAnalyzer(self.api_key)
        print("[OK] Gemini AI analyzer initialized successfully")
    
    def _analyze_in_thread(self, image: Image.Image):
        """Run the analysis in a separate thread."""
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Analyzing screenshot...")
            result = self.analyzer.analyze_screenshot(image)
            self.total_checks += 1
            
            if result == "DISTRACTED":
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  DISTRACTED - Activating penalty mode!")
                self.distracted_checks += 1
                self.total_penalty_time += PENALTY_DURATION
                # Record streak and reset
                if self.current_focus_streak > 0:
                    self.focus_streaks.append(self.current_focus_streak)
                    if self.current_focus_streak > self.longest_focus_streak:
                        self.longest_focus_streak = self.current_focus_streak
                self.current_focus_streak = 0
                self._trigger_penalty()
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  SAFE - Keep up the good work!")
                self.safe_checks += 1
                self.current_focus_streak += 1
                if self.current_focus_streak > self.longest_focus_streak:
                    self.longest_focus_streak = self.current_focus_streak
                
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}]  Analysis error: {e}")
            print("Will retry in the next check cycle...")
    
    def _trigger_penalty(self):
        """Trigger the penalty overlay in the main thread."""
        if self.penalty_active:
            return
        
        self.penalty_active = True
        
        # Run penalty overlay in a new thread to not block
        def show_penalty():
            try:
                overlay = PenaltyOverlay(PENALTY_DURATION)
                overlay.show()
            finally:
                self.penalty_active = False
        
        penalty_thread = threading.Thread(target=show_penalty, daemon=False)
        penalty_thread.start()
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            # Skip check if penalty is active
            if self.penalty_active:
                time.sleep(1)
                continue
            
            try:
                # Capture screenshot
                png_bytes = capture_screenshot()
                image = screenshot_to_pil(png_bytes)
                
                # Analyze in a separate thread
                analysis_thread = threading.Thread(
                    target=self._analyze_in_thread,
                    args=(image,),
                    daemon=True
                )
                analysis_thread.start()
                
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  Screenshot error: {e}")
            
            # Wait for the next check interval
            for _ in range(CHECK_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)
    
    def start(self):
        """Start the FocusGuard monitoring."""
        print("\n" + "=" * 60)
        print(" Focus Guard")
        print("=" * 60)
        print(f" Checking screen every {CHECK_INTERVAL} seconds")
        print(f" Penalty duration: {PENALTY_DURATION} seconds")
        print(f" Using model: {GEMINI_MODEL}")
        print("=" * 60)
        print("\n Whitelist: LeetCode, NeetCode, VS Code, StackOverflow,")
        print("              GeeksForGeeks, technical docs, terminals")
        print("\n Blacklist: YouTube (non-coding), Netflix, Twitter/X,")
        print("              LinkedIn, Reddit, social media, games, anything not code")
        print("\n" + "=" * 60)
        print("Press Ctrl+C to stop monitoring")
        print("=" * 60 + "\n")
        
        self.running = True
        
        try:
            self._monitoring_loop()
        except KeyboardInterrupt:
            print("\n\n[INFO] FocusGuard stopped by user")
            self.running = False
            self._print_session_metrics()
    
    def _print_session_metrics(self):
        """Print session metrics for LinkedIn/resume."""
        session_duration = (datetime.now() - self.session_start).total_seconds()
        session_minutes = int(session_duration / 60)
        focus_rate = (self.safe_checks / max(self.total_checks, 1)) * 100
        time_saved = self.distracted_checks * 15  # Assume 15 min saved per intervention
        productive_time = session_minutes - (self.total_penalty_time / 60)
        avg_focus_streak = sum(self.focus_streaks) / max(len(self.focus_streaks), 1) if self.focus_streaks else self.current_focus_streak
        
        print("\n" + "=" * 60)
        print(" SESSION METRICS (LinkedIn-Ready Stats)")
        print("=" * 60)
        print(f"\n  Session Duration: {session_minutes} minutes")
        print(f" Total Screen Checks: {self.total_checks}")
        print(f" Productive Checks: {self.safe_checks}")
        print(f" Distraction Events: {self.distracted_checks}")
        print(f" Focus Rate: {focus_rate:.1f}%")
        print(f" Time in Penalty: {self.total_penalty_time // 60}m {self.total_penalty_time % 60}s")
        print(f" Estimated Time Saved: ~{time_saved} minutes")
        print(f" Longest Focus Streak: {self.longest_focus_streak} checks ({self.longest_focus_streak * CHECK_INTERVAL // 60}+ min)")
        print(f" Avg Focus Streak: {avg_focus_streak:.1f} checks")
        print(f" Productive Time: ~{int(productive_time)} minutes")
        print("=" * 60)
    
    def stop(self):
        """Stop the FocusGuard monitoring."""
        self.running = False
        self._print_session_metrics()


# Entry 

if __name__ == "__main__":
    try:
        # Pass the loaded API_KEY (from environment or .env) into FocusGuard.
        guard = FocusGuard(api_key=API_KEY)
        guard.start()
    except ValueError as e:
        pass
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        print("\nMake sure you have installed the required libraries:")
        print("  pip install mss google-generativeai pillow python-dotenv")