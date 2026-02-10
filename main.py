import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = None
GEMINI_API_KEY = None
GEMINI_MODEL = None
GEMINI_SYSTEM_PROMPT = None


MENU_BUTTON_START = "Начать диалог"
MENU_BUTTON_RECORD = "Записать запрос"


def build_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [MENU_BUTTON_START, MENU_BUTTON_RECORD],
        ],
        resize_keyboard=True,
    )


def load_config() -> None:
    load_dotenv()

    global TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, GEMINI_MODEL, GEMINI_SYSTEM_PROMPT

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_SYSTEM_PROMPT = os.getenv(
        "GEMINI_SYSTEM_PROMPT",
        "Ты полезный ассистент, который помогает пользователю.",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Отправьте голосовое сообщение, чтобы получить текст и ответ ИИ.",
            reply_markup=build_menu(),
        )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=build_menu(),
        )


async def handle_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Готов записать запрос. Отправьте голосовое сообщение.",
            reply_markup=build_menu(),
        )


def transcribe_audio(client: genai.Client, audio_bytes: bytes) -> str:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            "Сделай точную транскрипцию голосового сообщения. Верни только текст транскрипции без пояснений.",
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
        ],
    )
    return (response.text or "").strip()


def process_text(client: genai.Client, transcript_text: str) -> str:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            f"{GEMINI_SYSTEM_PROMPT}\n\nЗапрос пользователя:\n{transcript_text}",
        ],
    )
    return (response.text or "").strip()


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return

    if not GEMINI_API_KEY:
        await update.message.reply_text("Не задан GEMINI_API_KEY.")
        return

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    client = genai.Client(api_key=GEMINI_API_KEY)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "voice.ogg"
            await file.download_to_drive(custom_path=str(audio_path))
            audio_bytes = audio_path.read_bytes()

        transcript_text = transcribe_audio(client, audio_bytes)
        if not transcript_text:
            await update.message.reply_text("Не удалось распознать текст из голосового сообщения.")
            return

        assistant_reply = process_text(client, transcript_text)

        await update.message.reply_text(
            "Транскрипция:\n"
            f"{transcript_text}",
            reply_markup=build_menu(),
        )
        await update.message.reply_text(
            "Ответ ИИ:\n"
            f"{assistant_reply}",
            reply_markup=build_menu(),
        )
    except Exception:
        logger.exception("Gemini API request failed")
        await update.message.reply_text(
            "Не удалось обратиться к Gemini API. "
            "Проверьте GEMINI_API_KEY и доступ к Gemini API в аккаунте Google AI Studio.",
            reply_markup=build_menu(),
        )


def validate_env() -> None:
    if not TELEGRAM_BOT_TOKEN:
        message = (
            "Не задан TELEGRAM_BOT_TOKEN.\n"
            "1) Скопируйте пример: cp .env.example .env\n"
            "2) Укажите TELEGRAM_BOT_TOKEN в .env\n"
            "Или экспортируйте переменную окружения перед запуском."
        )
        logger.error(message)
        raise SystemExit(message)


def main() -> None:
    load_config()
    validate_env()

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", show_menu))
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(f"^({MENU_BUTTON_START}|{MENU_BUTTON_RECORD})$"),
            handle_menu_action,
        )
    )
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    application.run_polling()


if __name__ == "__main__":
    main()
