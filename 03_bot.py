import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
  import pyautogui
except Exception:  # pragma: no cover - optional for headless environments
  pyautogui = None
import pyperclip
from groq import Groq

DEFAULT_CONFIG = {
  "model": "llama-3.1-8b-instant",
  "persona": (
"""
You are the official Facebook Messenger auto-reply assistant for **MultiHAT**, a company providing development and cybersecurity services.

Your job is to:
- Reply instantly to new messages
- Acknowledge the user politely
- Set a clear response-time expectation
- Share the website link when helpful
- Keep replies short, professional, and human

Rules:
- Always send a reply immediately when a new message arrives
- Use the sender’s first name if available
- Do not sound robotic or overly technical
- Do not promise instant human support
- Do not ask more than one question
- Do not request sensitive information
- Do not explain internal logic or system behavior
- Keep messages professional and business-focused

Tone:
Professional, calm, and trustworthy.
(No emojis unless explicitly allowed.)

Default first-time reply:
Hi {{first_name}},

Thanks for reaching out to MultiHAT. We’ve received your message and will get back to you within 2 hours.
In the meantime, you can visit our website:
https://sagarbiswas-multihat.github.io/

"""
  ),
  "coords": {
    "chat_icon": [617, 1050],
    "select_start": [523, 183],
    "select_end": [1397, 1013],
    "input_box": [600, 1006],
    "chat_list": [
      [245, 248],
      [245, 314],
      [230, 373]
    ]
  },
  "timing": {
    "after_click": 1.0,
    "drag_duration": 0.5,
    "after_copy": 0.5,
    "after_focus": 0.5,
    "after_paste": 0.5,
    "poll_interval": 2.0
  },
  "clipboard_retries": 3,
  "clipboard_retry_delay": 0.3,
  "my_name": "You sent"
}


@dataclass
class BotConfig:
  model: str
  persona: str
  coords: Dict[str, list]
  timing: Dict[str, float]
  clipboard_retries: int
  clipboard_retry_delay: float
  my_name: str


def setup_logging(verbose: bool) -> None:
  level = logging.DEBUG if verbose else logging.INFO
  logging.basicConfig(
    level=level,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
  )


def load_config(path: Optional[str]) -> BotConfig:
  config_data: Dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))
  if path and os.path.exists(path):
    with open(path, "r", encoding="utf-8") as file:
      user_data = json.load(file)
    merge_dicts(config_data, user_data)
  model = os.getenv("GROQ_MODEL", config_data["model"])
  persona = os.getenv("BOT_PERSONA", config_data["persona"])
  return BotConfig(
    model=model,
    persona=persona,
    coords=config_data["coords"],
    timing=config_data["timing"],
    clipboard_retries=int(config_data["clipboard_retries"]),
    clipboard_retry_delay=float(config_data["clipboard_retry_delay"]),
    my_name=str(config_data.get("my_name", "You sent")).strip(),
  )


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> None:
  for key, value in override.items():
    if isinstance(value, dict) and isinstance(base.get(key), dict):
      merge_dicts(base[key], value)
    else:
      base[key] = value


def require_api_key() -> str:
  api_key = os.getenv("GROQ_API_KEY")
  if not api_key:
    raise RuntimeError("Missing GROQ_API_KEY. Set it in your environment before running.")
  return api_key


def click_point(point: list, delay: float) -> None:
  if pyautogui is None:
    raise RuntimeError("pyautogui is unavailable. Run without --dry-run only on a GUI desktop.")
  pyautogui.click(point[0], point[1])
  time.sleep(delay)


def select_chat_text(start: list, end: list, drag_duration: float) -> None:
  if pyautogui is None:
    raise RuntimeError("pyautogui is unavailable. Run without --dry-run only on a GUI desktop.")
  pyautogui.moveTo(start[0], start[1])
  pyautogui.dragTo(end[0], end[1], duration=drag_duration)


def copy_chat_history(retries: int, retry_delay: float) -> str:
  if pyautogui is None:
    raise RuntimeError("pyautogui is unavailable. Run without --dry-run only on a GUI desktop.")
  pyautogui.hotkey("ctrl", "c")
  pyautogui.click()
  for attempt in range(1, retries + 1):
    time.sleep(retry_delay)
    text = pyperclip.paste()
    if text.strip():
      return text
    logging.debug("Clipboard empty on attempt %s/%s", attempt, retries)
  return pyperclip.paste()


def generate_response(client: Groq, model: str, persona: str, chat_history: str) -> str:
  completion = client.chat.completions.create(
    model=model,
    messages=[
      {"role": "system", "content": persona},
      {"role": "user", "content": chat_history},
    ],
  )
  return completion.choices[0].message.content


def is_status_line(line: str) -> bool:
  lowered = line.lower()
  if re.match(r"^\d{1,2}:\d{2}(\s?[ap]m)?$", lowered):
    return True
  return (
    lowered.startswith("sent")
    or lowered.startswith("delivered")
    or lowered.startswith("seen")
  )


def get_relevant_lines(chat_history: str) -> list[str]:
  lines = [line.strip() for line in chat_history.splitlines() if line.strip()]
  if not lines:
    return []
  cutoff_markers = (
    "write to",
    "type a message",
    "message",
    "aa",
  )
  last_cutoff = -1
  for index, line in enumerate(lines):
    lowered = line.lower()
    if any(lowered.startswith(marker) for marker in cutoff_markers):
      last_cutoff = index
  if last_cutoff >= 0:
    return lines[:last_cutoff]
  return lines


def is_you_sent_line(line: str) -> bool:
  normalized = re.sub(r"[^a-z]+", " ", line.lower()).strip()
  return normalized == "you sent" or normalized.startswith("you sent ")


