#!/usr/bin/env python3
"""
Честная демонстрация системы чат-бота ИТМО
Показывает реальную работу с данными из parsed_programs.json
"""

import json
import os
from final_parser import generate_recommendations, categorize_subjects

def load_parsed_data():
    """Загружает реальные данные из parsed_programs.json"""
    try:
        with open('parsed_programs.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Файл parsed_programs.json не найден!")
        print("Сначала запустите: python final_parser.py <urls>")
        return None

def simulate_user_interaction(programs_data):
    """Симулирует реальное взаимодействие пользователя с ботом"""

    print("🤖 СИМУЛЯЦИЯ РЕАЛЬНОГО ДИАЛОГА С ЧАТ-БОТОМ ИТМО")
    print("=" * 60)
    print()

    # Приветствие бота
    program_names = list(programs_data.keys())
    programs_text = "\n".join([f"     • {name}" for name in program_names])

    print("🤖 Бот: Добро пожаловать в универсальный чат-бот ИТМО!")
    print("     Я помогу выбрать между программами магистратуры:")
    print(programs_text)
    print("     Что вы хотите узнать?")
    print()

    # Пользователь 1: Программист
    print("👤 Пользователь: Привет! Я программист на Python с опытом 3 года, интересуюсь машинным обучением")
    print()

    # Бот анализирует профиль и дает рекомендации
    user_background = "Я программист на Python с опытом 3 года, интересуюсь машинным обучением"

    # Находим программу с curriculum для рекомендаций
    program_with_curriculum = None
    for prog_name, prog_data in programs_data.items():
        if 'curriculum' in prog_data and prog_data['curriculum'].get('all_courses'):
            program_with_curriculum = prog_data
            break

    if program_with_curriculum:
        recommendations = generate_recommendations(user_background, program_with_curriculum['curriculum'])

        print("🤖 Бот: Отлично! Ваш профиль сохранен.")
        print(f"     Определен профиль: {recommendations.get('user_profile', 'Не определен')}")
        print("     Теперь могу дать персональные рекомендации!")
        print()

        # Пользователь спрашивает про экзамены
        print("👤 Пользователь: Какие экзамены нужно сдавать?")
        print()

        # Бот ищет в FAQ
        for prog_name, prog_data in programs_data.items():
            for faq in prog_data.get('faq', []):
                if 'экзамен' in faq['question'].lower():
                    answer = faq['answer'][:150] + "..." if len(faq['answer']) > 150 else faq['answer']
                    print(f"🤖 Бот: Найден ответ в программе '{prog_name}':")
                    print(f"     ❓ {faq['question']}")
                    print(f"     💡 {answer}")
                    print()
                    break
            break

        # Пользователь просит рекомендации по предметам
        print("👤 Пользователь: Дай рекомендации по предметам")
        print()

        print("🤖 Бот: На основе вашего профиля рекомендую:")
        for i, rec in enumerate(recommendations.get('recommendations', [])[:3], 1):
            print(f"     {i}. {rec['name']} ({rec['credits']} кредитов)")
            print(f"        Категория: {rec['category']}")
            print(f"        Причина: {rec['reason']}")
        print()

        # Пользователь просит сравнить программы
        print("👤 Пользователь: Сравни программы для меня")
        print()

        print("🤖 Бот: Персонализированное сравнение программ:")
        print()

        for i, (prog_name, prog_data) in enumerate(programs_data.items(), 1):
            # Вычисляем соответствие профилю
            match_score = calculate_program_match(user_background, prog_data)

            # Подсчитываем дисциплины
            total_courses = len(prog_data.get('curriculum', {}).get('all_courses', []))

            print(f"     {i}. {prog_name}")
            print(f"     • Соответствие вашему профилю: {match_score}%")
            if total_courses > 0:
                print(f"     • Всего дисциплин: {total_courses}")
            print(f"     • FAQ вопросов: {len(prog_data.get('faq', []))}")

            # Краткое описание фокуса программы
            if 'искусственный интеллект' in prog_name.lower():
                print("     • Фокус: ML Engineering, технические дисциплины")
            elif 'продукт' in prog_name.lower():
                print("     • Фокус: Product Management, бизнес-процессы")
            elif 'высоконагруженные' in prog_name.lower():
                print("     • Фокус: Системная архитектура, производительность")
            print()

        # Рекомендация лучшей программы
        best_program = max(programs_data.items(),
                          key=lambda x: calculate_program_match(user_background, x[1]))
        print(f"     ✅ Рекомендация: {best_program[0]}")
        print()

    else:
        print("🤖 Бот: ❌ Данные о дисциплинах не загружены.")
        print("     Запустите парсер с URL программ для получения рекомендаций.")
        print()

def calculate_program_match(background: str, program_data: dict) -> int:
    """Вычисляет соответствие программы профилю пользователя"""
    background_lower = background.lower()
    score = 50  # Базовый балл

    # Анализ по ключевым словам
    if any(word in background_lower for word in ['программист', 'разработчик', 'python', 'код']):
        if 'искусственный интеллект' in program_data.get('title', '').lower():
            score += 35
        elif 'программное обеспечение' in program_data.get('title', '').lower():
            score += 30
        elif 'продукт' in program_data.get('title', '').lower():
            score -= 5

    elif any(word in background_lower for word in ['менеджер', 'продукт', 'product', 'бизнес']):
        if 'продукт' in program_data.get('title', '').lower():
            score += 35
        elif 'искусственный интеллект' in program_data.get('title', '').lower():
            score -= 5

    elif any(word in background_lower for word in ['системы', 'архитектура', 'highload', 'нагрузка']):
        if 'высоконагруженные' in program_data.get('title', '').lower():
            score += 40

    return min(100, max(0, score))

def show_system_stats(programs_data):
    """Показывает статистику системы"""
    print("📊 СТАТИСТИКА СИСТЕМЫ")
    print("=" * 60)
    print()

    total_programs = len(programs_data)
    total_faq = sum(len(prog.get('faq', [])) for prog in programs_data.values())
    total_courses = sum(len(prog.get('curriculum', {}).get('all_courses', []))
                       for prog in programs_data.values())

    print(f"📚 Загружено программ: {total_programs}")
    print(f"❓ Всего FAQ вопросов: {total_faq}")
    print(f"🎓 Всего дисциплин: {total_courses}")
    print()

    print("📋 Детали по программам:")
    for prog_name, prog_data in programs_data.items():
        courses_count = len(prog_data.get('curriculum', {}).get('all_courses', []))
        faq_count = len(prog_data.get('faq', []))

        print(f"• {prog_name}:")
        print(f"  - Дисциплин: {courses_count}")
        print(f"  - FAQ: {faq_count}")

        if courses_count > 0:
            curriculum = prog_data['curriculum']
            elective_count = len(curriculum.get('elective_courses', []))
            mandatory_count = len(curriculum.get('mandatory_courses', []))
            print(f"  - Выборных: {elective_count}, Обязательных: {mandatory_count}")

            # Показываем категории дисциплин
            categorized = categorize_subjects(curriculum)
            categories_with_courses = {cat: len(courses) for cat, courses in categorized.items() if len(courses) > 0}
            if categories_with_courses:
                print(f"  - Категории: {', '.join([f'{cat}({count})' for cat, count in categories_with_courses.items()])}")
        print()

def main():
    """Главная функция демонстрации"""
    print("🎓 ЧЕСТНАЯ ДЕМОНСТРАЦИЯ СИСТЕМЫ ЧАТ-БОТА ИТМО")
    print("=" * 60)
    print()

    # Проверяем наличие данных
    if not os.path.exists('parsed_programs.json'):
        print("❌ Файл parsed_programs.json не найден!")
        print()
        print("📋 Для запуска демонстрации:")
        print("1. Сначала запустите парсер:")
        print("   python final_parser.py https://abit.itmo.ru/program/master/ai https://abit.itmo.ru/program/master/ai_product")
        print("2. Затем запустите демо:")
        print("   python final_demo.py")
        return

    # Загружаем реальные данные
    programs_data = load_parsed_data()
    if not programs_data:
        return

    # Показываем статистику системы
    show_system_stats(programs_data)

    # Симулируем диалог с пользователем
    simulate_user_interaction(programs_data)

    print("=" * 60)
    print("🚀 СИСТЕМА ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
    print()
    print("📝 Для тестирования через Telegram:")
    print("1. Получите токен у @BotFather")
    print("2. Замените YOUR_BOT_TOKEN_HERE в bot.py на ваш токен")
    print("3. Запустите: python bot.py")
    print("4. Найдите вашего бота в Telegram и начните диалог с /start")
    print()
    print("💡 Бот будет использовать те же данные, что показаны в этой демонстрации!")

if __name__ == "__main__":
    main()