import json
import os
import shutil
import subprocess
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from google import genai
from google.genai import types

SYSTEM_PROMPT = (
    "You are a real-life automation planner. "
    "Return ONLY valid JSON with schema: "
    "{\"action\": string, \"args\": object, \"explanation\": string}. "
    "Allowed actions include voice and system management features: transcribe_voice, speak_text, "
    "set_voice_profile, open_application, close_application, list_processes, create_file, create_folder, system_status_check."
)

VOICE_PROFILES = {
    "female_1": {"gender": "female", "index_hint": 0},
    "female_2": {"gender": "female", "index_hint": 1},
    "female_3": {"gender": "female", "index_hint": 2},
    "female_4": {"gender": "female", "index_hint": 3},
    "male_1": {"gender": "male", "index_hint": 0},
    "male_2": {"gender": "male", "index_hint": 1},
    "male_3": {"gender": "male", "index_hint": 2},
    "male_4": {"gender": "male", "index_hint": 3},
}

DEFAULT_FEATURE_READOUT = [
    "Voice Input / Voice Output",
    "8 Voice Profiles (4 Male + 4 Female)",
    "Open / Close Applications",
    "Process Monitoring",
    "File / Folder Creation",
    "Weather Check",
    "WhatsApp Message Draft",
    "System Status Check (Battery/CPU/RAM/Internet)",
]

@dataclass
class Message:
    role: str
    content: str

