import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = None
OPENAI_API_KEY = None
OPENAI_AUDIO_MODEL = None
OPENAI_CHAT_MODEL = None
OPENAI_SYSTEM_PROMPT = None


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

    global TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, OPENAI_AUDIO_MODEL, OPENAI_CHAT_MODEL, OPENAI_SYSTEM_PROMPT

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_AUDIO_MODEL = os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-transcribe")
    OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    OPENAI_SYSTEM_PROMPT = os.getenv(
        "OPENAI_SYSTEM_PROMPT",
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


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return

    if not OPENAI_API_KEY:
        await update.message.reply_text("Не задан OPENAI_API_KEY.")
        return

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "voice.ogg"
            await file.download_to_drive(custom_path=str(audio_path))

            with audio_path.open("rb") as audio_file:
                transcription = await client.audio.transcriptions.create(
                    model=OPENAI_AUDIO_MODEL,
                    file=audio_file,
                )

        transcript_text = (transcription.text or "").strip()
        if not transcript_text:
            await update.message.reply_text("Не удалось распознать текст из голосового сообщения.")
            return

        completion = await client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                {"role": "user", "content": transcript_text},
            ],
        )

        assistant_reply = ""
        if completion.choices:
            assistant_reply = completion.choices[0].message.content or ""

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
        logger.exception("OpenAI API request failed")
        await update.message.reply_text(
            "Не удалось обратиться к OpenAI API. "
            "Проверьте OPENAI_API_KEY и наличие средств/кредитов в аккаунте.",
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
