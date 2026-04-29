import json
import os
import shutil
import subprocess
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
    "Allowed actions include voice features: transcribe_voice, speak_text, set_voice_profile."
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

    def list_voice_profiles(self) -> str:
        return "\n".join(VOICE_PROFILES.keys())

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
        return self.execute(self.plan(user_input))


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
