import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from openai import AsyncOpenAI

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # @твой_канал

ai_client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь мне текст анонки, и я проверю его на соответствие правилам. "
        "Если всё чисто — я опубликую его в канале анонимно."
    )


async def handle_anon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if len(text) > 2000:
        await update.message.reply_text("❌ Анонка слишком длинная. Максимум 2000 символов.")
        return

    processing_msg = await update.message.reply_text("⏳ Проверяю анонку...")

    try:

        response = await ai_client.chat.completions.create(
            model="google/gemini-2.5-flash",  # Бесплатная и быстрая модель на OpenRouter
            messages=[
                {
                    "role": "system",
                    "content": "Ты — строгий модератор. Проверь текст на наличие: поисковых вопросов (ссылки, 'с кем открыть группу/кто сделает...?'), оценок ('оцените практику'), скрытое продвижение (самоанон, пустой восторг), личной информации (липсинги, голосовые сообщения, фотографии), спам, тематики не [кпоп, онлайн музыкальная индустрия, музыка], буллинг, сливы чужой личной информации без согласия второй стороны. Проверь на наличие эмодзи '🐾', предмет обсуждения/мнения (позитивное или негативное). Если текст чистый — ответь строго 'PASS'. Если есть нарушения — ответь 'FAIL: краткая причина'."
                },
                {"role": "user", "content": text}
            ],
            temperature=0.0
        )

        result = response.choices[0].message.content

        if "PASS" in result:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📝 Анонка:\n\n{text}")
            await processing_msg.edit_text("✅ Анонка прошла проверку и опубликована в канале!")
        else:
            reason = result.replace("FAIL:", "").strip()
            await processing_msg.edit_text(f"❌ Анонка отклонена.\nПричина: {reason}")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await processing_msg.edit_text("⚠️ Произошла ошибка при проверке. Попробуйте позже.")


if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_anon))

    print("Бот запущен...")
    app.run_polling()