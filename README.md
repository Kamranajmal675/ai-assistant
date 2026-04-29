# Gemini Daily-Life + OS Automation Assistant

Ab assistant sirf OS commands nahi, balkay **daily life automation** bhi karta hai.

## Daily Life Automation

- Todo management
  - `add_todo`, `list_todos`, `complete_todo`
- Expense tracking
  - `add_expense`, `list_expenses`
- Reminder management
  - `add_reminder`, `list_reminders`

Data local workspace me `.assistant_data/` folder ke andar JSON files me save hota hai.

## OS Automation

- `list_files`, `read_file`, `write_file`, `append_file`
- `make_dir`, `delete_path`, `move_path`, `copy_path`
- `run_shell` (optional confirmation)
- `pwd`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Env vars

```bash
export GEMINI_API_KEY="your_api_key_here"
# or GOOGLE_API_KEY

export AUTOMATION_WORKSPACE="$PWD"
export AUTO_APPROVE="false"
```

## Run

```bash
python assistant.py
```

## Example prompts

- "Aaj ka todo add karo: bijli ka bill pay karna"
- "Mere todos dikhao"
- "Todo #1 complete kar do"
- "500 grocery expense add karo"
- "Is month ke expenses dikhao"
- "Kal subah 8 baje doctor appointment ka reminder laga do"
- "Desktop style me files list karo"

## Safety

- Workspace boundary enforced hai.
- Shell commands ke liye confirmation enabled rehta hai (jab tak `AUTO_APPROVE=true` na ho).
