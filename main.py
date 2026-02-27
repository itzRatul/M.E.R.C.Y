"""
M.E.R.C.Y Bot - Main Entry Point
Mindful Empathetic Responsive Companion for You
A AI best friend
"""
import os
import sys
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Import modules
from bot_config import TELEGRAM_TOKEN, BOT_NAME, MODEL_NAME, get_system_prompt
from memory_manager import MemoryManager
from ollama_client import OllamaClient

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize components
memory = MemoryManager()
ollama = OllamaClient()



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Welcome message"""
    user_id = update.effective_user.id
    user_name = memory.get_name(user_id)

    # Update user stats
    memory.save_message(user_id, "system", "conversation_started")

    welcome_text = f"""Hey there! I'm {BOT_NAME} 💕

I'm your 21-year-old AI best friend - here to chat, support you, and help with whatever you need!

I can:
📝 Save your notes and ideas
✅ Keep track of your tasks
⏰ Set reminders for you
🧠 Remember things about you
💬 Have real, meaningful conversations

Just talk to me naturally, like you would with a friend!

Use /help to see all commands, or just say hi! 👋"""

    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """Here are all the things I can do for you:

📋 *Basic Commands:*
/start - Start our friendship
/help - Show this help message

💾 *Memory Commands:*
/save <something> - Save something I should remember
/memory - Show everything I know about you
/notes - View your saved notes
/tasks - See your task list
/remind <message> <time> - Set a reminder

⚙️ *Settings:*
/myname <name> - Tell me what to call you
/settings - View your settings
/stats - See our conversation stats
/reset - Clear all your data (careful!)

Just message me naturally and I'll be here for you! 💕"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /save command - Save a note or fact"""
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "What would you like me to save? 💭\n\n"
            "Example: /save My birthday is on March 15th\n"
            "Or: /save I love chocolate cake!"
        )
        return

    content = " ".join(args)

    # Try to determine if it's a task, reminder, or general note
    content_lower = content.lower()

    if any(word in content_lower for word in ["birthday", "born", "date"]):
        memory.save_fact(user_id, content)
        note_id = memory.add_note(user_id, content, ["personal"])
        await update.message.reply_text(
            f"Got it! I'll remember that. 📝✨\n"
            f"(Saved as note #{note_id})"
        )
    elif any(word in content_lower for word in ["task", "todo", "need to", "should"]):
        task_id = memory.add_task(user_id, content)
        await update.message.reply_text(
            f"Added to your tasks! ✅\n"
            f"Task #{task_id}: {content}"
        )
    else:
        note_id = memory.add_note(user_id, content)
        await update.message.reply_text(
            f"Saved! I'll remember that. 📝\n"
            f"Note #{note_id}: {content}"
        )


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /memory command - Show user's memory"""
    user_id = update.effective_user.id
    user_name = memory.get_name(user_id)
    profile = memory.get_profile(user_id)
    facts = memory.get_facts(user_id)
    notes = memory.get_notes(user_id)

    memory_text = f"""*What I know about you, {user_name}:* 💕

📝 *Saved Facts:*
"""

    if facts:
        for fact in facts[-5:]:  # Show last 5 facts
            memory_text += f"• {fact['content']}\n"
    else:
        memory_text += "_No saved facts yet_\n"

    memory_text += f"\n📋 *Recent Notes:*\n"
    if notes:
        for note in notes[-3:]:
            memory_text += f"• {note['content'][:50]}...\n"
    else:
        memory_text += "_No notes yet_\n"

    memory_text += f"\n📊 *Profile:*\n"
    memory_text += f"Name: {profile.get('name', 'Not set')}\n"
    if profile.get('interests'):
        memory_text += f"Interests: {', '.join(profile['interests'])}\n"

    await update.message.reply_text(memory_text, parse_mode="Markdown")


async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /notes command - Show all notes"""
    user_id = update.effective_user.id
    notes = memory.get_notes(user_id)

    if not notes:
        await update.message.reply_text(
            "You don't have any notes yet! 📝\n\n"
            "Save one with: /save <your note>"
        )
        return

    notes_text = "*Your Notes:* 📝\n\n"
    for i, note in enumerate(notes, 1):
        notes_text += f"{i}. {note['content'][:100]}"
        if len(note['content']) > 100:
            notes_text += "..."
        notes_text += f"\n   _ID: {note['note_id']}_\n\n"

    await update.message.reply_text(notes_text, parse_mode="Markdown")


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tasks command - Show task list"""
    user_id = update.effective_user.id
    tasks = memory.get_tasks(user_id, completed=False)
    completed = memory.get_tasks(user_id, completed=True)

    if not tasks and not completed:
        await update.message.reply_text(
            "You have no tasks! ✅\n\n"
            "Add one with: /save I need to finish my homework"
        )
        return

    tasks_text = "*Your Tasks:* ✅\n\n"

    if tasks:
        tasks_text += "*Pending:*\n"
        for i, task in enumerate(tasks, 1):
            tasks_text += f"{i}. {task['description'][:80]}"
            if task.get('due_date'):
                tasks_text += f" (Due: {task['due_date']})"
            tasks_text += f"\n   _ID: {task['task_id']}_\n"
        tasks_text += "\n"

    if completed:
        tasks_text += f"*Completed:* {len(completed)} tasks 🎉\n"

    tasks_text += "\n_Mark complete: /complete <task_id>_"
    await update.message.reply_text(tasks_text, parse_mode="Markdown")