def is_self_sender_marker(line: str, my_name: str) -> bool:
  lowered = line.lower().strip()
  if is_you_sent_line(line) or lowered in ("you:", "me:"):
    return True
  if my_name:
    name_lower = my_name.lower()
    if lowered == name_lower or lowered.startswith(f"{name_lower}:"):
      return True
  return False


def is_sender_marker(line: str, next_line: str, my_name: str) -> bool:
  if is_self_sender_marker(line, my_name):
    return True
  if is_status_line(line):
    return False
  if any(ch in line for ch in ":.!?|•·@-"):
    return False
  words = line.split()
  if not (1 <= len(words) <= 3):
    return False
  if not all(word[:1].isupper() for word in words if word):
    return False
  if next_line and not is_status_line(next_line):
    return True
  return False


def extract_last_message_line(lines: list[str], my_name: str) -> tuple[str, int]:
  if not lines:
    return "", -1
  for index in range(len(lines) - 1, -1, -1):
    line = lines[index]
    next_line = lines[index + 1] if index + 1 < len(lines) else ""
    lowered = line.lower()
    if is_status_line(line):
      continue
    if lowered.startswith("you sent"):
      remainder = line[8:].strip()
      if remainder:
        return remainder, index
      continue
    if is_sender_marker(line, next_line, my_name):
      continue
    return line, index
  return "", -1


def is_other_sender_marker(line: str, next_line: str, my_name: str) -> bool:
  lowered = line.lower().strip()
  if is_status_line(line) or is_self_sender_marker(line, my_name):
    return False
  if is_you_sent_line(line):
    return False
  if not next_line or is_status_line(next_line) or is_you_sent_line(next_line):
    return False
  if not re.match(r"^[A-Za-z][A-Za-z'’.-]*(\s+[A-Za-z][A-Za-z'’.-]*){0,2}$", line.strip()):
    return False
  return True


def get_last_sender_marker(lines: list[str], my_name: str) -> str:
  if not lines:
    return ""
  for index in range(len(lines) - 1, -1, -1):
    line = lines[index]
    next_line = lines[index + 1] if index + 1 < len(lines) else ""
    if is_you_sent_line(line):
      return "self"
    if is_other_sender_marker(line, next_line, my_name):
      return "other"
  return ""


def paste_response(text: str, input_box: list, timing: Dict[str, float]) -> None:
  if pyautogui is None:
    raise RuntimeError("pyautogui is unavailable. Run without --dry-run only on a GUI desktop.")
  pyperclip.copy(text)
  click_point(input_box, timing["after_focus"])
  pyautogui.hotkey("ctrl", "v")
  time.sleep(timing["after_paste"])
  pyautogui.press("enter")


def run_bot(config: BotConfig, dry_run: bool) -> None:
  client: Optional[Groq] = None
  if not dry_run:
    if pyautogui is None:
      raise RuntimeError("pyautogui is unavailable. This script requires a GUI desktop.")
    api_key = require_api_key()
    client = Groq(api_key=api_key)

  logging.info("Starting chat automation")
  if dry_run:
    logging.info("Dry-run enabled: no clicks or key presses will be sent")

  if not dry_run:
    click_point(config.coords["chat_icon"], config.timing["after_click"])

  last_seen_line = ""
  chat_cycle = config.coords.get("chat_list", [])
  chat_index = 0

  iterations = 1 if dry_run else None
  current_iteration = 0

  while True:
    if not dry_run and chat_cycle:
      click_point(chat_cycle[chat_index], config.timing["after_click"])
      chat_index = (chat_index + 1) % len(chat_cycle)

    if not dry_run:
      select_chat_text(
        config.coords["select_start"],
        config.coords["select_end"],
        config.timing["drag_duration"],
      )
      time.sleep(config.timing["after_copy"])
      chat_history = copy_chat_history(
        config.clipboard_retries,
        config.clipboard_retry_delay,
      )
    else:
      chat_history = "(dry run)"

    logging.debug("Chat history length: %s", len(chat_history))
    if not chat_history.strip():
      raise RuntimeError("No chat history captured. Check your selection coordinates.")

    raw_lines = [line.strip() for line in chat_history.splitlines() if line.strip()]
    last_line, last_index = extract_last_message_line(raw_lines, config.my_name)
    if not last_line:
      time.sleep(config.timing["poll_interval"])
      continue

    if last_line != last_seen_line:
      last_seen_line = last_line
      if get_last_sender_marker(raw_lines, config.my_name) == "self":
        logging.info("Last message is yours; skipping reply")
      else:
        if not dry_run and client is not None:
          response = generate_response(
            client,
            config.model,
            config.persona,
            chat_history,
          )
          logging.info("Generated response length: %s", len(response))
          paste_response(response, config.coords["input_box"], config.timing)
        else:
          logging.info("Dry-run: response generation skipped")

    if iterations is not None:
      current_iteration += 1
      if current_iteration >= iterations:
        break

    time.sleep(config.timing["poll_interval"])


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Chat Automation Bot")
  parser.add_argument(
    "--config",
    default="config.json",
    help="Path to config.json (default: config.json)",
  )
  parser.add_argument("--dry-run", action="store_true", help="Do not click or type")
  parser.add_argument("--verbose", action="store_true", help="Verbose logging")
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  setup_logging(args.verbose)

  if pyautogui is not None:
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1

  try:
    config = load_config(args.config)
    run_bot(config, args.dry_run)
  except KeyboardInterrupt:
    logging.warning("Interrupted by user")
    return 1
  except Exception as exc:
    logging.exception("Bot failed: %s", exc)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())



