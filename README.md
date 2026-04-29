# Gemini OS Automation Assistant (Python)

Is version me assistant ko **Operating System automation** ke liye design kiya gaya hai.
Assistant Gemini se action-plan banata hai aur OS actions execute karta hai.

## Features (Full OS Automation Base)

- Workspace-scoped file system automation
  - `list_files`
  - `read_file`
  - `write_file`
  - `append_file`
  - `make_dir`
  - `delete_path`
  - `move_path`
  - `copy_path`
- Shell command execution (`run_shell`)
- Safety prompt for shell commands (`AUTO_APPROVE=false`)
- Conversation memory with action/result feedback loop

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

```bash
export GEMINI_API_KEY="your_api_key_here"
# or
export GOOGLE_API_KEY="your_api_key_here"

# assistant sirf isi workspace ke andar paths operate karega
export AUTOMATION_WORKSPACE="$PWD"

# shell commands ke liye auto-confirmation
export AUTO_APPROVE="false"
```

## Run

```bash
python assistant.py
```

## Example Prompts

- "current folder ki files list karo"
- "notes/today.txt file banao aur isme hello likho"
- "notes/today.txt read karo"
- "logs folder create karo"
- "disk usage check karo"

## Safety

- Path operations workspace boundary ke bahar allow nahi hain.
- Shell commands powerful hoti hain; production me allowlist/audit logging add karein.
