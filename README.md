# Python AI OS Automation Assistant (Gemini)

Ye project ab simple chat se aage barh kar **OS automation assistant** ban gaya hai.
Assistant Gemini se plan banata hai aur zarurat par shell command run karta hai.

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) API Key set karein

```bash
export GEMINI_API_KEY="your_api_key_here"
# alternative:
# export GOOGLE_API_KEY="your_api_key_here"
```

## 3) Optional automation env vars

```bash
# jis folder me commands chalani hain
export AUTOMATION_WORKSPACE="$PWD"

# true karne par command confirmation skip ho jayegi
export AUTO_APPROVE="false"
```

## 4) Run

```bash
python assistant.py
```

## 5) Kaise kaam karta hai

- Normal sawaal par normal answer deta hai.
- Automation request par assistant command propose karta hai.
- `AUTO_APPROVE=false` par pehle confirmation mangta hai.
- Approved hone par command execute karta hai aur output wapas deta hai.

## 6) Example prompts

- "current folder ki files list karo"
- "logs naam ka folder banao aur usme today.txt file create karo"
- "python version check karo"
- "system disk usage batao"

## Safety Note

Shell automation powerful hoti hai. Unknown commands ko blindly run na karein.
Production workflows ke liye allowlist, sandboxing, aur audit logs add karna recommended hai.
