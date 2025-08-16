#!/usr/bin/env python3
"""
Тестирование улучшенной системы вопросов и ответов
"""

import json
from bot import ITMOChatBot

def test_qa_system():
    """Тестирует систему Q&A с различными вопросами"""

    # Создаем экземпляр бота (без токена для тестирования)
    bot = ITMOChatBot("test_token")

    if not bot.programs_data:
        print("❌ Данные программ не загружены")
        return

    # Тестовые вопросы
    test_questions = [
        "какое количество мест?",
        "Содержание программы искусственный интеллект какое?",
        "Содержании программ",
        "Сколько мест на программе ИИ?",
        "Какая стоимость обучения?",
        "Как поступить на магистратуру?",
        "Какие экзамены нужно сдавать?",
        "Сколько длится обучение?",
        "Что изучают на программе?",
        "Какие требования к поступлению?",
        "Есть ли бюджетные места?",
        "Кто преподает на программе?",
        "Какие карьерные возможности?",
        "Стипендия есть?",
        "Документы для поступления",
        "Привет как дела?"  # Нерелевантный вопрос
    ]

    print("🧪 Тестирование системы вопросов и ответов")
    print(f"📊 Загружено программ: {len(bot.programs_data)}")

    total_faq = sum(len(prog.get('faq', [])) for prog in bot.programs_data.values())
    print(f"❓ Всего FAQ вопросов: {total_faq}")
    print("=" * 80)

    relevant_count = 0
    answered_count = 0

    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. 🤔 **Вопрос:** {question}")

        # Проверяем релевантность
        is_relevant = bot.is_relevant_question(question)
        print(f"   🎯 **Релевантный:** {'✅ Да' if is_relevant else '❌ Нет'}")

        if is_relevant:
            relevant_count += 1

            # Ищем ответ
            answer = bot.find_best_answer(question)
            if answer:
                answered_count += 1
                print(f"   💡 **Ответ найден:** ✅ Да (релевантность: {answer['score']:.2f})")
                print(f"   📋 **Программа:** {answer['program']}")
                print(f"   ❓ **Похожий вопрос:** {answer['question'][:100]}...")

                matched_words = answer.get('matched_words', [])
                if matched_words:
                    print(f"   🔍 **Совпавшие слова:** {', '.join(matched_words[:5])}")

                print(f"   📝 **Ответ:** {answer['answer'][:150]}...")
            else:
                print(f"   💡 **Ответ найден:** ❌ Нет")

        print("-" * 60)

    print(f"\n📊 **Статистика тестирования:**")
    print(f"• Всего вопросов: {len(test_questions)}")
    print(f"• Релевантных: {relevant_count} ({relevant_count/len(test_questions)*100:.1f}%)")
    print(f"• С ответами: {answered_count} ({answered_count/relevant_count*100:.1f}% от релевантных)" if relevant_count > 0 else "• С ответами: 0")
    print(f"• Общий успех: {answered_count/len(test_questions)*100:.1f}%")

if __name__ == "__main__":
    test_qa_system()