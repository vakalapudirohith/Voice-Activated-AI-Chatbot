"""
voice_assistant.py
A simple voice-activated AI chatbot with:
- speech -> text (SpeechRecognition)
- text -> speech (pyttsx3)
- wikipedia lookup (wikipedia-api)
- open websites / google search
- notes & reminders
- safe system commands (shutdown/restart)
- optional: take photo (requires OpenCV)
"""

import speech_recognition as sr
import pyttsx3
import datetime
import time
import webbrowser
import os
import subprocess
import platform
import threading
import json
import wikipediaapi
from urllib.parse import quote_plus

# Optional import for camera
try:
    import cv2
except Exception:
    cv2 = None

# --- Text-to-speech setup ---
engine = pyttsx3.init()
engine.setProperty('rate', 150)        # speaking rate (words per minute)
voices = engine.getProperty('voices')
if voices:
    engine.setProperty('voice', voices[0].id)  # pick voice index 0 (change if needed)

def speak(text: str):
    """Speak the given text and print to console."""
    print("[Assistant]:", text)
    engine.say(text)
    engine.runAndWait()

# --- Speech to text (microphone) ---
def takeCommand(timeout: int = None, phrase_time_limit: int = 8) -> str:
    """
    Listen from the microphone and return recognized text.
    Returns empty string on failure.
    """
    r = sr.Recognizer()
    r.pause_threshold = 0.8          # seconds of pause before finishing a phrase
    r.energy_threshold = 300         # adjust if too quiet/too noisy
    try:
        with sr.Microphone() as source:
            print("Listening...")
            r.adjust_for_ambient_noise(source, duration=0.6)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            query = r.recognize_google(audio, language='en-in')
            print("[You]:", query)
            return query
        except sr.UnknownValueError:
            speak("Sorry, I didn't understand that. Please say it again.")
            return ""
        except sr.RequestError:
            speak("Network/API error. Check your internet connection.")
            return ""
    except Exception as e:
        print("Microphone error:", str(e))
        speak("Microphone not available. Check your microphone and permissions.")
        return ""

# --- Greeting ---
def wishMe():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        speak("Good morning!")
    elif 12 <= hour < 18:
        speak("Good afternoon!")
    elif 18 <= hour < 22:
        speak("Good evening!")
    else:
        speak("Hello!")
    speak("I am your voice assistant. How can I help you?")

# --- Wikipedia search ---
wiki_wiki = wikipediaapi.Wikipedia(
    language='en',
    user_agent='VoiceAssistant/1.0 (https://github.com/vshashank; vakalapudi.shashank@example.com)'
)


def search_wikipedia(query: str, sentences: int = 2):
    topic = query.strip()
    if not topic:
        speak("What should I search on Wikipedia?")
        topic = takeCommand()
    page = wiki_wiki.page(topic)
    if page.exists():
        summary = page.summary
        # speak only first few sentences
        short = ". ".join(summary.split(".")[:sentences]).strip()
        if not short:
            short = summary[:500]
        speak(f"According to Wikipedia: {short}")
        print("--- full summary start ---")
        print(summary[:1500])  # print snippet to console
        print("--- full summary end ---")
    else:
        speak("I couldn't find that page on Wikipedia.")

# --- Open websites / search web ---
WEBSITE_MAP = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
}

def open_website(site_key: str):
    url = WEBSITE_MAP.get(site_key, None)
    if url:
        webbrowser.open(url)
        speak(f"Opening {site_key}.")
    else:
        # try direct open
        if "." in site_key:
            webbrowser.open("http://" + site_key)
            speak(f"Opening {site_key}")
        else:
            speak(f"I don't have a direct shortcut for {site_key}. I'll search it on Google.")
            webbrowser.open("https://www.google.com/search?q=" + quote_plus(site_key))

def google_search(query: str):
    if not query:
        speak("What should I search for?")
        query = takeCommand()
    webbrowser.open("https://www.google.com/search?q=" + quote_plus(query))
    speak(f"Here are the search results for {query}.")

# --- Time & date ---
def tell_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The time is {now}")

def tell_date():
    today = datetime.date.today().strftime("%B %d, %Y")
    speak(f"Today's date is {today}")

# --- Notes ---
NOTES_FILE = "notes.json"

def write_note():
    speak("What should I write in the note?")
    content = takeCommand()
    if not content:
        speak("No content provided; note canceled.")
        return
    note = {"time": datetime.datetime.now().isoformat(), "content": content}
    notes = []
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                notes = json.load(f)
        except Exception:
            notes = []
    notes.append(note)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)
    speak("Note saved.")
    # optionally open notes file
    speak("Do you want me to open the notes file? Say yes or no.")
    ans = takeCommand().lower()
    if "yes" in ans:
        open_file(NOTES_FILE)

def open_file(path):
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])
    except Exception as e:
        speak("Unable to open file. " + str(e))

