# Gemini Real-Life + OS Automation Assistant

## 🎙 Voice Input + 8 Voice Options

Assistant me voice interaction add kar di gayi hai:

- **Voice Input**: microphone se bol kar command de sakte ho (`voice` command).
- **8 voice profiles** for output speech:
  - Female: `female_1`, `female_2`, `female_3`, `female_4`
  - Male: `male_1`, `male_2`, `male_3`, `male_4`

> Note: actual installed system voices par depend karta hai ke kis profile par kaunsi tone map ho.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install SpeechRecognition pyaudio pyttsx3
```

## Env vars

```bash
export GEMINI_API_KEY="your_api_key_here"
export AUTOMATION_WORKSPACE="$PWD"
export AUTO_APPROVE="false"

# pick one of 8 profiles
export VOICE_PROFILE="female_1"

# optional: assistant response bhi awaaz me suno
export SPEAK_RESPONSES="true"
```

## Usage

```bash
python assistant.py
```

- `voice` type karo -> assistant mic se input lega.
- normal text bhi kaam karega.

## Full System Automation (Voice + Text)

Ab assistant application aur file/folder management bhi karta hai:

- **Open app**: `open chrome` / `open calculator`
- **Close app**: `close chrome`
- **List processes**: `list processes`
- **Create file**: `create file notes/today.txt`
- **Create folder**: `create folder projects/demo`

Yeh commands voice input mode (`voice`) me bhi kaam karti hain.
