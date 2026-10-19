# FRIDAY

FRIDAY is a Windows desktop voice assistant with a futuristic dashboard. It listens for the wake word **“Friday”**, speaks replies, understands natural requests with a local AI model, and includes useful PC, music, notes, timer, web-answer, and Gmail features.

## Features

- Wake-word voice control: say **“Friday”**, then give your command.
- Dashboard with live listening and speaking status.
- Local AI brain powered by Ollama — no paid AI API required.
- Natural requests, such as “Could you open the calculator for me?”
- Opens common Windows tools: Chrome, YouTube, Calculator, Notepad, Settings, File Explorer, Downloads, Documents, Camera, and Spotify.
- Plays a requested song from YouTube.
- Speaks concise web lookup results instead of opening Google by default.
- Local notes, timers, battery-level checks, jokes, date, and time.
- Gmail compose window with a mandatory confirmation before an email is sent.
- Voice selector for installed Windows voices.

## Requirements

- Windows 10 or Windows 11
- Python 3.12 or newer
- A working microphone
- Internet connection for speech recognition, web lookups, YouTube, and Gmail
- Ollama for the local AI features

## Installation

1. Clone or download this repository.
2. Open Command Prompt in the project folder.
3. Install Python packages:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Double-click `SETUP_LOCAL_AI.bat`.
   - Install Ollama from the official page it opens.
   - Return to the script and press a key to download the local `qwen3:4b` model.
5. Start FRIDAY:

   ```powershell
   python friday_dashboard.py
   ```

For later dependency updates, run `UPDATE_FRIDAY.bat`.

## Example commands

- “Friday, what time is it?”
- “Friday, could you open the calculator for me?”
- “Friday, play Blinding Lights.”
- “Friday, search for black holes.”
- “Friday, remember that my test is Monday.”
- “Friday, read my notes.”
- “Friday, set a timer for 5 minutes.”
- “Friday, what is my battery level?”

## Gmail setup (optional)

Gmail is optional and is only used when you press **Compose Email** in the dashboard.

1. Create a Google Cloud project and enable the Gmail API.
2. Create a **Desktop app** OAuth client.
3. Download the OAuth file, rename it to `credentials.json`, and place it in this folder.
4. Start FRIDAY and use **Compose Email**. Google opens a secure sign-in page the first time.

FRIDAY always shows the recipient, subject, and message and asks for confirmation before it sends an email.

## Choosing a voice

Install additional Windows voices through **Settings → Time & language → Speech → Manage voices → Add voices**. Then open FRIDAY and click **CHANGE VOICE** in the dashboard.

## Privacy and security

- Local AI questions are processed by Ollama on your computer.
- Gmail requires your own Google authorization; FRIDAY never needs your Gmail password.
- Do **not** upload `.env`, `credentials.json`, `gmail_token.json`, `friday_settings.json`, or `friday_notes.txt` to GitHub.

## Notes

- YouTube playback opens a matching video with autoplay requested; browser autoplay settings may still require one click.
- This project is a personal assistant prototype. Review commands and permissions before using it with personal accounts.
