import json
import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from google import genai
from google.genai import types


SYSTEM_PROMPT = (
    "You are an OS automation assistant. "
    "When the user asks for system/file automation, return ONLY JSON with keys: "
    "action, command, explanation. "
    "Use action='run_shell' for terminal commands and action='chat' for normal replies. "
    "Never include markdown in JSON mode."
)


@dataclass
class Message:
    role: str
    content: str


class ConversationAssistant:
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        workspace: Optional[str] = None,
        auto_approve: bool = False,
    ) -> None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is required"
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.history: List[Message] = []
        self.workspace = workspace or os.getcwd()
        self.auto_approve = auto_approve

    def _build_contents(self) -> List[types.Content]:
        contents = [types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)])]
        for message in self.history:
            role = "model" if message.role == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=message.content)]))
        return contents

    def ask_model(self, user_input: str) -> str:
        self.history.append(Message(role="user", content=user_input))

        response = self.client.models.generate_content(
            model=self.model,
            contents=self._build_contents(),
            config=types.GenerateContentConfig(temperature=0.2),
        )
        answer = response.text or ""
        self.history.append(Message(role="assistant", content=answer))
        return answer

    def run_shell(self, command: str) -> str:
        try:
            completed = subprocess.run(
                command,
                cwd=self.workspace,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return "Command timed out after 120 seconds."

        output = (completed.stdout or "").strip()
        err = (completed.stderr or "").strip()

        result_lines = [f"Exit code: {completed.returncode}"]
        if output:
            result_lines.append(f"STDOUT:\n{output}")
        if err:
            result_lines.append(f"STDERR:\n{err}")
        return "\n\n".join(result_lines)

    def handle(self, user_input: str) -> str:
        raw = self.ask_model(user_input)

        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        action = plan.get("action", "chat")
        if action != "run_shell":
            return plan.get("explanation", raw)

        command = (plan.get("command") or "").strip()
        explanation = plan.get("explanation", "")
        if not command:
            return "Automation plan missing shell command."

        if not self.auto_approve:
            print(f"Planned command: {command}")
            print(f"Reason: {explanation}")
            confirm = input("Run this command? (y/N): ").strip().lower()
            if confirm not in {"y", "yes"}:
                return "Command cancelled."

        result = self.run_shell(command)
        self.history.append(
            Message(
                role="user",
                content=f"Command executed: {command}\nResult:\n{result}",
            )
        )
        return f"{explanation}\n\n{result}"


def main() -> None:
    auto_approve = os.getenv("AUTO_APPROVE", "false").lower() in {"1", "true", "yes"}
    workspace = os.getenv("AUTOMATION_WORKSPACE", os.getcwd())

    print("AI OS Automation Assistant started (Gemini). Type 'exit' to quit.\n")
    print(f"Workspace: {workspace}")
    print(f"Auto-approve: {auto_approve}\n")

    assistant = ConversationAssistant(workspace=workspace, auto_approve=auto_approve)

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Assistant: Allah Hafiz 👋")
            break
        if not user_input:
            continue

        answer = assistant.handle(user_input)
        print(f"Assistant: {answer}\n")


if __name__ == "__main__":
    main()
