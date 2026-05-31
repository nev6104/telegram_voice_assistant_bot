import asyncio
import logging
import os
import subprocess
import tempfile
from typing import Dict, Any

import whisper
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from checklist import (
    init_db, add_task, mark_done,
    delete_task, clear_tasks, format_list
)
from intent_llm import parse_intent_llm

# Initialize logging system
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Load configuration and secrets safely
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN is not set in the environment or .env file.")
    raise SystemExit("Error: BOT_TOKEN is required. Please define it in a .env file.")

# Initialize core services
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
whisper_model = None


def load_whisper_model() -> None:
    """Synchronously loads the Whisper model.
    
    This is called during the application startup process to prevent blocking
    module imports or initial file reads.
    """
    global whisper_model
    logger.info("Initializing Whisper speech-to-text model ('medium')...")
    whisper_model = whisper.load_model("medium")
    logger.info("Whisper model successfully loaded and ready.")


async def run_ffmpeg(ogg_path: str, wav_path: str) -> None:
    """Executes FFmpeg in a non-blocking background thread to convert audio formats.
    
    Args:
        ogg_path: Absolute path to the source OGG/OPUS file.
        wav_path: Absolute path where the target WAV file should be saved.
        
    Raises:
        RuntimeError: If the conversion process fails.
    """
    def _execute():
        return subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, wav_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    try:
        await asyncio.to_thread(_execute)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed: {e}")
        raise RuntimeError("Failed to convert audio formats using FFmpeg.") from e


@dp.message(CommandStart())
async def start(message: Message) -> None:
    """Handles the /start command by greeting the user."""
    await message.answer("🎙 Send a voice message to manage your checklist.")


@dp.message()
async def handle_voice(message: Message) -> None:
    """Processes incoming voice messages, transcribes them, and performs database actions.
    
    This handles audio download, format conversion via FFmpeg, Whisper transcription,
    natural language intent parsing (with rule-based fallback), database operations,
    and replies with the updated checklist.
    """
    if not message.voice:
        return

    await message.answer("🎙 Processing voice message...")

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ogg_path = os.path.join(tmp_dir, "audio.ogg")
            wav_path = os.path.join(tmp_dir, "audio.wav")

            # Download the incoming voice message file from Telegram servers
            file_info = await bot.get_file(message.voice.file_id)
            await bot.download_file(file_info.file_path, destination=ogg_path)

            # Convert OGG format to 16kHz WAV format (required for optimal Whisper input)
            await run_ffmpeg(ogg_path, wav_path)

            # Transcribe the audio in a thread pool to avoid blocking the main async loop
            if whisper_model is None:
                raise RuntimeError("Whisper model is not loaded yet.")

            transcription_result = await asyncio.to_thread(
                whisper_model.transcribe, wav_path
            )
            text = transcription_result.get("text", "").strip()
            logger.info(f"User {message.from_user.id} audio transcript: '{text}'")

            # Parse user intent from transcript using async-safe LLM/Fallback architecture
            intent = await parse_intent_llm(text)
            action = intent.get("action", "unknown")
            logger.info(f"Parsed intent for user {message.from_user.id}: {intent}")

            reply_msg = ""
            user_id = message.from_user.id

            # Execute the database state updates
            if action == "add":
                tasks = intent.get("tasks", [])
                for task in tasks:
                    add_task(user_id, task)
                reply_msg = f"Added {len(tasks)} item(s) to your list."

            elif action == "done":
                positions = intent.get("positions", [])
                for pos in positions:
                    mark_done(user_id, pos)
                reply_msg = f"Marked {len(positions)} item(s) as completed."

            elif action == "delete":
                positions = intent.get("positions", [])
                for pos in positions:
                    delete_task(user_id, pos)
                reply_msg = f"Deleted {len(positions)} item(s) from your list."

            elif action == "clear":
                clear_tasks(user_id)
                reply_msg = "Cleared all tasks from your checklist."

            elif action == "show":
                reply_msg = "Here is your current checklist:"

            else:
                reply_msg = f"Sorry, I couldn't understand that instruction: \"{text}\""

            # Retrieve and format the updated checklist
            updated_list = format_list(user_id)
            await message.answer(f"{reply_msg}\n\n{updated_list}".strip())

    except Exception as e:
        logger.exception(f"Error handling voice message from user {message.from_user.id}: {e}")
        await message.answer("⚠️ Sorry, I encountered an unexpected error processing your voice message. Please try again.")


async def main() -> None:
    """Initializes checklist services, loads Whisper model, and starts Telegram polling."""
    # Ensure SQLite schema is prepared
    init_db()
    
    # Load model synchronously on startup (before entering active polling state)
    load_whisper_model()
    
    logger.info("Starting Telegram Bot long polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution terminated gracefully.")