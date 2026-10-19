"""FRIDAY V1 - a small Windows voice assistant.

Run: python friday.py
Say "Friday" followed by a request, for example: "Friday, what time is it?"
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import random
import re
import subprocess
import threading
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

import speech_recognition as sr
from dotenv import load_dotenv

from ai_brain import LocalAIUnavailable, ask_local_ai, route_spoken_intent
from notes import NOTES_FILE, recent_notes, save_note
from web_lookup import spoken_web_answer
from youtube_music import YouTubePlaybackUnavailable, find_first_video


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

NAME = "friday"
LISTEN_TIMEOUT_SECONDS = 6
PHRASE_LIMIT_SECONDS = 12
SPEECH_LANGUAGE = os.getenv("SPEECH_LANGUAGE", "en-IN")
MIC_SENSITIVITY = float(os.getenv("MIC_SENSITIVITY", "1.7"))
MIC_CALIBRATION_SECONDS = 0.8
FRIDAY_VOICE = os.getenv("FRIDAY_VOICE", "").strip()
SETTINGS_FILE = PROJECT_DIR / "friday_settings.json"


class Friday:
    def __init__(self) -> None:
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.recognizer.dynamic_energy_threshold = True
        self.microphone_index = self._get_microphone_index()
        self.microphone_calibrated = False
        self.timers: list[threading.Timer] = []
        self.client = self._create_ai_client()

    @staticmethod
    def _get_microphone_index() -> int | None:
        """Use the default Windows microphone unless an index is configured."""
        value = os.getenv("MIC_DEVICE_INDEX", "").strip()
        if not value:
            return None

    @staticmethod
    def available_voices() -> list[str]:
        """Return Windows voices installed on this computer."""
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$voice.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name } | ConvertTo-Json -Compress"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                check=True,
            )
            voices = json.loads(result.stdout)
            return voices if isinstance(voices, list) else [voices]
        except Exception:
            return []

    @staticmethod
    def selected_voice() -> str:
        if FRIDAY_VOICE:
            return FRIDAY_VOICE
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return str(settings.get("voice", "")).strip()
        except (OSError, json.JSONDecodeError):
            return ""

    @staticmethod
    def set_selected_voice(voice_name: str) -> None:
        SETTINGS_FILE.write_text(
            json.dumps({"voice": voice_name}, indent=2), encoding="utf-8"
        )
        try:
            return int(value)
        except ValueError:
            print("Ignoring invalid MIC_DEVICE_INDEX; using the Windows default microphone.")
            return None

    @staticmethod
    def _create_ai_client():
        """Create an optional OpenAI-compatible client only if configured."""
        api_key = os.getenv("AI_API_KEY", "").strip()
        if not api_key:
            return None

        try:
            from openai import OpenAI

            options = {"api_key": api_key}
            base_url = os.getenv("AI_BASE_URL", "").strip()
            if base_url:
                options["base_url"] = base_url
            return OpenAI(**options)
        except Exception as error:
            print(f"AI setup unavailable: {error}")
            return None

    def speak(self, message: str, rate: int | None = None) -> None:
        print(f"FRIDAY: {message}")
        # Use Windows' own speech engine. It is more dependable than the
        # third-party engine used by earlier versions of this project.
        message_bytes = base64.b64encode(message.encode("utf-8")).decode("ascii")
        voice_bytes = base64.b64encode(self.selected_voice().encode("utf-8")).decode("ascii")
        script = (
            "$message = [Text.Encoding]::UTF8.GetString("
            f"[Convert]::FromBase64String('{message_bytes}')); "
            "$requestedVoice = [Text.Encoding]::UTF8.GetString("
            f"[Convert]::FromBase64String('{voice_bytes}')); "
            "Add-Type -AssemblyName System.Speech; "
            "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$installed = @($voice.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }); "
            "if ($requestedVoice -and $installed -contains $requestedVoice) { $voice.SelectVoice($requestedVoice) } "
            "elseif ($installed -contains 'Microsoft Mark') { $voice.SelectVoice('Microsoft Mark') } "
            "elseif ($installed -contains 'Microsoft David') { $voice.SelectVoice('Microsoft David') }; "
            f"$voice.Rate = {rate if rate is not None else -1}; "
            "$voice.Volume = 100; $voice.Speak($message)"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"Windows speech error: {error}")

    @staticmethod
    def send_media_key(key_code: int) -> None:
        """Send a global Windows media key to the active music player."""
        script = (
            'Add-Type @"\n'
            'using System; using System.Runtime.InteropServices;\n'
            'public class FridayMedia {\n'
            '  [DllImport("user32.dll")] public static extern void keybd_event('
            'byte key, byte scan, uint flags, UIntPtr extra);\n'
            '}\n'
            '"@; '
            f'[FridayMedia]::keybd_event({key_code}, 0, 0, [UIntPtr]::Zero); '
            f'[FridayMedia]::keybd_event({key_code}, 0, 2, [UIntPtr]::Zero)'
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def listen(self) -> str:
        try:
            with sr.Microphone(device_index=self.microphone_index) as source:
                if not self.microphone_calibrated:
                    print("Calibrating microphone…")
                    self.recognizer.adjust_for_ambient_noise(
                        source, duration=MIC_CALIBRATION_SECONDS
                    )
                    # A lower threshold makes the microphone respond to softer speech.
                    self.recognizer.energy_threshold = max(
                        75, self.recognizer.energy_threshold / MIC_SENSITIVITY
                    )
                    self.microphone_calibrated = True
                print("Listening…")
                audio = self.recognizer.listen(
                    source,
                    timeout=LISTEN_TIMEOUT_SECONDS,
                    phrase_time_limit=PHRASE_LIMIT_SECONDS,
                )
            heard = self.recognizer.recognize_google(
                audio, language=SPEECH_LANGUAGE
            ).lower()
            print(f"You: {heard}")
            return heard
        except sr.WaitTimeoutError:
            print("No speech detected. Listening again…")
            return ""
        except sr.UnknownValueError:
            print("I heard audio but could not understand it. Listening again…")
            return ""
        except sr.RequestError:
            self.speak("Speech recognition is unavailable. Please check your internet connection.")
            return ""
        except OSError as error:
            self.microphone_calibrated = False
            self.speak("I cannot access the microphone.")
            print(f"Microphone error: {error}")
            return ""

    def _start_timer(self, seconds: int) -> None:
        def timer_finished() -> None:
            self.speak("Your timer is complete.")

        timer = threading.Timer(seconds, timer_finished)
        timer.daemon = True
        self.timers.append(timer)
        timer.start()

    def ask_ai(self, question: str) -> str:
        try:
            return ask_local_ai(question)
        except LocalAIUnavailable:
            pass

        if not self.client:
            return (
                "My local AI brain is not ready yet. Run SETUP LOCAL AI in the FRIDAY "
                "folder, then I will be able to understand general questions."
            )

        model = os.getenv("AI_MODEL", "").strip()
        if not model:
            return "Please set AI_MODEL in your .env file before asking AI questions."

        try:
            response = self.client.responses.create(
                model=model,
                instructions=(
                    "You are FRIDAY, a friendly Windows voice assistant. "
                    "Give short, helpful spoken answers."
                ),
                input=question,
            )
            return response.output_text
        except Exception as error:
            print(f"AI error: {error}")
            return "I could not reach the AI service right now."

    def handle(self, command: str, allow_ai_routing: bool = True) -> bool:
        command = command.lower().strip()
        # Remove polite filler so requests can be phrased naturally.
        command = re.sub(
            r"^(?:can you|could you|would you|please|hey friday|friday)[, ]+",
            "",
            command,
        ).strip()

        if not command:
            return True

        if any(phrase in command for phrase in ("what can you do", "help", "commands")):
            self.speak(
                "You can ask for the time or date, open Chrome, YouTube, Google, "
                "Calculator, Notepad, Settings, Files, Downloads, or Camera, search "
                "the web or Spotify, control music playback, hear a joke, or say stop."
            )
            return True

        if any(word in command for word in ("stop", "shutdown", "goodbye", "exit")):
            self.speak("FRIDAY shutting down. Goodbye.")
            return False

        if "time" in command:
            now = dt.datetime.now().strftime("%I:%M %p")
            self.speak(f"It is {now}.")
            return True

        if "date" in command or "day is it" in command or "what day" in command:
            today = dt.datetime.now().strftime("%A, %d %B %Y")
            self.speak(f"Today is {today}.")
            return True

        if command.startswith("remember ") or command.startswith("make a note "):
            note = re.sub(r"^(?:remember|make a note)\s+", "", command).strip()
            if note:
                save_note(note)
                self.speak("I saved that note.")
            return True

        if any(phrase in command for phrase in ("read my notes", "what do you remember", "my notes")):
            notes = recent_notes()
            if notes:
                self.speak("Here are your latest notes. " + " ".join(notes))
            else:
                self.speak("You do not have any saved notes yet.")
            return True

        if "open notes" in command:
            if not NOTES_FILE.exists():
                NOTES_FILE.touch()
            os.startfile(NOTES_FILE)
            self.speak("Opening your notes.")
            return True

        if "battery" in command:
            result = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_Battery | Select-Object -First 1 -ExpandProperty EstimatedChargeRemaining)",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            percentage = result.stdout.strip()
            if percentage.isdigit():
                self.speak(f"Your battery is at {percentage} percent.")
            else:
                self.speak("I cannot find a battery. This may be a desktop computer.")
            return True

        timer_match = re.search(
            r"(?:set )?(?:a )?timer(?: for| in)?\s*(\d+)\s*(second|seconds|minute|minutes|hour|hours)",
            command,
        )
        if timer_match:
            quantity = int(timer_match.group(1))
            unit = timer_match.group(2)
            multiplier = 3600 if unit.startswith("hour") else 60 if unit.startswith("minute") else 1
            self._start_timer(quantity * multiplier)
            self.speak(f"Timer set for {quantity} {unit}.")
            return True

        if "test voice" in command or "voice test" in command:
            self.speak("Voice test successful.")
            return True

        if "open youtube" in command:
            self.speak("Opening YouTube.")
            webbrowser.open("https://www.youtube.com")
            return True

        if "open google" in command:
            self.speak("Opening Google.")
            webbrowser.open("https://www.google.com")
            return True

        if "open chrome" in command:
            self.speak("Opening Chrome.")
            try:
                subprocess.Popen(["cmd", "/c", "start", "", "chrome"], shell=False)
            except OSError:
                webbrowser.open("https://www.google.com")
            return True

        if "spotify" in command and ("search" in command or "find" in command):
            query = re.sub(r"^.*?(?:search|find)(?:\s+spotify)?(?:\s+for)?\s*", "", command).strip()
            if query:
                self.speak(f"Searching Spotify for {query}.")
                webbrowser.open(f"https://open.spotify.com/search/{quote_plus(query)}")
                return True

        if "next song" in command or "next track" in command:
            self.speak("Skipping to the next track.")
            self.send_media_key(0xB0)
            return True

        if "previous song" in command or "previous track" in command:
            self.speak("Going back one track.")
            self.send_media_key(0xB1)
            return True

        if "pause spotify" in command or "pause music" in command:
            self.speak("Pausing music.")
            self.send_media_key(0xB3)
            return True

        if "play spotify" in command or "resume music" in command or "play music" in command:
            self.speak("Playing music.")
            self.send_media_key(0xB3)
            return True

        if command.startswith("play "):
            song = command.removeprefix("play ").strip()
            if song:
                song = re.sub(r"\s+(?:on\s+)?youtube$", "", song).strip()
                try:
                    video_id, title = find_first_video(song)
                    self.speak(f"Playing {title}.")
                    webbrowser.open(
                        f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
                    )
                except YouTubePlaybackUnavailable:
                    self.speak(f"I could not start {song}, so I opened the YouTube results.")
                    webbrowser.open(
                        f"https://www.youtube.com/results?search_query={quote_plus(song)}"
                    )
                return True

        desktop_apps = {
            "calculator": ("calc", "Calculator"),
            "notepad": ("notepad", "Notepad"),
            "settings": ("start ms-settings:", "Settings"),
            "camera": ("start microsoft.windows.camera:", "Camera"),
            "files": ("explorer", "File Explorer"),
            "file explorer": ("explorer", "File Explorer"),
            "downloads": ("explorer shell:Downloads", "Downloads"),
            "documents": ("explorer shell:Personal", "Documents"),
            "spotify": ("start spotify:", "Spotify"),
        }
        for app_name, (launch_command, display_name) in desktop_apps.items():
            launch_words = (
                "open", "launch", "start", "run", "show", "bring up", "take me to",
            )
            if app_name in command and any(word in command for word in launch_words):
                self.speak(f"Opening {display_name}.")
                subprocess.Popen(
                    ["cmd", "/c", launch_command],
                    shell=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True

        if "joke" in command:
            self.speak(random.choice([
                "Why do programmers prefer dark mode? Because light attracts bugs.",
                "Why was the computer cold? It left its Windows open.",
                "I would tell you a UDP joke, but you might not get it.",
            ]))
            return True

        if "who are you" in command:
            self.speak("I am FRIDAY, your personal Windows voice assistant.")
            return True

        if "send email" in command or "send an email" in command or "compose email" in command:
            self.speak(
                "Use the Compose Email button in my dashboard. I will always show the "
                "message and ask you before sending it."
            )
            return True

        if any(word in command for word in ("search", "google", "look up", "find")):
            query = re.sub(
                r"^.*?(?:\bsearch|\bgoogle|\blook up|\bfind)(?:\s+for|\s+about)?\s*",
                "",
                command,
            ).strip()
            if query:
                self.speak(f"Looking up {query}.")
                answer = spoken_web_answer(query)
                if answer:
                    self.speak(answer)
                else:
                    self.speak(self.ask_ai(query))
                return True
            self.speak("What would you like me to search for?")
            return True

        if allow_ai_routing:
            routed = route_spoken_intent(command)
            if routed and routed != "NONE":
                command_map = {
                    "TIME": "time",
                    "DATE": "date",
                    "PAUSE": "pause music",
                    "NEXT": "next song",
                    "PREVIOUS": "previous song",
                    "JOKE": "tell me a joke",
                    "HELP": "help",
                }
                if routed.startswith("OPEN:"):
                    routed_command = f"open {routed.partition(':')[2].strip().lower()}"
                elif routed.startswith("SEARCH:"):
                    routed_command = f"search for {routed.partition(':')[2].strip()}"
                elif routed.startswith("PLAY:"):
                    routed_command = f"play {routed.partition(':')[2].strip()}"
                else:
                    routed_command = command_map.get(routed, "")
                if routed_command:
                    return self.handle(routed_command, allow_ai_routing=False)

        self.speak(self.ask_ai(command))
        return True

    def run(self) -> None:
        print("Using Windows' current default microphone.")
        self.speak("FRIDAY online. Say Friday followed by a command.")
        waiting_for_command = False
        while True:
            spoken = self.listen()
            if not spoken:
                continue

            if waiting_for_command:
                command = spoken
                waiting_for_command = False
            else:
                if NAME not in spoken:
                    continue
                command = spoken.split(NAME, 1)[1].strip(" ,.!?")

            if not command:
                waiting_for_command = True
                continue
            if not self.handle(command):
                break


if __name__ == "__main__":
    Friday().run()
