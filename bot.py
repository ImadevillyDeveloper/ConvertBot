#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import tempfile
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "ТВОЙ_ТОКЕН_СЮДА")
MAX_FILE_SIZE_MB = 20
# =====================

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def convert_word_to_pdf(input_path: str, output_path: str) -> bool:
    """Конвертация через LibreOffice (внутри контейнера)"""
    try:
        libreoffice_path = "/usr/bin/libreoffice"
        
        if not os.path.exists(libreoffice_path):
            libreoffice_path = "libreoffice"
        
        cmd = [
            libreoffice_path,
            '--headless',
            '--nologo',
            '--norestore',
            '--convert-to', 'pdf',
            '--outdir', os.path.dirname(output_path),
            input_path
        ]
        
        logger.info(f"Запуск конвертации: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=90,
            env={**os.environ, 'HOME': '/tmp'}
        )
        
        if result.returncode != 0:
            logger.error(f"LibreOffice ошибка: {result.stderr}")
            return False
        
        original_name = Path(input_path).stem
        generated_pdf = Path(os.path.dirname(output_path)) / f"{original_name}.pdf"
        
        if generated_pdf.exists():
            if generated_pdf != Path(output_path):
                os.rename(generated_pdf, output_path)
            return True
        else:
            logger.error(f"PDF файл не найден: {generated_pdf}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Конвертация превысила 90 секунд")
        return False
    except Exception as e:
        logger.error(f"Ошибка конвертации: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    chat_type = update.effective_chat.type
    
    if chat_type == 'private':
        text = (
            "🤖 *Word → PDF Конвертер*\n\n"
            "Отправь мне `.docx` или `.doc` файл, и я превращу его в PDF.\n\n"
            "📌 *Команды:*\n"
            "/help — справка\n"
            "/id — узнать свой ID\n\n"
            "🔥 Разработан проектом «Мой.Маршрут»"
        )
    else:
        text = (
            "👋 *Привет, группа!*\n\n"
            "Я конвертирую Word файлы в PDF.\n\n"
            "📌 *Как использовать:*\n"
            "• Отправьте Word файл в чат\n"
            "• Затем **ответьте на это сообщение** командой `/convert`\n\n"
            "📌 *Команды:*\n"
            "/help — подробная справка\n"
            "/id — информация о чате\n\n"
            "🔥 Разработан проектом «Мой.Маршрут»"
        )
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    chat_type = update.effective_chat.type
    
    if chat_type == 'private':
        text = (
            "📖 *Справка*\n\n"
            "🔹 *Как пользоваться:*\n"
            "Отправьте мне Word файл (.docx или .doc)\n\n"
            "🔹 *Команды:*\n"
            "/start — приветствие\n"
            "/help — эта справка\n"
            "/id — узнать свой ID\n"
            "/health — проверка работы бота\n\n"
            "🔹 *Ограничения:*\n"
            f"• Максимальный размер: {MAX_FILE_SIZE_MB} МБ\n"
            "• Время конвертации: до 60 секунд"
        )
    else:
        text = (
            "📖 *Справка для группы*\n\n"
            "🔹 *Как использовать:*\n"
            "1️⃣ Отправьте Word файл (.docx или .doc) в чат\n"
            "2️⃣ **Ответьте на это сообщение** командой `/convert`\n\n"
            "🔹 *Команды:*\n"
            "/start — приветствие\n"
            "/help — эта справка\n"
            "/convert — конвертировать файл (ответьте на него)\n"
            "/id — информация о чате\n"
            "/health — проверка работы бота\n\n"
            "🔹 *Ограничения:*\n"
            f"• Максимальный размер: {MAX_FILE_SIZE_MB} МБ\n\n"
            "💡 *Пример:*\n"
            "Пользователь отправляет `документ.docx`\n"
            "Другой пользователь отвечает на это сообщение: `/convert`\n"
            "Бот отправляет PDF"
        )
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /id — показывает ID пользователя и чата"""
    user = update.effective_user
    chat = update.effective_chat
    
    text = (
        f"🆔 *Ваш ID:* `{user.id}`\n"
        f"📝 *Имя:* {user.first_name}\n"
        f"💬 *Чат ID:* `{chat.id}`\n"
        f"📂 *Тип чата:* {chat.type}"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /convert — конвертирует файл, на который ответили"""
    user_name = update.effective_user.first_name
    chat_type = update.effective_chat.type
    
    # Проверяем, есть ли ответ на сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ *Как использовать /convert:*\n"
            "Ответьте на сообщение с Word файлом командой `/convert`\n\n"
            "📌 *Пример:*\n"
            "1. Пользователь отправляет файл\n"
            "2. Вы отвечаете на это сообщение: `/convert`\n"
            "3. Бот присылает PDF",
            parse_mode='Markdown'
        )
        return
    
    # Проверяем, есть ли в ответном сообщении документ
    replied_msg = update.message.reply_to_message
    if not replied_msg.document:
        await update.message.reply_text(
            "❌ Ответьте на сообщение, которое содержит Word файл.\n\n"
            "Команда `/convert` работает только в ответ на файл.",
            parse_mode='Markdown'
        )
        return
    
    document = replied_msg.document
    file_name = document.file_name
    
    # Проверяем расширение
    if not file_name.lower().endswith(('.docx', '.doc')):
        await update.message.reply_text("❌ Файл должен быть в формате `.docx` или `.doc`", parse_mode='Markdown')
        return
    
    # Проверяем размер
    if document.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(f"❌ Файл больше {MAX_FILE_SIZE_MB} МБ")
        return
    
    # Показываем, кто запросил конвертацию
    await update.message.reply_text(f"👤 *{user_name}*, конвертирую файл *{file_name}*...", parse_mode='Markdown')
    
    status_msg = await update.message.reply_text("⏳ Скачиваю файл...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file = await context.bot.get_file(document.file_id)
            input_path = os.path.join(temp_dir, file_name)
            await file.download_to_drive(input_path)
            
            await status_msg.edit_text("🔄 Конвертирую в PDF...")
            
            output_name = Path(file_name).stem + ".pdf"
            output_path = os.path.join(temp_dir, output_name)
            
            success = convert_word_to_pdf(input_path, output_path)
            
            if success and os.path.exists(output_path):
                await status_msg.edit_text("📤 Отправляю PDF...")
                with open(output_path, 'rb') as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=output_name,
                        caption=f"✅ Готово! Конвертировал *{user_name}*",
                        parse_mode='Markdown'
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text(
                    "❌ Не удалось сконвертировать файл.\n"
                    "Проверь, что документ не повреждён и содержит текст."
                )
                
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Техническая ошибка. Попробуй позже.")

async def handle_document_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка документов в ЛИЧНЫХ СООБЩЕНИЯХ (автоматическая конвертация)"""
    user_name = update.effective_user.first_name
    
    document = update.message.document
    file_name = document.file_name
    
    if not file_name.lower().endswith(('.docx', '.doc')):
        await update.message.reply_text("❌ Отправь файл в формате `.docx` или `.doc`", parse_mode='Markdown')
        return
    
    if document.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(f"❌ Файл больше {MAX_FILE_SIZE_MB} МБ")
        return
    
    status_msg = await update.message.reply_text("⏳ Скачиваю файл...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file = await context.bot.get_file(document.file_id)
            input_path = os.path.join(temp_dir, file_name)
            await file.download_to_drive(input_path)
            
            await status_msg.edit_text("🔄 Конвертирую в PDF...")
            
            output_name = Path(file_name).stem + ".pdf"
            output_path = os.path.join(temp_dir, output_name)
            
            success = convert_word_to_pdf(input_path, output_path)
            
            if success and os.path.exists(output_path):
                await status_msg.edit_text("📤 Отправляю PDF...")
                with open(output_path, 'rb') as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=output_name,
                        caption=f"✅ Готово!"
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text(
                    "❌ Не удалось сконвертировать файл.\n"
                    "Проверь, что документ не повреждён и содержит текст."
                )
                
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Техническая ошибка. Попробуй позже.")

async def handle_document_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка документов в ГРУППАХ (только напоминание, без конвертации)"""
    user_name = update.effective_user.first_name
    file_name = update.message.document.file_name
    
    # Только для Word файлов показываем напоминание
    if file_name.lower().endswith(('.docx', '.doc')):
        await update.message.reply_text(
            f"📄 *{user_name}*, файл *{file_name}* получен!\n\n"
            "Чтобы конвертировать его в PDF:\n"
            "1️⃣ Ответьте на это сообщение\n"
            "2️⃣ Напишите команду `/convert`\n\n"
            "💡 Подробнее: /help",
            parse_mode='Markdown'
        )
    # Для остальных файлов просто игнорируем

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /health - проверка работы LibreOffice"""
    await update.message.reply_text("🏥 Проверка системы...")
    
    try:
        result = subprocess.run(
            ['libreoffice', '--version'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            await update.message.reply_text(f"✅ LibreOffice работает:\n`{result.stdout.strip()}`", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ LibreOffice не отвечает")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def greet_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие при добавлении бота в группу"""
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text(
                "👋 Привет! Я конвертирую Word файлы в PDF.\n\n"
                "📌 *Как я работаю в группах:*\n"
                "• Вы отправляете Word файл\n"
                "• Отвечаете на него командой `/convert`\n"
                "• Я присылаю PDF\n\n"
                "📌 Отправь /help для подробной справки",
                parse_mode='Markdown'
            )
            break

def main():
    """Запуск бота"""
    if not TOKEN or TOKEN == "ТВОЙ_ТОКЕН_СЮДА":
        logger.error("❌ Токен не установлен! Используй переменную окружения TELEGRAM_BOT_TOKEN")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("convert", convert_command))
    app.add_handler(CommandHandler("health", health_check))
    
    # Обработка документов:
    # - в личке: автоматическая конвертация
    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.ChatType.PRIVATE, 
        handle_document_private
    ))
    
    # - в группах: только напоминание (без конвертации)
    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.ChatType.GROUP & filters.ChatType.SUPERGROUP, 
        handle_document_group
    ))
    
    # Приветствие при добавлении в группу
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_chat_members))
    
    logger.info("🤖 Бот запущен!")
    logger.info("📌 В личке: авто-конвертация")
    logger.info("📌 В группах: только по команде /convert")
    app.run_polling()

if __name__ == "__main__":
    main()