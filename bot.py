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
        # В Docker контейнере путь к LibreOffice
        libreoffice_path = "/usr/bin/libreoffice"
        
        if not os.path.exists(libreoffice_path):
            # Альтернативный путь (для разных версий)
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
            env={**os.environ, 'HOME': '/tmp'}  # Домашняя директория для LibreOffice
        )
        
        if result.returncode != 0:
            logger.error(f"LibreOffice ошибка: {result.stderr}")
            return False
        
        # LibreOffice создаёт PDF с оригинальным именем
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
    await update.message.reply_text(
        "🤖 *Word → PDF Конвертер*\n\n"
        "Отправь мне `.docx` или `.doc` файл, и я превращу его в PDF.\n\n"
        "🔥 Разработан проектом «Мой.Маршрут»",
        parse_mode='Markdown'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка документов"""
    document = update.message.document
    file_name = document.file_name
    
    # Проверка расширения
    if not file_name.lower().endswith(('.docx', '.doc')):
        await update.message.reply_text("❌ Отправь файл в формате `.docx` или `.doc`", parse_mode='Markdown')
        return
    
    # Проверка размера
    if document.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(f"❌ Файл больше {MAX_FILE_SIZE_MB} МБ")
        return
    
    status_msg = await update.message.reply_text("⏳ Скачиваю файл...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Скачиваем
            file = await context.bot.get_file(document.file_id)
            input_path = os.path.join(temp_dir, file_name)
            await file.download_to_drive(input_path)
            
            await status_msg.edit_text("🔄 Конвертирую в PDF (это может занять до 30 секунд)...")
            
            # Конвертируем
            output_name = Path(file_name).stem + ".pdf"
            output_path = os.path.join(temp_dir, output_name)
            
            success = convert_word_to_pdf(input_path, output_path)
            
            if success and os.path.exists(output_path):
                await status_msg.edit_text("📤 Отправляю PDF...")
                with open(output_path, 'rb') as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=output_name,
                        caption="✅ Готово!"
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

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /health - проверка работы LibreOffice"""
    await update.message.reply_text("🏥 Проверка системы...")
    
    # Проверяем LibreOffice
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

def main():
    """Запуск бота"""
    if not TOKEN or TOKEN == "ТВОЙ_ТОКЕН_СЮДА":
        logger.error("❌ Токен не установлен! Используй переменную окружения TELEGRAM_BOT_TOKEN")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("health", health_check))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    logger.info("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()