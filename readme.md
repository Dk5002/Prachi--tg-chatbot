# Prachi — Telegram AI Chatbot

Friendly Telegram chatbot with MongoDB storage and optional OpenAI integration.

## Quick start
1. Create a new Replit / VPS / local env.
2. (Optional) Move sensitive values to environment variables for security.
3. Install requirements: `pip install -r requirements.txt`
4. Run: `python main.py`

## Commands
- `/start` — Start
- `/help` — Usage
- `/ban <user_id|reply>` — Owner only
- `/unban <user_id>` — Owner only
- `/chat on|off` — Owner only (global)

## Notes
- The bot replies to all messages in groups when chat is ON.
- Welcome messages mention first name and group name using `{mention}` and `{group}` placeholders.
- Keep tokens secret. It's safer to use env vars than committing credentials.