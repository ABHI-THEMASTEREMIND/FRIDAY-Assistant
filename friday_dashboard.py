"""Futuristic desktop dashboard for FRIDAY V1.

Run this file instead of friday.py to use the visual interface.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from friday import Friday, NAME


BG = "#06121d"
PANEL = "#0a2233"
CYAN = "#43f4ff"
MUTED = "#82a9b8"
TEXT = "#e9fbff"
GREEN = "#64f5ae"
RED = "#ff6b81"


class FridayDashboard:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("FRIDAY — Personal Assistant")
        self.root.geometry("940x640")
        self.root.minsize(720, 520)
        self.root.configure(bg=BG)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.running = threading.Event()
        self.worker: threading.Thread | None = None
        self.assistant: Friday | None = None
        self._build()
        self.root.after(100, self._process_events)
        self.root.after(350, self.start)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=34, pady=(28, 10))
        tk.Label(
            header, text="F R I D A Y", bg=BG, fg=CYAN,
            font=("Segoe UI", 28, "bold"),
        ).pack(side="left")
        self.status = tk.Label(
            header, text="●  STANDBY", bg=BG, fg=MUTED,
            font=("Segoe UI", 11, "bold"),
        )
        self.status.pack(side="right", pady=10)

        center = tk.Frame(self.root, bg=BG)
        center.pack(fill="both", expand=True, padx=34, pady=12)

        left = tk.Frame(center, bg=PANEL, highlightbackground="#15506a", highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        right = tk.Frame(center, bg=PANEL, highlightbackground="#15506a", highlightthickness=1)
        right.pack(side="right", fill="y")

        self.orb = tk.Canvas(left, width=260, height=230, bg=PANEL, highlightthickness=0)
        self.orb.pack(pady=(35, 4))
        self._draw_orb(CYAN)
        self.state_label = tk.Label(
            left, text="READY FOR YOUR COMMAND", bg=PANEL, fg=TEXT,
            font=("Segoe UI", 13, "bold"),
        )
        self.state_label.pack(pady=(5, 16))
        self.last_heard = tk.Label(
            left, text="Say “Friday” followed by a command", bg=PANEL, fg=MUTED,
            wraplength=440, font=("Segoe UI", 10),
        )
        self.last_heard.pack(padx=24, pady=(0, 24))

        tk.Label(right, text="SYSTEM COMMANDS", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=24, pady=(26, 10))
        command_text = (
            "• What time is it?\n"
            "• What is today’s date?\n"
            "• Open Chrome / YouTube\n"
            "• Open Calculator / Notepad\n"
            "• Open Settings / Files\n"
            "• Open Downloads / Camera\n"
            "• Open Spotify\n"
            "• Spotify search for …\n"
            "• Play / pause music\n"
            "• Play <song name> on YouTube\n"
            "• Next / previous song\n"
            "• Search for … (spoken answer)\n"
            "• Remember … / read my notes\n"
            "• Set a timer for 5 minutes\n"
            "• What is my battery level?\n"
            "• Tell me a joke\n"
            "• Stop"
        )
        tk.Label(right, text=command_text, justify="left", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=24)

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=34, pady=(6, 28))
        self.stop_button = tk.Button(
            controls, text="EXIT FRIDAY", command=self.close, bg="#14384b", fg=TEXT,
            activebackground="#235a73", relief="flat", padx=18, pady=11,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
        )
        self.stop_button.pack(side="left")

        tk.Button(
            controls, text="COMPOSE EMAIL", command=self.compose_email, bg="#14384b", fg=TEXT,
            activebackground="#235a73", relief="flat", padx=14, pady=11,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
        ).pack(side="left", padx=10)

        tk.Button(
            controls, text="CHANGE VOICE", command=self.choose_voice, bg="#14384b", fg=TEXT,
            activebackground="#235a73", relief="flat", padx=14, pady=11,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
        ).pack(side="left")

        self.typed = tk.Entry(controls, bg="#0c2a3a", fg=TEXT, insertbackground=TEXT,
                              relief="flat", font=("Segoe UI", 10))
        self.typed.pack(side="left", fill="x", expand=True, padx=(12, 8), ipady=10)
        self.typed.bind("<Return>", self.run_typed_command)
        self.send_button = tk.Button(
            controls, text="SEND", command=self.run_typed_command, bg="#14384b", fg=TEXT,
            activebackground="#235a73", relief="flat", padx=14, pady=11,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
        )
        self.send_button.pack(side="right")

    def _draw_orb(self, color: str) -> None:
        self.orb.delete("all")
        self.orb.create_oval(24, 10, 236, 222, outline="#15506a", width=2)
        self.orb.create_oval(43, 29, 217, 203, outline=color, width=3)
        self.orb.create_oval(69, 55, 191, 177, fill="#0d3850", outline=color, width=2)
        self.orb.create_oval(101, 87, 159, 145, fill=color, outline="")
        self.orb.create_text(130, 116, text="F", fill="#001319", font=("Segoe UI", 24, "bold"))

    def _set_state(self, label: str, color: str, detail: str | None = None) -> None:
        self.status.configure(text=f"●  {label}", fg=color)
        self.state_label.configure(text=label)
        self._draw_orb(color)
        if detail:
            self.last_heard.configure(text=detail)

    def start(self) -> None:
        if self.running.is_set():
            return
        self.running.set()
        self.worker = threading.Thread(target=self._voice_loop, daemon=True)
        self.worker.start()

    def stop(self) -> None:
        self.running.clear()
        self._set_state("OFFLINE", MUTED, "FRIDAY is offline")

    def _voice_loop(self) -> None:
        self.assistant = Friday()
        original_speak = self.assistant.speak

        def speak_with_ui(message: str, rate: int | None = None) -> None:
            self.events.put(("speaking", message))
            original_speak(message, rate=rate)

        self.assistant.speak = speak_with_ui
        greeting = "FRIDAY online. How can I help you, Mister Abhinav?"
        self.events.put(("speaking", greeting))
        original_speak(greeting, rate=3)
        waiting_for_command = False
        while self.running.is_set():
            prompt = "Waiting for your command…" if waiting_for_command else "Waiting for “Friday”…"
            self.events.put(("listening", prompt))
            spoken = self.assistant.listen()
            if not spoken:
                continue
            self.events.put(("heard", spoken))
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
            if not self.assistant.handle(command):
                self.running.clear()
                self.events.put(("stopped", "FRIDAY is offline"))

    def choose_voice(self) -> None:
        voices = Friday.available_voices()
        if not voices:
            messagebox.showerror("FRIDAY", "I could not find any Windows voices.", parent=self.root)
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("FRIDAY — Choose Voice")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="CHOOSE FRIDAY'S VOICE", bg=BG, fg=CYAN,
                 font=("Segoe UI", 14, "bold")).pack(padx=24, pady=(24, 12))
        tk.Label(dialog, text="Install more voices in Windows Settings to see them here.", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(padx=24, pady=(0, 12))
        selected = tk.StringVar(value=Friday.selected_voice() or voices[0])
        picker = ttk.Combobox(dialog, textvariable=selected, values=voices, state="readonly", width=40)
        picker.pack(padx=24, pady=(0, 18))

        def apply_voice() -> None:
            voice = selected.get()
            Friday.set_selected_voice(voice)
            dialog.destroy()
            self.events.put(("speaking", f"Voice changed to {voice}."))
            if self.assistant:
                threading.Thread(target=self.assistant.speak, args=("Voice updated.",), daemon=True).start()

        tk.Button(dialog, text="USE THIS VOICE", command=apply_voice, bg=CYAN, fg="#001319",
                  activebackground="#9af8ff", relief="flat", padx=16, pady=10,
                  font=("Segoe UI", 10, "bold"), cursor="hand2").pack(pady=(0, 24))

    def compose_email(self) -> None:
        """Compose an email using either voice or typing."""
        dialog = tk.Toplevel(self.root)
        dialog.title("FRIDAY - Compose Email")
        dialog.configure(bg=BG)
        dialog.geometry("600x500")
        dialog.resizable(False, False)

        current_question = {"value": 0}

        questions = [
            "Who should I send the email to?",
            "What is the subject?",
            "What should I write in the email?",
            "Should I send the email?"
        ]

        answers = {
            "recipient": "",
            "subject": "",
            "body": ""
        }

        tk.Label(
            dialog,
            text="F R I D A Y  —  EMAIL",
            bg=BG,
            fg=CYAN,
            font=("Segoe UI", 20, "bold")
        ).pack(pady=(20, 10))

        question_label = tk.Label(
            dialog,
            text=questions[0],
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 13, "bold"),
            wraplength=520
        )
        question_label.pack(pady=15)

        entry = tk.Entry(
            dialog,
            bg="#0c2a3a",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 12)
        )
        entry.pack(
            fill="x",
            padx=40,
            pady=10,
            ipady=12
        )

        status_label = tk.Label(
            dialog,
            text="Type your answer or press 🎤 Voice",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10)
        )
        status_label.pack(pady=5)

        def clean_email(text: str) -> str:
            text = text.lower().strip()

            replacements = {
                " at the rate ": "@",
                " at rate ": "@",
                " at ": "@",
                " dot ": ".",
                " point ": ".",
                " underscore ": "_",
                " dash ": "-",
                " hyphen ": "-"
            }

            for old, new in replacements.items():
                text = text.replace(old, new)

            text = text.replace(" ", "")

            return text

        def ask_next() -> None:
            answer = entry.get().strip()

            if not answer:
                status_label.config(
                    text="Please type something or use Voice."
                )
                return

            step = current_question["value"]

            if step == 0:
                answer = clean_email(answer)

                if "@" not in answer or "." not in answer.split("@")[-1]:
                    status_label.config(
                        text=f"That doesn't look like a valid email: {answer}"
                    )
                    return

                answers["recipient"] = answer

            elif step == 1:
                answers["subject"] = answer

            elif step == 2:
                answers["body"] = answer

            elif step == 3:
                confirmation = answer.lower()

                if confirmation in (
                    "yes",
                    "yeah",
                    "yep",
                    "ok",
                    "okay",
                    "send",
                    "send it",
                    "confirm"
                ):
                    status_label.config(
                        text="Sending email..."
                    )

                    threading.Thread(
                        target=self._send_email_worker,
                        args=(
                            answers["recipient"],
                            answers["subject"],
                            answers["body"],
                            dialog
                        ),
                        daemon=True
                    ).start()

                    return

                else:
                    status_label.config(
                        text="Email cancelled."
                    )
                    return

            current_question["value"] += 1
            step = current_question["value"]

            entry.delete(0, "end")

            if step == 1:
                question_label.config(
                    text="What is the subject?"
                )

            elif step == 2:
                question_label.config(
                    text="What should I write in the email?"
                )

            elif step == 3:
                question_label.config(
                    text=(
                        f"To: {answers['recipient']}\n"
                        f"Subject: {answers['subject']}\n\n"
                        f"Message: {answers['body']}\n\n"
                        "Should I send it?"
                    )
                )

                entry.focus_set()

        def voice_answer() -> None:
                """Listen for an answer using FRIDAY's microphone."""
                try:
                    status_label.config(
                        text="🎤 Listening... Speak now."
                    )

                    answer = self.assistant.listen()

                    if not answer:
                        self.root.after(
                            0,
                            lambda: status_label.config(
                                text="I didn't hear anything. Try again."
                            )
                        )
                        return

                    self.root.after(
                        0,
                        lambda: process_voice_answer(answer)
                    )

                except Exception as error:
                    print(f"Voice email error: {error}")

                    self.root.after(
                        0,
                        lambda: status_label.config(
                            text=f"Voice error: {error}"
                        )
                    )
        def process_voice_answer(answer: str) -> None:
            answer = answer.strip().lower()

            # Step 3 = email confirmation
            if current_question["value"] == 3:
                if answer in (
                    "yes",
                    "yeah",
                    "yep",
                    "yes send it",
                    "send",
                    "send it",
                    "okay",
                    "ok",
                    "confirm",
                ):
                    status_label.config(text="Sending email...")

                    threading.Thread(
                        target=self._send_email_worker,
                        args=(
                            answers["recipient"],
                            answers["subject"],
                            answers["body"],
                            dialog,
                        ),
                        daemon=True,
                    ).start()

                else:
                    status_label.config(text="Email cancelled.")
                    self.assistant.speak(
                        "Okay, I won't send the email."
                    )

                return

            # Normal voice answers: recipient, subject, message
            entry.delete(0, "end")
            entry.insert(0, answer)

            status_label.config(
                text=f"Heard: {answer}"
            )

            ask_next()

        def start_voice() -> None:
            threading.Thread(
                target=voice_answer,
                daemon=True
            ).start()

        button_frame = tk.Frame(
            dialog,
            bg=BG
        )
        button_frame.pack(
            fill="x",
            padx=40,
            pady=20
        )

        tk.Button(
            button_frame,
            text="🎤 VOICE",
            command=start_voice,
            bg="#14384b",
            fg=TEXT,
            activebackground="#235a73",
            relief="flat",
            padx=20,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        ).pack(
            side="left"
        )

        tk.Button(
            button_frame,
            text="NEXT",
            command=ask_next,
            bg="#14384b",
            fg=TEXT,
            activebackground="#235a73",
            relief="flat",
            padx=25,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        ).pack(
            side="right"
        )

        entry.bind(
            "<Return>",
            lambda event: ask_next()
        )

        entry.focus_set()
    def _send_email_worker(self, recipient: str, subject: str, body: str, dialog: tk.Toplevel) -> None:
        self.events.put(("speaking", "Preparing your email."))
        try:
            from gmail_service import GmailSetupError, send_email

            send_email(recipient, subject, body)
            message = "Your email was sent."
            self.events.put(("speaking", message))
            self.root.after(0, dialog.destroy)
            self.root.after(0, lambda: messagebox.showinfo("FRIDAY", message, parent=self.root))
        except GmailSetupError as error:
            message = f"Gmail setup is needed: {error}"
            self.events.put(("speaking", message))
            self.root.after(0, lambda: messagebox.showerror("FRIDAY", message, parent=self.root))
        except Exception as error:
            message = f"I could not send that email: {error}"
            self.events.put(("speaking", message))
            self.root.after(0, lambda: messagebox.showerror("FRIDAY", message, parent=self.root))

    def run_typed_command(self, _event=None) -> None:
        command = self.typed.get().strip()
        if not command:
            self.last_heard.configure(text="Type a question or command first.")
            return
        self.typed.delete(0, "end")
        self.typed.configure(state="disabled")
        self.send_button.configure(state="disabled")
        self.events.put(("heard", command))
        threading.Thread(target=self._handle_typed, args=(command,), daemon=True).start()

    def _handle_typed(self, command: str) -> None:
        try:
            if not self.assistant:
                self.assistant = Friday()
                original_speak = self.assistant.speak

                def speak_with_ui(message: str) -> None:
                    self.events.put(("speaking", message))
                    original_speak(message)

                self.assistant.speak = speak_with_ui
            if not self.assistant.handle(command):
                self.events.put(("stopped", "FRIDAY is offline"))
        except Exception as error:
            print(f"Typed-command error: {error}")
            self.events.put(("error", f"Typed command failed: {error}"))
        finally:
            self.root.after(0, self._enable_typed_input)

    def _enable_typed_input(self) -> None:
        self.typed.configure(state="normal")
        self.send_button.configure(state="normal")
        self.typed.focus_set()

    def _process_events(self) -> None:
        while not self.events.empty():
            event, detail = self.events.get()
            if event == "listening":
                self._set_state("LISTENING", GREEN, detail)
            elif event == "heard":
                self._set_state("PROCESSING", CYAN, f"You: {detail}")
            elif event == "speaking":
                self._set_state("SPEAKING", CYAN, f"FRIDAY: {detail}")
            elif event == "stopped":
                self.stop()
            elif event == "error":
                self._set_state("ERROR", RED, detail)
        self.root.after(100, self._process_events)

    def close(self) -> None:
        self.running.clear()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    FridayDashboard().run()
