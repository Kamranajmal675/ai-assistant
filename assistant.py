import json
import os
import shutil
import subprocess
import tempfile
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
    "Allowed actions: chat, list_files, read_file, write_file, append_file, make_dir, delete_path, move_path, "
    "copy_path, run_shell, pwd, add_todo, list_todos, complete_todo, add_expense, list_expenses, add_reminder, "
    "list_reminders, ocr_image, take_screenshot, get_weather, whatsapp_send, whatsapp_call, whatsapp_open_chat, "
    "text_to_voice."
)


@dataclass
class Message:
    role: str
    content: str


class OSActions:
    def __init__(self, workspace: str) -> None:
        self.workspace = Path(workspace).resolve()
        self.data_dir = self.workspace / ".assistant_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

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

    def pwd(self) -> str:
        return str(self.workspace)

    def list_files(self, path: str = ".") -> str:
        target = self._safe_path(path)
        if not target.exists():
            return f"Path not found: {target}"
        if target.is_file():
            return target.name
        items = sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        return "\n".join([f"[D] {i.name}" if i.is_dir() else f"[F] {i.name}" for i in items])

    def read_file(self, path: str) -> str:
        target = self._safe_path(path)
        if not target.exists() or not target.is_file():
            return f"File not found: {target}"
        return target.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str = "") -> str:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote file: {target}"

    def append_file(self, path: str, content: str = "") -> str:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended to file: {target}"

    def make_dir(self, path: str) -> str:
        target = self._safe_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return f"Directory ready: {target}"

    def delete_path(self, path: str) -> str:
        target = self._safe_path(path)
        if not target.exists():
            return f"Path not found: {target}"
        if target.is_dir():
            shutil.rmtree(target)
            return f"Deleted directory: {target}"
        target.unlink()
        return f"Deleted file: {target}"

    def move_path(self, src: str, dst: str) -> str:
        source = self._safe_path(src)
        target = self._safe_path(dst)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        return f"Moved: {source} -> {target}"

    def copy_path(self, src: str, dst: str) -> str:
        source = self._safe_path(src)
        target = self._safe_path(dst)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
        return f"Copied: {source} -> {target}"

    def run_shell(self, command: str) -> str:
        completed = subprocess.run(command, cwd=str(self.workspace), shell=True, capture_output=True, text=True, timeout=180)
        parts = [f"Exit code: {completed.returncode}"]
        if completed.stdout.strip():
            parts.append(f"STDOUT:\n{completed.stdout.strip()}")
        if completed.stderr.strip():
            parts.append(f"STDERR:\n{completed.stderr.strip()}")
        return "\n\n".join(parts)

    def add_todo(self, title: str, due: str = "") -> str:
        todos = self._load_json("todos")
        item = {"id": len(todos) + 1, "title": title, "due": due, "done": False, "created_at": datetime.utcnow().isoformat()}
        todos.append(item)
        self._save_json("todos", todos)
        return f"Todo added: #{item['id']} {title}"

    def list_todos(self) -> str:
        todos = self._load_json("todos")
        if not todos:
            return "No todos found."
        return "\n".join([f"{'✅' if t.get('done') else '⬜'} #{t['id']} {t['title']}{' | due: ' + t['due'] if t.get('due') else ''}" for t in todos])

    def complete_todo(self, todo_id: int) -> str:
        todos = self._load_json("todos")
        for t in todos:
            if int(t["id"]) == int(todo_id):
                t["done"] = True
                self._save_json("todos", todos)
                return f"Todo completed: #{todo_id}"
        return f"Todo not found: #{todo_id}"

    def add_expense(self, amount: float, category: str, note: str = "") -> str:
        expenses = self._load_json("expenses")
        expenses.append({"id": len(expenses) + 1, "amount": amount, "category": category, "note": note, "date": datetime.utcnow().date().isoformat()})
        self._save_json("expenses", expenses)
        return f"Expense added: {amount} ({category})"

    def list_expenses(self, category: str = "") -> str:
        expenses = self._load_json("expenses")
        if category:
            expenses = [e for e in expenses if e.get("category", "").lower() == category.lower()]
        if not expenses:
            return "No expenses found."
        total = sum(float(e["amount"]) for e in expenses)
        rows = [f"Total: {total}"] + [f"#{e['id']} {e['date']} {e['category']} {e['amount']} - {e.get('note', '')}" for e in expenses]
        return "\n".join(rows)

    def add_reminder(self, title: str, remind_at: str) -> str:
        reminders = self._load_json("reminders")
        reminders.append({"id": len(reminders) + 1, "title": title, "remind_at": remind_at, "created_at": datetime.utcnow().isoformat()})
        self._save_json("reminders", reminders)
        return f"Reminder added: #{len(reminders)} {title} @ {remind_at}"

    def list_reminders(self) -> str:
        reminders = self._load_json("reminders")
        if not reminders:
            return "No reminders found."
        return "\n".join([f"#{r['id']} {r['title']} @ {r['remind_at']}" for r in reminders])

    def ocr_image(self, image_path: str) -> str:
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return "OCR dependency missing. Install: pip install pytesseract pillow"
        img = self._safe_path(image_path)
        text = pytesseract.image_to_string(Image.open(img))
        return text.strip() or "No text detected."

    def take_screenshot(self, output_path: str = "screenshots/latest.png") -> str:
        try:
            import pyautogui
        except ImportError:
            return "Screenshot dependency missing. Install: pip install pyautogui"
        out = self._safe_path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        shot = pyautogui.screenshot()
        shot.save(out)
        return f"Screenshot saved: {out}"

    def get_weather(self, city: str) -> str:
        url = f"https://wttr.in/{quote(city)}?format=j1"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        cur = data["current_condition"][0]
        return f"{city}: {cur['temp_C']}°C, feels {cur['FeelsLikeC']}°C, humidity {cur['humidity']}%, wind {cur['windspeedKmph']} km/h"

    def whatsapp_open_chat(self, phone: str, message: str = "") -> str:
        encoded = quote(message)
        webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}&text={encoded}")
        return "WhatsApp Web chat opened in browser."

    def whatsapp_send(self, phone: str, message: str) -> str:
        webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}&text={quote(message)}")
        return "WhatsApp message drafted in browser. Press Enter in WhatsApp Web to send."

    def whatsapp_call(self, phone: str) -> str:
        webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}")
        return "WhatsApp chat opened. Start call manually from call icon (web/API limitation)."

    def text_to_voice(self, text: str, output_path: str = "audio/tts.mp3") -> str:
        try:
            from gtts import gTTS
        except ImportError:
            return "Voice dependency missing. Install: pip install gTTS"
        out = self._safe_path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        gTTS(text=text, lang="en").save(out)
        return f"Voice file generated: {out}"


