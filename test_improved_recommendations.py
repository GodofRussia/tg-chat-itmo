#!/usr/bin/env python3
"""
Тестирование улучшенной системы рекомендаций
"""

import json
from final_parser import generate_recommendations

def test_recommendations():
    """Тестирует систему рекомендаций с различными профилями"""

    # Загружаем данные
    try:
        with open('parsed_programs.json', 'r', encoding='utf-8') as f:
            programs_data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл parsed_programs.json не найден. Запустите сначала парсер.")
        return

    # Находим программу с curriculum
    program_with_curriculum = None
    for prog_name, prog_data in programs_data.items():
        if 'curriculum' in prog_data and prog_data['curriculum'].get('all_courses'):
            program_with_curriculum = prog_data
            print(f"✅ Используем программу: {prog_name}")
            break

    if not program_with_curriculum:
        print("❌ Не найдена программа с учебным планом")
        return

    # Тестовые профили
    test_profiles = [
        {
            'name': 'Fullstack разработчик из Яндекса',
            'description': 'Я фуллстек из Яндекса, опыт 2 года, очень много знаю про компьютеры и их устройство. Умею писать сервисы и фронтенд, инфраструктуру'
        },
        {
            'name': 'ML Engineer',
            'description': 'Работаю ML engineer в стартапе, занимаюсь машинным обучением и нейронными сетями'
        },
        {
            'name': 'Data Scientist',
            'description': 'Data scientist с опытом анализа данных и статистики'
        },
        {
            'name': 'Product Manager',
            'description': 'Product manager, хочу изучить AI для создания продуктов'
        },
        {
            'name': 'Неопределенный профиль',
            'description': 'Просто интересуюсь технологиями'
        }
    ]

    print(f"\n🧪 Тестирование системы рекомендаций")
    print(f"📊 Всего дисциплин в программе: {len(program_with_curriculum['curriculum']['all_courses'])}")
    print(f"📚 Выборных дисциплин: {len(program_with_curriculum['curriculum']['elective_courses'])}")
    print("=" * 80)

    for profile in test_profiles:
        print(f"\n👤 **Тестируем профиль: {profile['name']}**")
        print(f"📝 Описание: {profile['description']}")
        print("-" * 60)

        try:
            recommendations = generate_recommendations(
                profile['description'],
                program_with_curriculum['curriculum']
            )

            print(f"🎯 **Определенный профиль:** {recommendations.get('user_profile', 'Не определен')}")

            matched_keywords = recommendations.get('matched_keywords', [])
            if matched_keywords:
                print(f"🔍 **Найденные ключевые слова:** {', '.join(matched_keywords[:8])}")

            print(f"\n📚 **Рекомендуемые дисциплины (топ-5):**")
            for i, rec in enumerate(recommendations.get('recommendations', [])[:5], 1):
                priority_icon = "⭐" if rec.get('priority', 0) >= 3 else "📖"
                print(f"{i}. {priority_icon} **{rec['name']}** ({rec['credits']} кредитов)")
                print(f"   📂 Категория: {rec['category']}")
                print(f"   💡 {rec['reason']}")
                print()

            # Анализ
            analysis = recommendations.get('analysis', {})
            if analysis:
                print(f"📊 **Анализ:** {analysis.get('categories_found', 0)} категорий найдено")

            # Распределение по категориям
            cat_dist = recommendations.get('category_distribution', {})
            if cat_dist:
                sorted_categories = sorted(cat_dist.items(), key=lambda x: x[1], reverse=True)
                top_categories = [f"{cat}: {count}" for cat, count in sorted_categories[:4] if count > 0]
                if top_categories:
                    print(f"🏆 **Топ категории:** {' • '.join(top_categories)}")

        except Exception as e:
            print(f"❌ Ошибка при генерации рекомендаций: {e}")

        print("=" * 80)

if __name__ == "__main__":
    test_recommendations()