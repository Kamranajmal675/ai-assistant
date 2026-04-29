import os
from dataclasses import dataclass
from typing import List

from google import genai
from google.genai import types


SYSTEM_PROMPT = (
    "You are a helpful AI automation assistant. "
    "Understand user intent, ask short clarifying questions when needed, "
    "and provide step-by-step actionable outputs."
)


@dataclass
class Message:
    role: str
    content: str


class ConversationAssistant:
    def __init__(self, model: str = "gemini-2.0-flash") -> None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is required"
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.history: List[Message] = []

    def ask(self, user_input: str) -> str:
        self.history.append(Message(role="user", content=user_input))

        contents = [types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)])]
        for message in self.history:
            role = "model" if message.role == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=message.content)]))

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.3),
        )

        answer = response.text or ""
        self.history.append(Message(role="assistant", content=answer))
        return answer


def main() -> None:
    print("AI Assistant started (Gemini). Type 'exit' to quit.\n")
    assistant = ConversationAssistant()

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Assistant: Allah Hafiz 👋")
            break

        if not user_input:
            continue

        answer = assistant.ask(user_input)
        print(f"Assistant: {answer}\n")


if __name__ == "__main__":
    main()
