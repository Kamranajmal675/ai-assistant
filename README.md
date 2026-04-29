# Python Conversation AI Assistant (Gemini Starter)

Ye project ek basic **conversation-based AI assistant** ka starter hai jo **Google Gemini API** use karta hai.
Aap is base ko aage full automation workflows (email, scraping, reports, API tasks, etc.) ke liye extend kar sakte hain.

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) API Key set karein

Gemini key AI Studio se banayein, phir env variable set karein:

```bash
export GEMINI_API_KEY="your_api_key_here"
# alternative:
# export GOOGLE_API_KEY="your_api_key_here"
```

## 3) Run

```bash
python assistant.py
```

## 4) Next step (Full Automation Roadmap)

- Intent router add karein (user input se task type detect ho).
- Tools layer banayein (filesystem, web, email, database actions).
- Safety layer add karein (confirmation before critical actions).
- Scheduler/Cron integration se autonomous runs enable karein.
- Memory store (SQLite/Postgres) add karein taake long-term context maintain ho.

Agar chahen to next iteration me main aap ke liye:
1. intent-based command system,
2. local task automation,
3. report generation pipeline
bhi bana deta hoon.
