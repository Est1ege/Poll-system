#!/usr/bin/env python
"""
Скрипт для автоматического обновления переводов Django проекта
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None):
    """Выполняет команду и возвращает результат"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Ошибка выполнения команды: {command}")
            print(f"Ошибка: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Исключение при выполнении команды {command}: {e}")
        return False

def update_translations():
    """Обновляет переводы для всех языков"""
    # Путь к проекту
    project_path = Path(__file__).parent
    
    print("🔄 Обновление переводов...")
    
    # 1. Извлекаем сообщения из кода
    print("📝 Извлечение сообщений из кода...")
    if not run_command("python manage.py makemessages -l ru -l kk", cwd=project_path):
        print("❌ Ошибка при извлечении сообщений")
        return False
    
    # 2. Компилируем переводы
    print("🔨 Компиляция переводов...")
    if not run_command("python manage.py compilemessages", cwd=project_path):
        print("❌ Ошибка при компиляции переводов")
        return False
    
    print("✅ Переводы успешно обновлены!")
    return True

def add_new_translations():
    """Добавляет новые переводы в файлы .po"""
    print("📋 Добавление новых переводов...")
    
    # Список новых переводов для добавления
    new_translations = {
        # Новые переводы для шаринга
        "Share Poll": "Поделиться опросом",
        "Share Link": "Ссылка для шаринга",
        "Copy": "Копировать",
        "Copied!": "Скопировано!",
        "Share on Social Media": "Поделиться в социальных сетях",
        "Poll Statistics": "Статистика опроса",
        "Votes": "Голосов",
        "Choices": "Вариантов",
        "Status": "Статус",
        "Active": "Активен",
        "Closed": "Закрыт",
        "View Poll": "Посмотреть опрос",
        "Back to Polls": "Вернуться к опросам",
        "Share": "Поделиться",
        
        # Новые переводы для создания опросов
        "Create New Poll": "Создать новый опрос",
        "Poll Information": "Информация об опросе",
        "Answer Choices": "Варианты ответов",
        "Number of choices": "Количество вариантов",
        "Check this if this is a quiz with correct answers": "Отметьте, если это викторина с правильными ответами",
        "Allow users to discuss this poll": "Разрешить пользователям обсуждать этот опрос",
        "Create Poll": "Создать опрос",
        "Enter your question here...": "Введите ваш вопрос здесь...",
        "Optional description...": "Необязательное описание...",
        "Correct answer": "Правильный ответ",
        "For a quiz, you must select at least one correct answer.": "Для викторины необходимо выбрать хотя бы один правильный ответ.",
        
        # Новые переводы для личного кабинета
        "Personal Account": "Личный кабинет",
        "Welcome back": "Добро пожаловать",
        "My Polls": "Мои опросы",
        "Total Votes": "Всего голосов",
        "Votes Given": "Отдано голосов",
        "Days Registered": "Дней с регистрации",
        "Username": "Имя пользователя",
        "Email": "Электронная почта",
        "Date Joined": "Дата регистрации",
        "Last Login": "Последний вход",
        "Recent Polls": "Недавние опросы",
        "Created": "Создан",
        "Profile": "Профиль",
        "Logout": "Выход",
        
        # Общие переводы
        "Home": "Главная",
        "current": "текущая",
        "Polls": "Опросы",
        "Register": "Регистрация",
        "First": "Первая",
        "Previous": "Предыдущая",
        "Next": "Следующая",
        "Last": "Последняя",
        "No polls found.": "Опросы не найдены.",
        "Poll Detail": "Детали опроса",
        "Back to Polls": "Вернуться к опросам",
        "Search": "Поиск",
        "Name": "Имя",
        "Date": "Дата",
        "Vote": "Голос",
        "Are you sure?": "Вы уверены?",
        "End Poll": "Завершить опрос",
        "Edit": "Редактировать",
        "Delete": "Удалить",
        "Add": "Добавить",
        "Update": "Обновить",
        "Cancel": "Отмена",
        "Close": "Закрыть",
        "Welcome to Polls List!": "Добро пожаловать в список опросов!",
        "Welcome to polls List!": "Добро пожаловать в список опросов!",
        "Poll & Choices added successfully.": "Опрос и варианты успешно добавлены.",
        "Poll updated successfully.": "Опрос успешно обновлен.",
        "Poll deleted successfully.": "Опрос успешно удален.",
        "Choice added successfully.": "Вариант успешно добавлен.",
        "Choice updated successfully.": "Вариант успешно обновлен.",
        "Choice deleted successfully.": "Вариант успешно удален.",
        "No choice selected!": "Вариант не выбран!",
        "You already voted this poll!": "Вы уже голосовали в этом опросе!",
        "This is a quiz": "Это викторина",
        "Update choice": "Изменить вариант",
        "Add new choice": "Добавить вариант",
        "Create new poll": "Создать опрос",
        "Edit poll": "Редактировать опрос",
        "Add Choice": "Добавить вариант",
        "Choices": "Варианты",
        "Result for: %(poll.text)s": "Результаты для: %(poll.text)s",
        "Result for: %(text)s": "Результаты для: %(text)s",
        "\"%(text)s\" Has Ended Polling!": "\"%(text)s\" голосование завершено!",
        "Total: %(total)s votes": "Всего голосов: %(total)s",
        "%(name)s — %(percent)s%%": "%(name)s — %(percent)s%%",
        "%(name|truncatewords:2)s — %(percent)s%%": "%(name|truncatewords:2)s — %(percent)s%%",
        "Back To Polls": "Вернуться к опросам",
        "Polls details page": "Страница опроса",
        "Vote now": "Голосовать сейчас",
        "Login": "Войти",
        "Don't have an account?": "Нет аккаунта?",
        "Sign Up": "Зарегистрироваться",
        "Already have an account?": "Уже есть аккаунт?",
        "Login Here": "Войти",
        "English": "Английский",
        "Русский": "Русский",
        "Қазақша": "Казахский",
    }
    
    # Обновляем русский перевод
    ru_po_path = Path("locale/ru/LC_MESSAGES/django.po")
    if ru_po_path.exists():
        print(f"📝 Обновление {ru_po_path}...")
        update_po_file(ru_po_path, new_translations)
    
    # Обновляем казахский перевод
    kk_po_path = Path("locale/kk/LC_MESSAGES/django.po")
    if kk_po_path.exists():
        print(f"📝 Обновление {kk_po_path}...")
        # Для казахского языка можно добавить переводы или оставить как есть
        pass

def update_po_file(po_path, translations):
    """Обновляет файл .po новыми переводами"""
    try:
        with open(po_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Добавляем новые переводы в конец файла
        new_content = ""
        for msgid, msgstr in translations.items():
            if f'msgid "{msgid}"' not in content:
                new_content += f'\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n'
        
        if new_content:
            with open(po_path, 'a', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Добавлено {len(translations)} новых переводов в {po_path}")
        else:
            print(f"ℹ️ Все переводы уже существуют в {po_path}")
            
    except Exception as e:
        print(f"❌ Ошибка при обновлении {po_path}: {e}")

if __name__ == "__main__":
    print("🚀 Запуск обновления переводов...")
    
    # Добавляем новые переводы
    add_new_translations()
    
    # Обновляем переводы
    if update_translations():
        print("🎉 Все переводы успешно обновлены!")
    else:
        print("💥 Произошла ошибка при обновлении переводов")
        sys.exit(1) 