class OSActions:
    def __init__(self, workspace: str, voice_profile: str = "female_1") -> None:
        self.workspace = Path(workspace).resolve()
        self.data_dir = self.workspace / ".assistant_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.voice_profile = voice_profile if voice_profile in VOICE_PROFILES else "female_1"

    def _safe_path(self, relative_or_abs: str) -> Path:
        p = Path(relative_or_abs)
        candidate = (self.workspace / p).resolve() if not p.is_absolute() else p.resolve()
        if self.workspace not in [candidate, *candidate.parents]:
            raise ValueError("Path is outside AUTOMATION_WORKSPACE")
        return candidate

    def _json_file(self, name: str) -> Path:
        return self.data_dir / f"{name}.json"

    def _load_json(self, name: str) -> List[Dict[str, Any]]:
        path = self._json_file(name)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json(self, name: str, data: List[Dict[str, Any]]) -> None:
        self._json_file(name).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def set_voice_profile(self, profile: str) -> str:
        if profile not in VOICE_PROFILES:
            return f"Invalid profile. Use one of: {', '.join(VOICE_PROFILES.keys())}"
        self.voice_profile = profile
        return f"Voice profile set to: {profile}"

    def create_file(self, path: str, content: str = "") -> str:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"File created: {target}"

    def create_folder(self, path: str) -> str:
        target = self._safe_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return f"Folder created: {target}"

    def list_voice_profiles(self) -> str:
        return "\n".join(VOICE_PROFILES.keys())

    def readout_features(self) -> str:
        return "Available features:\n- " + "\n- ".join(DEFAULT_FEATURE_READOUT)

    def transcribe_voice(self, timeout: int = 8) -> str:
        try:
            import speech_recognition as sr
        except ImportError:
            return "Voice input dependency missing. Install: pip install SpeechRecognition pyaudio"
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=timeout)
        try:
            return r.recognize_google(audio)
        except Exception as exc:
            return f"Voice transcription failed: {exc}"

    def speak_text(self, text: str) -> str:
        try:
            import pyttsx3
        except ImportError:
            return "Voice output dependency missing. Install: pip install pyttsx3"
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        profile = VOICE_PROFILES.get(self.voice_profile, VOICE_PROFILES["female_1"])
        gender = profile["gender"]
        idx = profile["index_hint"]
        filtered = [v for v in voices if gender in (getattr(v, "name", "").lower() + getattr(v, "id", "").lower())]
        selected = (filtered[idx % len(filtered)] if filtered else voices[idx % len(voices)]) if voices else None
        if selected:
            engine.setProperty("voice", selected.id)
        engine.say(text)
        engine.runAndWait()
        return f"Spoken with profile: {self.voice_profile}"

    # existing actions kept concise
    def get_weather(self, city: str) -> str:
        data = requests.get(f"https://wttr.in/{quote(city)}?format=j1", timeout=15).json()["current_condition"][0]
        return f"{city}: {data['temp_C']}°C, feels {data['FeelsLikeC']}°C"

    def whatsapp_send(self, phone: str, message: str) -> str:
        webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}&text={quote(message)}")
        return "WhatsApp message drafted in browser."

    def list_processes(self, limit: int = 20) -> str:
        completed = subprocess.run(
            "ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 25",
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if completed.returncode != 0:
            return completed.stderr.strip() or "Failed to read processes."
        rows = completed.stdout.strip().splitlines()
        return "\n".join(rows[: max(2, min(limit + 1, len(rows)))])

    def open_application(self, app: str) -> str:
        app = app.strip()
        if not app:
            return "Application name is required."
        candidates = [f"nohup {app} >/dev/null 2>&1 &", f"nohup xdg-open {app} >/dev/null 2>&1 &"]
        for cmd in candidates:
            completed = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if completed.returncode == 0:
                return f"Application launched: {app}"
        return f"Could not open application: {app}"

    def close_application(self, app: str) -> str:
        app = app.strip()
        if not app:
            return "Application name is required."
        completed = subprocess.run(f"pkill -f '{app}'", shell=True, capture_output=True, text=True)
        if completed.returncode == 0:
            return f"Application closed: {app}"
        return f"No running process matched: {app}"

    def system_status_check(self, realtime_seconds: int = 0, interval_seconds: int = 2) -> str:
        try:
            import psutil
        except ImportError:
            return "System status dependency missing. Install: pip install psutil"

        def snapshot() -> str:
            battery = psutil.sensors_battery()
            battery_text = (
                f"{battery.percent}% ({'charging' if battery.power_plugged else 'on battery'})"
                if battery
                else "not available"
            )
            cpu = psutil.cpu_percent(interval=0.4)
            ram = psutil.virtual_memory()
            try:
                requests.get("https://www.google.com/generate_204", timeout=4)
                internet = "connected"
            except Exception:
                internet = "disconnected"
            return (
                f"Battery: {battery_text} | CPU: {cpu}% | RAM: {ram.percent}% "
                f"({round(ram.used / (1024**3), 2)}GB/{round(ram.total / (1024**3), 2)}GB) | Internet: {internet}"
            )

        if realtime_seconds <= 0:
            return snapshot()

        end_time = time.time() + realtime_seconds
        lines = []
        while time.time() < end_time:
            lines.append(snapshot())
            time.sleep(max(1, interval_seconds))
        return "\n".join(lines)

class ConversationAssistant:
    def __init__(self, model: str = "gemini-2.0-flash", workspace: Optional[str] = None, auto_approve: bool = False, voice_profile: str = "female_1") -> None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required")
        self.workspace = workspace or os.getcwd()
        self.actions = OSActions(self.workspace, voice_profile=voice_profile)
        self.auto_approve = auto_approve
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.history: List[Message] = []

    def _contents(self) -> List[types.Content]:
        contents = [types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)])]
        for m in self.history:
            role = "model" if m.role == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=m.content)]))
        return contents

    def plan(self, user_input: str) -> Dict[str, Any]:
        self.history.append(Message(role="user", content=user_input))
        response = self.client.models.generate_content(model=self.model, contents=self._contents(), config=types.GenerateContentConfig(temperature=0.1))
        raw = response.text or ""
        self.history.append(Message(role="assistant", content=raw))
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"action": "chat", "args": {}, "explanation": raw}

    def execute(self, plan: Dict[str, Any]) -> str:
        action = plan.get("action", "chat")
        args = plan.get("args") or {}
        explanation = plan.get("explanation", "")
        if action == "chat":
            return explanation or "Done."
        if action == "run_shell" and not self.auto_approve:
            command = str(args.get("command", "")).strip()
            print(f"Planned shell command: {command}")
            if input("Run shell command? (y/N): ").strip().lower() not in {"y", "yes"}:
                return "Shell command cancelled."
        try:
            result = getattr(self.actions, action)(**args)
        except Exception as exc:
            return f"Automation error: {exc}"
        return f"{explanation}\n\n{result}".strip()

    def handle(self, user_input: str) -> str:
        fast = self._handle_voice_shortcuts(user_input)
        if fast is not None:
            return fast
        return self.execute(self.plan(user_input))

    def _handle_voice_shortcuts(self, text: str) -> Optional[str]:
        t = text.strip().lower()
        if t.startswith("open "):
            return self.actions.open_application(text[5:].strip())
        if t.startswith("close "):
            return self.actions.close_application(text[6:].strip())
        if t.startswith("create file "):
            return self.actions.create_file(text[len("create file "):].strip())
        if t.startswith("create folder "):
            return self.actions.create_folder(text[len("create folder "):].strip())
        if t in {"list processes", "show processes"}:
            return self.actions.list_processes()
        if t in {"system status", "status check", "check system status"}:
            return self.actions.system_status_check()
        if t in {"read features", "feature list", "readout features"}:
            return self.actions.readout_features()
        if t.startswith("system status realtime "):
            try:
                secs = int(t.replace("system status realtime ", "").strip())
            except ValueError:
                secs = 10
            return self.actions.system_status_check(realtime_seconds=secs, interval_seconds=2)
        return None


def main() -> None:
    workspace = os.getenv("AUTOMATION_WORKSPACE", os.getcwd())
    auto_approve = os.getenv("AUTO_APPROVE", "false").lower() in {"1", "true", "yes"}
    voice_profile = os.getenv("VOICE_PROFILE", "female_1")
    print("Gemini Real-Life Automation Assistant started.")
    print(f"Voice profile: {voice_profile}")
    print("Type 'voice' for voice input, or 'exit'.\n")
    assistant = ConversationAssistant(workspace=workspace, auto_approve=auto_approve, voice_profile=voice_profile)
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Assistant: Allah Hafiz 👋")
            break
        if user_input.lower() == "voice":
            user_input = assistant.actions.transcribe_voice()
            print(f"(Voice Input): {user_input}")
        if user_input:
            answer = assistant.handle(user_input)
            print(f"Assistant: {answer}\n")
            if os.getenv("SPEAK_RESPONSES", "false").lower() in {"1", "true", "yes"}:
                print(f"Assistant Voice: {assistant.actions.speak_text(answer)}")

if __name__ == "__main__":
    main()
