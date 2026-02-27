"""
M.E.R.C.Y Memory Manager
Handles all data storage, retrieval, and management using SQLite for performance
"""
import json
import sqlite3
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiosqlite

class MemoryManager:
    """Manages user data, memory, tasks, notes, and reminders using SQLite"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "mercy_memory.db"
        self._init_db()
        self._pending_saves = 0
        self._last_save_time = datetime.now()
        self._save_lock = asyncio.Lock()

    def _init_db(self):
        """Initialize SQLite database with tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT DEFAULT 'friend',
                    username TEXT DEFAULT '',
                    gender TEXT DEFAULT 'unknown',
                    preferences TEXT DEFAULT '{}',
                    interests TEXT DEFAULT '[]',
                    important_dates TEXT DEFAULT '{}',
                    language TEXT DEFAULT 'mixed',
                    mood TEXT DEFAULT 'adaptive',
                    notifications INTEGER DEFAULT 1,
                    total_messages INTEGER DEFAULT 0,
                    last_interaction TEXT,
                    created_at TEXT
                )
            ''')

            # Notes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    note_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    content TEXT,
                    tags TEXT DEFAULT '[]',
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    description TEXT,
                    due_date TEXT DEFAULT '',
                    completed INTEGER DEFAULT 0,
                    priority TEXT DEFAULT 'normal',
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Reminders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    reminder_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    message TEXT,
                    remind_at TEXT,
                    completed INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Saved facts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS facts (
                    fact_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    content TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Conversation patterns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    pattern TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            conn.commit()

    async def _get_or_create_user(self, user_id: int) -> Dict:
        """Get or create user data"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()

            if not row:
                # Create new user
                now = datetime.now().isoformat()
                await db.execute('''
                    INSERT INTO users (user_id, name, created_at, last_interaction)
                    VALUES (?, 'friend', ?, ?)
                ''', (user_id, now, now))
                await db.commit()
                return {
                    "user_id": user_id,
                    "name": "friend",
                    "username": "",
                    "gender": "unknown",
                    "preferences": {},
                    "interests": [],
                    "important_dates": {},
                    "language": "mixed",
                    "mood": "adaptive",
                    "notifications": True,
                    "total_messages": 0,
                    "last_interaction": now
                }

            # Convert row to dict
            columns = [description[0] for description in cursor.description]
            user_data = dict(zip(columns, row))
            user_data["preferences"] = json.loads(user_data.get("preferences", "{}"))
            user_data["interests"] = json.loads(user_data.get("interests", "[]"))
            user_data["important_dates"] = json.loads(user_data.get("important_dates", "{}"))
            user_data["notifications"] = bool(user_data.get("notifications", 1))
            return user_data

    # === PROFILE MANAGEMENT ===
    def get_profile(self, user_id: int) -> Dict:
        """Get user profile"""
        # Run in executor to make it async-compatible
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "username": row["username"],
                    "gender": row["gender"],
                    "preferences": json.loads(row["preferences"] or "{}"),
                    "interests": json.loads(row["interests"] or "[]"),
                    "important_dates": json.loads(row["important_dates"] or "{}")
                }
            return {"user_id": user_id, "name": "friend"}

    def update_profile(self, user_id: int, **kwargs) -> bool:
        """Update user profile fields"""
        allowed_fields = ["name", "username", "gender", "preferences", "interests", "important_dates"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        with sqlite3.connect(self.db_path) as conn:
            for field, value in updates.items():
                if field in ["preferences", "interests", "important_dates"]:
                    value = json.dumps(value)
                conn.execute(
                    f"UPDATE users SET {field} = ? WHERE user_id = ?",
                    (value, user_id)
                )
            conn.commit()
        return True

    def set_name(self, user_id: int, name: str) -> bool:
        """Set user's preferred name"""
        return self.update_profile(user_id, name=name)

    def get_name(self, user_id: int) -> str:
        """Get user's name"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else "friend"

    # === MOOD DETECTION ===
    def detect_mood(self, message: str) -> str:
        """Detect mood based on message content"""
        message_lower = message.lower()
        from bot_config import MOODS

        mood_scores = {}
        for mood, config in MOODS.items():
            score = sum(1 for trigger in config["triggers"] if trigger in message_lower)
            if score > 0:
                mood_scores[mood] = score

        return max(mood_scores, key=mood_scores.get) if mood_scores else "caring"

    # === NOTES MANAGEMENT ===
    def add_note(self, user_id: int, content: str, tags: List[str] = None) -> str:
        """Add a new note"""
        note_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        tags_json = json.dumps(tags or [])

        # Ensure user exists
        self._ensure_user_exists(user_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO notes (note_id, user_id, content, tags, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (note_id, user_id, content, tags_json, now))
            conn.commit()
        return note_id

    def get_notes(self, user_id: int, tag: str = None) -> List[Dict]:
        """Get user notes, optionally filtered by tag"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if tag:
                cursor.execute('''
                    SELECT * FROM notes WHERE user_id = ? AND tags LIKE ?
                    ORDER BY created_at DESC
                ''', (user_id, f'%"{tag}"%'))
            else:
                cursor.execute('''
                    SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC
                ''', (user_id,))

            rows = cursor.fetchall()
            return [{"note_id": row["note_id"], "content": row["content"],
                    "tags": json.loads(row["tags"]), "created_at": row["created_at"]}
                   for row in rows]

    def delete_note(self, user_id: int, note_id: str) -> bool:
        """Delete a note by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM notes WHERE note_id = ? AND user_id = ?",
                (note_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    # === TASKS MANAGEMENT ===
    def add_task(self, user_id: int, description: str, due_date: str = "") -> str:
        """Add a new task"""
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        self._ensure_user_exists(user_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO tasks (task_id, user_id, description, due_date, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, user_id, description, due_date, now))
            conn.commit()
        return task_id

    def get_tasks(self, user_id: int, completed: bool = False) -> List[Dict]:
        """Get tasks, optionally filtered by completion status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM tasks WHERE user_id = ? AND completed = ?
                ORDER BY priority DESC, created_at DESC
            ''', (user_id, 1 if completed else 0))

            rows = cursor.fetchall()
            return [{"task_id": row["task_id"], "description": row["description"],
                    "due_date": row["due_date"], "completed": bool(row["completed"]),
                    "priority": row["priority"]} for row in rows]

    def complete_task(self, user_id: int, task_id: str) -> bool:
        """Mark task as completed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks SET completed = 1
                WHERE task_id = ? AND user_id = ?
            ''', (task_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_task(self, user_id: int, task_id: str) -> bool:
        """Delete a task"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM tasks WHERE task_id = ? AND user_id = ?",
                (task_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    # === REMINDERS MANAGEMENT ===
    def add_reminder(self, user_id: int, message: str, remind_at: str) -> str:
        """Add a reminder"""
        reminder_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        self._ensure_user_exists(user_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO reminders (reminder_id, user_id, message, remind_at, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (reminder_id, user_id, message, remind_at, now))
            conn.commit()
        return reminder_id

    def get_reminders(self, user_id: int) -> List[Dict]:
        """Get pending reminders"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM reminders WHERE user_id = ? AND completed = 0
                ORDER BY remind_at ASC
            ''', (user_id,))

            rows = cursor.fetchall()
            return [{"reminder_id": row["reminder_id"], "message": row["message"],
                    "remind_at": row["remind_at"]} for row in rows]

    def complete_reminder(self, user_id: int, reminder_id: str) -> bool:
        """Mark reminder as completed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reminders SET completed = 1
                WHERE reminder_id = ? AND user_id = ?
            ''', (reminder_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    # === SAVED FACTS ===
    def save_fact(self, user_id: int, fact: str) -> str:
        """Save a fact about the user"""
        fact_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        self._ensure_user_exists(user_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO facts (fact_id, user_id, content, created_at)
                VALUES (?, ?, ?, ?)
            ''', (fact_id, user_id, fact, now))
            conn.commit()
        return fact_id

    def get_facts(self, user_id: int) -> List[Dict]:
        """Get all saved facts about user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM facts WHERE user_id = ? ORDER BY created_at DESC
            ''', (user_id,))

            rows = cursor.fetchall()
            return [{"fact_id": row["fact_id"], "content": row["content"],
                    "created_at": row["created_at"]} for row in rows]

    # === CONVERSATION MEMORY ===
    def save_message(self, user_id: int, role: str, content: str):
        """Save message to conversation history and update stats"""
        self._ensure_user_exists(user_id)

        with sqlite3.connect(self.db_path) as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                UPDATE users SET total_messages = total_messages + 1, last_interaction = ?
                WHERE user_id = ?
            ''', (now, user_id))
            conn.commit()

    def get_conversation_context(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Get recent conversation context"""
        # This can be extended to store actual conversation history
        return []

    # === STATS ===
    def get_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get user stats
            cursor.execute('''
                SELECT total_messages, last_interaction FROM users WHERE user_id = ?
            ''', (user_id,))
            user_row = cursor.fetchone()

            # Get counts
            cursor.execute('SELECT COUNT(*) FROM notes WHERE user_id = ?', (user_id,))
            notes_count = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 0', (user_id,))
            tasks_count = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM reminders WHERE user_id = ? AND completed = 0', (user_id,))
            reminders_count = cursor.fetchone()[0]

            return {
                "total_messages": user_row["total_messages"] if user_row else 0,
                "notes_count": notes_count,
                "tasks_count": tasks_count,
                "reminders_count": reminders_count,
                "last_interaction": user_row["last_interaction"] if user_row else "Never"
            }

    def reset_user(self, user_id: int) -> bool:
        """Reset all user data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Delete all user data
            tables = ["notes", "tasks", "reminders", "facts", "conversation_patterns"]
            for table in tables:
                cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))

            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_settings(self, user_id: int) -> Dict:
        """Get user settings"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT language, mood, notifications FROM users WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "language": row["language"],
                    "mood": row["mood"],
                    "notifications": bool(row["notifications"])
                }
            return {"language": "mixed", "mood": "adaptive", "notifications": True}

    def update_settings(self, user_id: int, **kwargs) -> bool:
        """Update user settings"""
        allowed_fields = ["language", "mood", "notifications"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        with sqlite3.connect(self.db_path) as conn:
            for field, value in updates.items():
                conn.execute(
                    f"UPDATE users SET {field} = ? WHERE user_id = ?",
                    (value, user_id)
                )
            conn.commit()
        return True

    def _ensure_user_exists(self, user_id: int):
        """Ensure user record exists in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO users (user_id, name, created_at, last_interaction)
                    VALUES (?, 'friend', ?, ?)
                ''', (user_id, now, now))
                conn.commit()
