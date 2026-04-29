import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types


SYSTEM_PROMPT = (
    "You are an Operating System automation planner. "
    "Return ONLY valid JSON with schema: "
    "{\"action\": string, \"args\": object, \"explanation\": string}. "
    "Allowed actions: chat, list_files, read_file, write_file, append_file, make_dir, "
    "delete_path, move_path, copy_path, run_shell, pwd."
)


@dataclass
class Message:
    role: str
    content: str


class OSActions:
    def __init__(self, workspace: str) -> None:
        self.workspace = Path(workspace).resolve()

    def _safe_path(self, relative_or_abs: str) -> Path:
        p = Path(relative_or_abs)
        candidate = (self.workspace / p).resolve() if not p.is_absolute() else p.resolve()
        if self.workspace not in [candidate, *candidate.parents]:
            raise ValueError("Path is outside AUTOMATION_WORKSPACE")
        return candidate

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
        completed = subprocess.run(
            command,
            cwd=str(self.workspace),
            shell=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        out = (completed.stdout or "").strip()
        err = (completed.stderr or "").strip()
        chunks = [f"Exit code: {completed.returncode}"]
        if out:
            chunks.append(f"STDOUT:\n{out}")
        if err:
            chunks.append(f"STDERR:\n{err}")
        return "\n\n".join(chunks)


class ConversationAssistant:
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        workspace: Optional[str] = None,
        auto_approve: bool = False,
    ) -> None:
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
        response = self.client.models.generate_content(
            model=self.model,
            contents=self._contents(),
            config=types.GenerateContentConfig(temperature=0.1),
        )
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
            confirm = input("Run shell command? (y/N): ").strip().lower()
            if confirm not in {"y", "yes"}:
                return "Shell command cancelled."

        try:
            method = getattr(self.actions, action)
        except AttributeError:
            return f"Unknown action: {action}"

        try:
            result = method(**args)
        except Exception as exc:
            return f"Automation error: {exc}"

        self.history.append(
            Message(role="user", content=f"Executed action={action}, args={args}, result={result}")
        )
        return f"{explanation}\n\n{result}".strip()

    def handle(self, user_input: str) -> str:
        return self.execute(self.plan(user_input))


def main() -> None:
    workspace = os.getenv("AUTOMATION_WORKSPACE", os.getcwd())
    auto_approve = os.getenv("AUTO_APPROVE", "false").lower() in {"1", "true", "yes"}

    print("Gemini OS Automation Assistant started.")
    print(f"Workspace: {Path(workspace).resolve()}")
    print(f"Auto-approve shell: {auto_approve}")
    print("Type 'exit' to quit.\n")

    assistant = ConversationAssistant(workspace=workspace, auto_approve=auto_approve)

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Assistant: Allah Hafiz 👋")
            break
        if not user_input:
            continue
        print(f"Assistant: {assistant.handle(user_input)}\n")


if __name__ == "__main__":
    main()
