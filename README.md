# M.E.R.C.Y Bot
**Mindful Empathetic Responsive Companion for You**

A 21-year-old female AI best friend powered by Telegram and Ollama.

## Features

💕 **Personality**
- Natural, caring conversation like a real best friend
- Adaptive mood system (caring, playful, serious, supportive, protective, calm, happy)
- Remembers your preferences and conversation style

🧠 **Memory System**
- User profiles with preferences
- Notes and saved facts
- Task management with priorities
- Reminders
- Conversation history (last 10 messages)

⚡ **Commands**
- `/start` - Begin conversation
- `/help` - Show all commands
- `/save <text>` - Save a note or fact
- `/memory` - Show what Mercy remembers about you
- `/notes` - View all notes
- `/tasks` - View tasks
- `/complete <id>` - Mark task done
- `/remind <msg> <time>` - Set reminder
- `/myname <name>` - Set your name
- `/settings` - View settings
- `/stats` - Conversation statistics
- `/reset` - Clear all data

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export TELEGRAM_TOKEN="your_bot_token"
export OLLAMA_URL="http://localhost:11434/api/chat"
export MODEL_NAME="qwen2.5"
```

3. Run Ollama:
```bash
ollama run qwen2.5
```

4. Start the bot:
```bash
python main.py
```

## Data Storage

All user data is stored locally in `data/mercy_memory.json`.

## Architecture

- `main.py` - Telegram bot handlers and entry point
- `memory_manager.py` - JSON-based memory system
- `ollama_client.py` - AI model communication
- `bot_config.py` - Configuration and personality settings