# --- Reminders (simple minutes-based reminder) ---
def set_reminder():
    speak("What should I remind you about?")
    message = takeCommand()
    if not message:
        speak("No message provided. Reminder canceled.")
        return
    speak("In how many minutes should I remind you?")
    mins_text = takeCommand()
    # try to parse integer minutes
    minutes = None
    for token in mins_text.split():
        try:
            minutes = int(token)
            break
        except:
            continue
    if minutes is None:
        speak("I couldn't parse the time in minutes. Reminder canceled.")
        return
    def _reminder():
        speak(f"Reminder: {message}")
    t = threading.Timer(minutes * 60, _reminder)
    t.daemon = True
    t.start()
    speak(f"Okay, I will remind you in {minutes} minutes.")

# --- Take photo (optional) ---
def take_photo():
    if cv2 is None:
        speak("OpenCV is not installed. Install opencv-python to use the camera.")
        return
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        speak("Could not access the camera.")
        return
    ret, frame = cam.read()
    if ret:
        fname = f"photo_{int(time.time())}.png"
        cv2.imwrite(fname, frame)
        speak(f"Photo taken and saved as {fname}")
        open_file(fname)
    else:
        speak("Failed to capture photo.")
    cam.release()

# --- System commands (safe) ---
def shutdown_system():
    speak("Do you really want to shutdown the computer? Say 'yes' to confirm.")
    ans = takeCommand().lower()
    if "yes" in ans or "confirm" in ans:
        system = platform.system()
        speak("Shutting down...")
        if system == "Windows":
            os.system("shutdown /s /t 5")
        elif system in ("Linux", "Darwin"):
            # For Linux/macOS this may prompt for password
            os.system("sudo shutdown now")
    else:
        speak("Shutdown canceled.")

def restart_system():
    speak("Do you really want to restart the computer? Say 'yes' to confirm.")
    ans = takeCommand().lower()
    if "yes" in ans or "confirm" in ans:
        system = platform.system()
        speak("Restarting...")
        if system == "Windows":
            os.system("shutdown /r /t 5")
        elif system in ("Linux","Darwin"):
            os.system("sudo reboot")
    else:
        speak("Restart canceled.")

# --- Small talk & helper ---
def small_talk(command: str):
    if "how are you" in command:
        speak("I am a program, but I'm functioning correctly. How can I help you?")
    elif "your name" in command or "who are you" in command:
        speak("I am your voice assistant. You can call me Assistant.")
    else:
        speak("Sorry, I didn't understand that. I can open websites, search Google, fetch Wikipedia, set reminders, write notes, and run system commands.")

# --- Main command processor ---
def process_command(command: str):
    cmd = command.lower()

    if cmd == "":
        return

    # Exit
    if any(x in cmd for x in ["exit", "quit", "goodbye", "stop", "bye"]):
        speak("Goodbye. Have a nice day!")
        raise SystemExit

    # Wikipedia
    if "wikipedia" in cmd:
        topic = cmd.replace("wikipedia", "").strip()
        search_wikipedia(topic, sentences=2)
        return

    # Open sites
    if cmd.startswith("open "):
        target = cmd.replace("open ", "").strip()
        open_website(target)
        return

    # Google search
    if "search for" in cmd or cmd.startswith("search "):
        # normalize
        q = cmd.replace("search for", "").replace("search", "").strip()
        google_search(q)
        return
    if "google " in cmd:
        q = cmd.replace("google", "").strip()
        google_search(q)
        return

    # Time & Date
    if "time" in cmd:
        tell_time()
        return
    if "date" in cmd:
        tell_date()
        return

    # Notes & reminders
    if "write a note" in cmd or "take note" in cmd or "note" in cmd:
        write_note()
        return
    if "remind me" in cmd or "set reminder" in cmd:
        set_reminder()
        return

    # Take photo
    if "take a photo" in cmd or "take photo" in cmd or "capture photo" in cmd:
        take_photo()
        return

    # Wikipedia alternative phrasing: "who is ..." "what is ..."
    if cmd.startswith("who is ") or cmd.startswith("what is ") or cmd.startswith("tell me about "):
        topic = cmd.replace("who is", "").replace("what is", "").replace("tell me about", "").strip()
        search_wikipedia(topic, sentences=2)
        return

    # System commands
    if "shutdown" in cmd:
        shutdown_system()
        return
    if "restart" in cmd or "reboot" in cmd:
        restart_system()
        return

    # Open common shortcuts
    for key in WEBSITE_MAP.keys():
        if key in cmd and "open" in cmd:
            open_website(key)
            return

    # small talk fallback
    small_talk(cmd)

# --- Entry point ---
def main():
    wishMe()
    try:
        while True:
            speak("Listening for your command.")
            query = takeCommand()
            if not query:
                continue
            try:
                process_command(query)
            except SystemExit:
                break
            # tiny idle sleep
            time.sleep(0.5)
    except KeyboardInterrupt:
        speak("Assistant terminated by user. Bye!")

if __name__ == "__main__":
    main()
