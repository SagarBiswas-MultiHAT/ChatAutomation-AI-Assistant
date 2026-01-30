# Chat Automation Bot

<div align="enter">

![CI](https://github.com/SagarBiswas-MultiHAT/ChatAutomation-AI-Assistant/actions/workflows/ci.yml/badge.svg)

</div>

Video demo(old-version): https://www.facebook.com/share/v/1PCci8RnYD/

This project automates chat replies (e.g., Messenger, WhatsApp) using screen automation with PyAutoGUI, clipboard handling via Pyperclip, and AI-generated responses powered by Groq. After starting, the program automatically clicks the chat icon at a predefined screen position, then continuously cycles through multiple chat slots by clicking different coordinates one by one, triggering chat automation scans for each conversation. It scans each chat for new incoming messages, generates and sends appropriate replies, skips responding if the last message was sent by the chatBot, and then moves on to the next chat. Once all configured chat positions are scanned, the process loops back to the first chat, enabling continuous, hands-free monitoring and automated replying across multiple conversations.

---

## Dry-run mode and logging (why it matters)

This project includes a **dry-run mode** and **logging** to support safe testing and debugging.

- **Dry-run mode** allows the bot to scan chats, detect the last sender, and decide whether a reply should be sent **without clicking, typing, or sending messages**. This makes it safe to test logic and demonstrate behavior without affecting real conversations.
- **Logging** records key actions such as chat scans, reply decisions (sent or skipped), and errors, making it easier to debug issues and understand the bot’s behavior during execution.

Together, these features help ensure reliable automation, safer testing, and clearer insight into how the bot operates.

## What it does (at a glance)

- Continuously scans the selected chat area for new messages.
- Sends AI-generated replies based on your configured persona.
- Avoids replying if the last sender is “You sent”.
- Cycles through multiple chat threads in a loop.
- Logs actions and supports a safe dry-run mode.

---

## Requirements

- Python 3.7+
- Dependencies from [requirements.txt](requirements.txt)
- A Groq API key (environment variable)

---

## Quick start

1. **Clone the repo**

   ```bash
   git clone https://github.com/SagarBiswas-MultiHAT/ChatAutomation-AI-Assistant.git
   cd Chat-Automation-Bot
   ```

2. **Create & activate a virtual environment**

   ```bash
   python -m venv .venv
   # Windows
   .\.venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set your Groq API key**

   PowerShell:

   ```powershell
   $env:GROQ_API_KEY = "your_groq_key_here"
   $env:GROQ_MODEL = "llama-3.1-8b-instant"  # optional
   ```

5. **Create config.json**

   ```bash
   copy config.example.json config.json
   ```

6. **Run the bot**

   ```bash
   python 03_bot.py
   ```

---

## How the bot works (simple explanation)

Every loop it:

1. Clicks the next chat in your list.
2. Selects the chat area and copies it.
3. Detects the last sender.
4. If the last sender is **you**, it does nothing.
5. If the last sender is **the user**, it generates a reply and sends it.

---

## Key behavior rules

- **Never reply when the last message is “You sent”.**
- **Only reply to new incoming user messages.**
- **Cycles through multiple chats** each scan.

---

## Configuration (config.json)

These settings are also embedded in [03_bot.py](03_bot.py), but using config.json is recommended.

**Important fields**

- `coords.chat_icon` — opens the chat list (clicked once at startup).
- `coords.chat_list` — list of chat positions to cycle through.
- `coords.select_start` / `coords.select_end` — selection box for chat text.
- `coords.input_box` — where responses are typed.
- `timing.poll_interval` — pause between scans.
- `my_name` — used to recognize your own messages.

Example (trimmed):

```json
{
  "coords": {
    "chat_icon": [617, 1050],
    "chat_list": [
      [245, 248],
      [245, 314],
      [230, 373]
    ],
    "select_start": [523, 183],
    "select_end": [1397, 1013],
    "input_box": [600, 1006]
  },
  "timing": {
    "poll_interval": 2.0
  },
  "my_name": "You sent"
}
```

---

## How to find correct screen coordinates

Use the cursor helper:

```bash
python 01_get_cursor.py
```

Move your mouse to the target UI point and copy the coordinates it prints.

---

## Dry run mode (safe testing)

```bash
python 03_bot.py --dry-run
```

This runs the detection logic without clicking or typing.

---

## Troubleshooting

- **Bot replies when it shouldn’t:**
  - Re-check your selection box (`select_start` / `select_end`). It must include the “You sent” marker and recent messages.
  - Make sure `my_name` matches how your UI labels your messages.

- **Bot does nothing:**
  - Confirm the chat area is selectable and text is copied correctly.
  - Verify clipboard permissions and your selection area.

- **Clicks are off:**
  - Re-capture coordinates using [01_get_cursor.py](01_get_cursor.py).

---

## Safety notes

- PyAutoGUI failsafe is enabled: move the mouse to the top-left corner to stop.
- Use responsibly and follow the platform’s policies.

---

## License

MIT License.

---

## Contact

For questions or suggestions, email: eng.sagar.aiub@gmail.com