async def complete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /complete command - Mark task as done"""
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage: /complete <task_id>\n"
            "Find task IDs with /tasks"
        )
        return

    task_id = args[0]
    if memory.complete_task(user_id, task_id):
        await update.message.reply_text(
            f"Great job! Task completed! 🎉✨\n"
            f"I'm proud of you!"
        )
    else:
        await update.message.reply_text(
            "Couldn't find that task ID. Check with /tasks"
        )


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remind command - Set a reminder"""
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /remind <message> <time>\n\n"
            "Examples:\n"
            "/remind Call mom tomorrow at 5pm\n"
            "/remind Take medicine in 2 hours\n"
            "/remind Meeting on 2024-02-25 at 10:00"
        )
        return

    # Simple parsing - last word is treated as time
    time_str = args[-1]
    message = " ".join(args[:-1])

    reminder_id = memory.add_reminder(user_id, message, time_str)

    await update.message.reply_text(
        f"Reminder set! ⏰\n"
        f"I'll remind you: '{message}'\n"
        f"When: {time_str}\n\n"
        f"Reminder ID: {reminder_id}"
    )


async def myname_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myname command - Set user's name"""
    user_id = update.effective_user.id
    args = context.args

    if not args:
        current_name = memory.get_name(user_id)
        await update.message.reply_text(
            f"I currently call you: {current_name}\n\n"
            f"To change it: /myname <your name>\n"
            f"Example: /myname Alex"
        )
        return

    name = " ".join(args)
    memory.set_name(user_id, name)

    await update.message.reply_text(
        f"Nice to meet you, {name}! 💕\n"
        f"I'll remember that from now on."
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - Show settings"""
    user_id = update.effective_user.id
    settings = memory.get_settings(user_id)
    profile = memory.get_profile(user_id)

    settings_text = f"""*Your Settings:* ⚙️

📝 Name: {profile.get('name', 'Not set')}
🌐 Language: {settings.get('language', 'mixed')}
😊 Mood: {settings.get('mood', 'adaptive')}
🔔 Notifications: {'On' if settings.get('notifications') else 'Off'}

To change your name: /myname <name>
"""

    await update.message.reply_text(settings_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - Show conversation statistics"""
    user_id = update.effective_user.id
    stats = memory.get_stats(user_id)

    from datetime import datetime
    last_interaction = stats.get('last_interaction', 'Never')

    stats_text = f"""*Our Friendship Stats:* 📊

💬 Total Messages: {stats['total_messages']}
📝 Notes Saved: {stats['notes_count']}
✅ Pending Tasks: {stats['tasks_count']}
⏰ Active Reminders: {stats['reminders_count']}
🕐 Last Chat: {last_interaction[:10] if last_interaction != 'Never' else 'Never'}

Thanks for being my friend! 💕
"""

    await update.message.reply_text(stats_text, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reset command - Clear all user data"""
    user_id = update.effective_user.id

    await update.message.reply_text(
        "⚠️ *WARNING* ⚠️\n\n"
        "This will delete ALL your data:\n"
        "- Notes\n"
        "- Tasks\n"
        "- Reminders\n"
        "- Profile\n\n"
        "This cannot be undone!\n\n"
        "Type /confirm_reset to confirm, or ignore to cancel.",
        parse_mode="Markdown"
    )


async def confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm reset command"""
    user_id = update.effective_user.id

    if memory.reset_user(user_id):
        ollama.clear_conversation(user_id)
        await update.message.reply_text(
            "All your data has been cleared. 🧹\n\n"
            "It's like we're meeting for the first time!\n"
            "Say /start to begin again."
        )
    else:
        await update.message.reply_text("Nothing to reset - we just met!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler - AI conversation - OPTIMIZED ASYNC"""
    user_id = update.effective_user.id
    message = update.message.text
    chat_id = update.message.chat_id

    # Send typing indicator IMMEDIATELY before any processing
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Get user info
    user_name = memory.get_name(user_id)

    # Detect mood from message
    mood = memory.detect_mood(message)

    # Get system prompt with current mood
    system_prompt = get_system_prompt(mood, user_name)

    # Build memory context (in parallel with typing indicator)
    memory_context = ""
    facts = memory.get_facts(user_id)
    if facts:
        memory_context = "I remember:\n"
        for fact in facts[-3:]:
            memory_context += f"- {fact['content']}\n"

    # Get pending tasks for context
    tasks = memory.get_tasks(user_id, completed=False)
    if tasks:
        memory_context += "\nCurrent tasks:\n"
        for task in tasks[:3]:
            memory_context += f"- {task['description']}\n"

    # Save message to stats
    memory.save_message(user_id, "user", message)

    # Generate AI response ASYNC (doesn't block other users!)
    try:
        response = await ollama.generate_with_memory(
            user_id,
            message,
            system_prompt,
            memory_context
        )
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        response = "I'm having trouble thinking right now. Can we try again in a moment?"

    # Send response
    await update.message.reply_text(response)


def main():
    """Initialize and run the bot"""
    # Check token
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("No Telegram token found! Set TELEGRAM_TOKEN environment variable.")
        print("ERROR: Please set your TELEGRAM_TOKEN environment variable!")
        sys.exit(1)

    logger.info(f"Starting {BOT_NAME}...")
    logger.info(f"Using model: {MODEL_NAME}")

    # Build application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("save", save_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("notes", notes_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("complete", complete_command))
    application.add_handler(CommandHandler("remind", remind_command))
    application.add_handler(CommandHandler("myname", myname_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("confirm_reset", confirm_reset))

    # Message handler (must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"{BOT_NAME} is running! Send messages on Telegram.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