class ConversationAssistant:
    def __init__(self, model: str = "gemini-2.0-flash", workspace: Optional[str] = None, auto_approve: bool = False) -> None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required")
        self.workspace = workspace or os.getcwd()
        self.actions = OSActions(self.workspace)
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
            print(f"Reason: {explanation}")
            if input("Run shell command? (y/N): ").strip().lower() not in {"y", "yes"}:
                return "Shell command cancelled."
        try:
            method = getattr(self.actions, action)
            result = method(**args)
        except AttributeError:
            return f"Unknown action: {action}"
        except Exception as exc:
            return f"Automation error: {exc}"
        self.history.append(Message(role="user", content=f"Executed {action} args={args} result={result}"))
        return f"{explanation}\n\n{result}".strip()

    def handle(self, user_input: str) -> str:
        return self.execute(self.plan(user_input))


def main() -> None:
    workspace = os.getenv("AUTOMATION_WORKSPACE", os.getcwd())
    auto_approve = os.getenv("AUTO_APPROVE", "false").lower() in {"1", "true", "yes"}
    print("Gemini Real-Life Automation Assistant started.")
    print(f"Workspace: {Path(workspace).resolve()}")
    print(f"Auto-approve shell: {auto_approve}")
    print("Type 'exit' to quit.\n")
    assistant = ConversationAssistant(workspace=workspace, auto_approve=auto_approve)
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Assistant: Allah Hafiz 👋")
            break
        if user_input:
            print(f"Assistant: {assistant.handle(user_input)}\n")


if __name__ == "__main__":
    main()
