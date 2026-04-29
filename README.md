# Gemini Real-Life + OS Automation Assistant

Ab assistant me daily-life + OS automation ke saath extra real-life modules add ho gaye hain:

- OCR automation (image se text)
- WhatsApp automation (chat open, message draft, call open)
- Screenshot automation
- Weather automation
- Todo / Expense / Reminder automation

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional extras (feature-wise):

```bash
pip install pillow pytesseract pyautogui gTTS
# OCR ke liye system pe tesseract binary bhi install honi chahiye
```

## Env vars

```bash
export GEMINI_API_KEY="your_api_key_here"
# or GOOGLE_API_KEY

export AUTOMATION_WORKSPACE="$PWD"
export AUTO_APPROVE="false"
```

## New Real-Life Actions

- `ocr_image(image_path)`
- `take_screenshot(output_path="screenshots/latest.png")`
- `get_weather(city)`
- `whatsapp_open_chat(phone, message="")`
- `whatsapp_send(phone, message)`
- `whatsapp_call(phone)`
- `text_to_voice(text, output_path="audio/tts.mp3")`

## Important WhatsApp Note

WhatsApp Web automation me security restrictions ki wajah se:
- message draft/open possible hai,
- lekin auto-call, auto-send press, chat-read scrape, voice-note read as text directly official API se reliably possible nahi hota.
- Is liye assistant browser flow open karta hai aur manual final step expect karta hai.

## Example prompts

- "is image ka OCR karo: receipts/bill1.png"
- "weather Lahore batao"
- "screenshot lo"
- "+923001234567 ko whatsapp message bhejo: meeting 6 baje hai"
- "is text ko voice me convert karo"
