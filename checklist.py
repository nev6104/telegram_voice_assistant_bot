import sqlite3
from typing import List
from contextlib import contextmanager

DB = "checklist.db"

@contextmanager
def get_db_connection():
    """Provides a transactional, auto-closing SQLite connection context.
    
    Yields:
        sqlite3.Connection: A configured SQLite connection object.
    """
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initializes the database schema if the tasks table does not exist."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_task(user_id: int, text: str) -> None:
    """Adds a new task to the user's checklist.
    
    Args:
        user_id: The unique ID of the Telegram user.
        text: The description of the task.
    """
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO tasks (user_id, text) VALUES (?, ?)", 
            (user_id, text)
        )


def get_tasks(user_id: int) -> List[sqlite3.Row]:
    """Retrieves all tasks for the specified user ordered by ID.
    
    Args:
        user_id: The unique ID of the Telegram user.
        
    Returns:
        A list of sqlite3.Row objects representing the tasks.
    """
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY id", 
            (user_id,)
        ).fetchall()


def mark_done(user_id: int, position: int) -> bool:
    """Marks a task as done based on its 1-indexed display position.
    
    Args:
        user_id: The unique ID of the Telegram user.
        position: The 1-indexed position of the task in the list.
        
    Returns:
        True if the task was successfully updated, False otherwise.
    """
    tasks = get_tasks(user_id)
    if 1 <= position <= len(tasks):
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE tasks SET done = 1 WHERE id = ?", 
                (tasks[position - 1]["id"],)
            )
        return True
    return False


def delete_task(user_id: int, position: int) -> bool:
    """Deletes a task based on its 1-indexed display position.
    
    Args:
        user_id: The unique ID of the Telegram user.
        position: The 1-indexed position of the task in the list.
        
    Returns:
        True if the task was successfully deleted, False otherwise.
    """
    tasks = get_tasks(user_id)
    if 1 <= position <= len(tasks):
        with get_db_connection() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE id = ?", 
                (tasks[position - 1]["id"],)
            )
        return True
    return False


def clear_tasks(user_id: int) -> None:
    """Deletes all tasks for a specific user.
    
    Args:
        user_id: The unique ID of the Telegram user.
    """
    with get_db_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))


def format_list(user_id: int) -> str:
    """Formats the user's checklist as a user-friendly string.
    
    Args:
        user_id: The unique ID of the Telegram user.
        
    Returns:
        A formatted string representation of the checklist.
    """
    tasks = get_tasks(user_id)
    if not tasks:
        return "📋 List empty"
    
    lines = ["📋 Your list"]
    for i, task in enumerate(tasks, 1):
        icon = "✅" if task["done"] else "☐"
        lines.append(f"{icon} {i}. {task['text']}")
    return "\n".join(lines)