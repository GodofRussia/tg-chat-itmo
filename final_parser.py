#!/usr/bin/env python3
"""
Финальный универсальный парсер для программ магистратуры
Поддерживает любые URL-ы и парсинг PDF с учебными планами
Скачивает и обрабатывает PDF файлы в памяти без сохранения на диск
"""

import re
import json
import sys
import io
import tempfile
from typing import Dict, List, Any, Optional

def extract_curriculum_data(text: str) -> Dict[str, Any]:
    """
    Извлекает данные о дисциплинах из текста учебного плана
    """
    curriculum = {
        "program_name": "",
        "semesters": {},
        "elective_courses": [],
        "mandatory_courses": [],
        "all_courses": []
    }

    # Извлекаем название программы
    program_match = re.search(r'ОП\s+(.+?)(?:Семестры|$)', text)
    if program_match:
        curriculum["program_name"] = program_match.group(1).strip()

    # Парсим дисциплины по семестрам
    lines = text.split('\n')
    current_semester = None
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Определяем семестр
        semester_match = re.search(r'(\d+)\s*семестр', line)
        if semester_match:
            current_semester = int(semester_match.group(1))
            if current_semester not in curriculum["semesters"]:
                curriculum["semesters"][current_semester] = {
                    "mandatory": [],
                    "elective": []
                }
            continue

        # Определяем тип дисциплин
        if "Обязательные дисциплины" in line:
            current_section = "mandatory"
            continue
        elif "Пул выборных дисциплин" in line or "выборных" in line.lower():
            current_section = "elective"
            continue

        # Парсим дисциплину - исправленное регулярное выражение
        # Формат: номер_семестра + название + число (кредиты+часы слитно)
        course_match = re.match(r'^(\d+)(.+?)\s+(\d+)\s*$', line)
        if course_match:
            semester_num = int(course_match.group(1))
            course_name = course_match.group(2).strip()
            combined_number = course_match.group(3)

            # Разделяем кредиты и часы
            # Обычно первая цифра - кредиты, остальные - часы
            if len(combined_number) >= 4:
                credits = int(combined_number[0])  # Первая цифра
                hours = int(combined_number[1:])   # Остальные цифры
            else:
                credits = int(combined_number)
                hours = 0

            # Определяем тип дисциплины
            if current_section is None:
                # Если секция не определена, определяем по контексту
                if any(keyword in course_name.lower() for keyword in ['обязательн', 'воркшоп']):
                    section_type = "mandatory"
                else:
                    section_type = "elective"
            else:
                section_type = current_section

            course_info = {
                "name": course_name,
                "credits": credits,
                "hours": hours,
                "semester": semester_num,
                "type": section_type
            }

            # Инициализируем семестр если нужно
            if semester_num not in curriculum["semesters"]:
                curriculum["semesters"][semester_num] = {
                    "mandatory": [],
                    "elective": []
                }

            # Добавляем в соответствующие списки
            if section_type == "mandatory":
                curriculum["semesters"][semester_num]["mandatory"].append(course_info)
                curriculum["mandatory_courses"].append(course_info)
            else:
                curriculum["semesters"][semester_num]["elective"].append(course_info)
                curriculum["elective_courses"].append(course_info)

            curriculum["all_courses"].append(course_info)

    return curriculum

def categorize_subjects(curriculum: Dict) -> Dict[str, List[Dict]]:
    """Категоризирует предметы по областям"""
    categories = {
        'machine_learning': {
            'keywords': ['машинное обучение', 'machine learning', 'ml', 'глубокое обучение',
                       'deep learning', 'нейронные сети', 'neural networks', 'автоматическое'],
            'description': 'Машинное обучение и ИИ'
        },
        'programming': {
            'keywords': ['программирование', 'python', 'c++', 'разработка', 'веб-приложений',
                       'микросервисов', 'backend', 'языки программирования'],
            'description': 'Программирование и разработка'
        },
        'computer_vision': {
            'keywords': ['компьютерное зрение', 'computer vision', 'изображений', 'обработка изображений',
                       'генерация изображений', 'мультимодальные'],
            'description': 'Компьютерное зрение'
        },
        'nlp': {
            'keywords': ['естественного языка', 'nlp', 'обработка текстов', 'языковые модели',
                       'llm', 'генеративные модели', 'разговорного'],
            'description': 'Обработка естественного языка'
        },
        'data_science': {
            'keywords': ['данные', 'data', 'статистика', 'анализ', 'визуализация',
                       'временные ряды', 'big data', 'больших данных'],
            'description': 'Наука о данных'
        },
        'systems': {
            'keywords': ['системы', 'mlops', 'devops', 'контейнеризация', 'gpu', 'unix',
                       'базы данных', 'инфраструктура', 'архитектура'],
            'description': 'Системы и инфраструктура'
        },
        'product': {
            'keywords': ['продукт', 'product', 'бизнес', 'управление', 'проект',
                       'аналитика', 'дизайн', 'прототипирование'],
            'description': 'Продуктовое управление'
        }
    }

    categorized = {category: [] for category in categories.keys()}
    categorized['other'] = []

    all_courses = curriculum.get('all_courses', [])

    for course in all_courses:
        course_name = course['name'].lower()
        assigned = False

        for category, category_data in categories.items():
            if any(keyword in course_name for keyword in category_data['keywords']):
                categorized[category].append(course)
                assigned = True
                break

        if not assigned:
            categorized['other'].append(course)

    return categorized

def generate_recommendations(background_text: str, curriculum: Dict) -> Dict:
    """Генерирует рекомендации на основе профиля пользователя с улучшенным распознаванием"""

    # Расширенные профили пользователей с синонимами
    user_profiles = {
        'fullstack_developer': {
            'keywords': [
                # Основные термины
                'фуллстек', 'fullstack', 'full-stack', 'full stack',
                'разработчик', 'программист', 'developer', 'programmer',
                'фронтенд', 'frontend', 'front-end', 'бэкенд', 'backend', 'back-end',
                'сервисы', 'services', 'веб', 'web', 'приложения', 'applications',
                'инфраструктура', 'infrastructure', 'devops',
                # Технологии
                'python', 'javascript', 'react', 'node', 'django', 'flask',
                'api', 'rest', 'микросервисы', 'microservices',
                # Опыт работы
                'яндекс', 'yandex', 'опыт', 'experience', 'работаю', 'работал'
            ],
            'preferences': ['programming', 'systems', 'machine_learning'],
            'description': 'Fullstack разработчик'
        },
        'ml_engineer': {
            'keywords': [
                'ml engineer', 'машинное обучение', 'machine learning', 'ml',
                'модели', 'models', 'алгоритмы', 'algorithms', 'нейронные сети',
                'deep learning', 'глубокое обучение', 'tensorflow', 'pytorch',
                'sklearn', 'data science', 'ai', 'artificial intelligence',
                'kaggle', 'соревнования', 'competitions'
            ],
            'preferences': ['machine_learning', 'programming', 'systems'],
            'description': 'ML Engineer'
        },
        'data_scientist': {
            'keywords': [
                'data scientist', 'данные', 'data', 'аналитик', 'analyst',
                'статистика', 'statistics', 'анализ данных', 'data analysis',
                'pandas', 'numpy', 'jupyter', 'visualization', 'визуализация',
                'bi', 'business intelligence', 'дашборды', 'dashboards'
            ],
            'preferences': ['data_science', 'machine_learning', 'programming'],
            'description': 'Data Scientist'
        },
        'cv_specialist': {
            'keywords': [
                'computer vision', 'компьютерное зрение', 'cv', 'изображения',
                'images', 'opencv', 'обработка изображений', 'image processing',
                'распознавание', 'recognition', 'детекция', 'detection',
                'сегментация', 'segmentation', 'yolo', 'cnn'
            ],
            'preferences': ['computer_vision', 'machine_learning', 'programming'],
            'description': 'Computer Vision специалист'
        },
        'nlp_specialist': {
            'keywords': [
                'nlp', 'natural language processing', 'естественный язык',
                'обработка языка', 'текст', 'text', 'языковые модели',
                'language models', 'llm', 'bert', 'gpt', 'transformers',
                'чатботы', 'chatbots', 'sentiment', 'тональность'
            ],
            'preferences': ['nlp', 'machine_learning', 'programming'],
            'description': 'NLP специалист'
        },
        'product_manager': {
            'keywords': [
                'product manager', 'продукт', 'product', 'менеджер', 'manager',
                'управление', 'management', 'бизнес', 'business', 'стратегия',
                'strategy', 'roadmap', 'планирование', 'planning', 'продуктовый',
                'аналитика', 'analytics', 'метрики', 'metrics', 'a/b тесты'
            ],
            'preferences': ['product', 'data_science', 'machine_learning'],
            'description': 'Product Manager'
        },
        'systems_architect': {
            'keywords': [
                'архитектор', 'architect', 'системы', 'systems', 'архитектура',
                'architecture', 'высоконагруженные', 'highload', 'high-load',
                'масштабирование', 'scaling', 'производительность', 'performance',
                'инфраструктура', 'infrastructure', 'облако', 'cloud',
                'kubernetes', 'docker', 'микросервисы'
            ],
            'preferences': ['systems', 'programming', 'machine_learning'],
            'description': 'Системный архитектор'
        },
        'backend_developer': {
            'keywords': [
                'backend', 'бэкенд', 'серверная разработка', 'server-side',
                'api', 'rest', 'graphql', 'базы данных', 'databases',
                'postgresql', 'mysql', 'mongodb', 'redis',
                'java', 'go', 'c#', 'node.js', 'spring'
            ],
            'preferences': ['programming', 'systems', 'data_science'],
            'description': 'Backend разработчик'
        },
        'frontend_developer': {
            'keywords': [
                'frontend', 'фронтенд', 'клиентская разработка', 'client-side',
                'react', 'vue', 'angular', 'javascript', 'typescript',
                'html', 'css', 'ui', 'ux', 'интерфейсы', 'interfaces'
            ],
            'preferences': ['programming', 'product', 'machine_learning'],
            'description': 'Frontend разработчик'
        },
        'mobile_developer': {
            'keywords': [
                'mobile', 'мобильная разработка', 'android', 'ios',
                'react native', 'flutter', 'swift', 'kotlin',
                'приложения', 'apps', 'мобильные приложения'
            ],
            'preferences': ['programming', 'product', 'systems'],
            'description': 'Mobile разработчик'
        },
        'devops_engineer': {
            'keywords': [
                'devops', 'деплой', 'deployment', 'ci/cd', 'jenkins',
                'gitlab', 'github actions', 'terraform', 'ansible',
                'мониторинг', 'monitoring', 'логирование', 'logging'
            ],
            'preferences': ['systems', 'programming', 'machine_learning'],
            'description': 'DevOps Engineer'
        },
        'qa_engineer': {
            'keywords': [
                'qa', 'тестирование', 'testing', 'автотесты', 'automation',
                'selenium', 'pytest', 'качество', 'quality assurance',
                'баги', 'bugs', 'тест-кейсы', 'test cases'
            ],
            'preferences': ['programming', 'systems', 'product'],
            'description': 'QA Engineer'
        },
        'business_analyst': {
            'keywords': [
                'business analyst', 'бизнес-аналитик', 'аналитик',
                'требования', 'requirements', 'процессы', 'processes',
                'документация', 'documentation', 'stakeholders'
            ],
            'preferences': ['product', 'data_science', 'programming'],
            'description': 'Бизнес-аналитик'
        },
        'researcher': {
            'keywords': [
                'исследователь', 'researcher', 'наука', 'science',
                'исследования', 'research', 'публикации', 'papers',
                'эксперименты', 'experiments', 'phd', 'кандидат наук'
            ],
            'preferences': ['machine_learning', 'data_science', 'programming'],
            'description': 'Исследователь'
        },
        'student': {
            'keywords': [
                'студент', 'student', 'учусь', 'studying', 'университет',
                'вуз', 'институт', 'курсовые', 'дипломная', 'thesis',
                'бакалавр', 'bachelor', 'магистр', 'master'
            ],
            'preferences': ['machine_learning', 'programming', 'data_science'],
            'description': 'Студент'
        }
    }

    # Улучшенное определение профиля пользователя
    background_lower = background_text.lower()
    profile_scores = {}

    for profile_name, profile_data in user_profiles.items():
        score = 0
        matched_keywords = []

        for keyword in profile_data['keywords']:
            if keyword in background_lower:
                score += 1
                matched_keywords.append(keyword)

        # Бонус за количество совпадений
        if score > 0:
            score = score * (1 + len(matched_keywords) * 0.1)

        profile_scores[profile_name] = {
            'score': score,
            'matched_keywords': matched_keywords
        }

    # Находим доминирующий профиль
    best_profile = None
    best_score = 0

    for profile_name, data in profile_scores.items():
        if data['score'] > best_score:
            best_score = data['score']
            best_profile = profile_name

    if best_profile and best_score > 0:
        dominant_profile = best_profile
        preferences = user_profiles[dominant_profile]['preferences']
        profile_description = user_profiles[dominant_profile]['description']
    else:
        # Если профиль не определен, анализируем текст на предмет общих паттернов
        if any(word in background_lower for word in ['программист', 'разработчик', 'developer', 'код', 'code']):
            dominant_profile = 'general_developer'
            preferences = ['programming', 'systems', 'machine_learning']
            profile_description = 'Разработчик (общий профиль)'
        else:
            dominant_profile = None
            preferences = ['machine_learning', 'programming', 'data_science']
            profile_description = 'Не определен'

    # Категоризируем предметы
    categorized = categorize_subjects(curriculum)

    # Генерируем рекомендации с улучшенной логикой
    recommendations = []

    # Добавляем рекомендации по приоритетным категориям
    for i, category in enumerate(preferences):
        subjects = categorized.get(category, [])
        elective_subjects = [s for s in subjects if s.get('type') == 'elective']

        # Сортируем по кредитам (больше кредитов = важнее)
        elective_subjects.sort(key=lambda x: x.get('credits', 0), reverse=True)

        # Берем топ предметы из каждой категории
        limit = max(1, 4 - i)  # Первая категория - 4 предмета, вторая - 3, третья - 2
        for subject in elective_subjects[:limit]:
            reason = f"Рекомендовано для {profile_description}" if dominant_profile else "Базовая рекомендация"
            if i == 0:
                reason += " (приоритетная область)"

            recommendations.append({
                **subject,
                'category': category,
                'reason': reason,
                'priority': len(preferences) - i  # Приоритет от 3 до 1
            })

    # Сортируем рекомендации по приоритету и кредитам
    recommendations.sort(key=lambda x: (x.get('priority', 0), x.get('credits', 0)), reverse=True)

    return {
        'user_profile': profile_description,
        'dominant_profile_key': dominant_profile,
        'profile_scores': {k: v['score'] for k, v in profile_scores.items()},
        'matched_keywords': profile_scores.get(best_profile, {}).get('matched_keywords', []) if best_profile else [],
        'recommendations': recommendations[:10],  # Топ-10
        'category_distribution': {cat: len(subjects) for cat, subjects in categorized.items()},
        'analysis': {
            'total_courses': len(curriculum.get('all_courses', [])),
            'elective_courses': len(curriculum.get('elective_courses', [])),
            'categories_found': len([cat for cat, subjects in categorized.items() if subjects])
        }
    }

def get_profile_examples() -> str:
    """Возвращает примеры описания профилей для пользователей"""

    examples = {
        '👨‍💻 Разработчики': [
            'Fullstack разработчик из Яндекса, опыт 3 года, знаю Python, React, работаю с микросервисами',
            'Backend разработчик на Java, работаю в банке, опыт с Spring Boot и PostgreSQL',
            'Frontend разработчик, делаю интерфейсы на React и Vue, интересуюсь UX',
            'Mobile разработчик iOS, пишу на Swift, хочу изучить ML для мобильных приложений'
        ],
        '🤖 ML/AI специалисты': [
            'ML Engineer в стартапе, занимаюсь обучением моделей, знаю TensorFlow и PyTorch',
            'Data Scientist, анализирую данные в e-commerce, работаю с pandas и sklearn',
            'Computer Vision специалист, делаю системы распознавания, опыт с OpenCV',
            'NLP инженер, создаю чатботы и анализирую тексты, работал с BERT и GPT'
        ],
        '📊 Аналитики и менеджеры': [
            'Product Manager в IT, управляю продуктом, хочу понимать AI для принятия решений',
            'Бизнес-аналитик, работаю с требованиями, интересуюсь data science',
            'Аналитик данных, строю дашборды в Tableau, хочу изучить машинное обучение'
        ],
        '🔧 Инфраструктура и системы': [
            'DevOps инженер, настраиваю CI/CD, работаю с Kubernetes и Docker',
            'Системный архитектор, проектирую высоконагруженные системы',
            'QA Engineer, автоматизирую тестирование, хочу изучить ML для тестов'
        ],
        '🎓 Студенты и исследователи': [
            'Студент 4 курса по информатике, пишу дипломную по машинному обучению',
            'Исследователь в области AI, публикуюсь в конференциях, интересуют новые методы',
            'Магистрант по математике, хочу применить знания в data science'
        ]
    }

    result = "📝 **Примеры описания профиля:**\n\n"

    for category, profiles in examples.items():
        result += f"**{category}:**\n"
        for profile in profiles:
            result += f"• `{profile}`\n"
        result += "\n"

    result += "💡 **Что указывать:**\n"
    result += "• Текущую профессию/должность\n"
    result += "• Опыт работы (в годах)\n"
    result += "• Технологии и инструменты\n"
    result += "• Компанию или сферу деятельности\n"
    result += "• Интересы и цели обучения\n"
    result += "• Проекты или достижения\n\n"

    result += "🎯 **Система распознает 15+ профилей:**\n"
    result += "Fullstack, Backend, Frontend, Mobile, ML Engineer, Data Scientist, "
    result += "Computer Vision, NLP, Product Manager, DevOps, QA, Business Analyst, "
    result += "Systems Architect, Researcher, Student"

    return result

def download_and_parse_pdf(pdf_url: str) -> Optional[Dict[str, Any]]:
    """
    Скачивает PDF файл в память и извлекает из него данные о курсах
    Работает полностью в памяти, не сохраняет файлы на диск
    """
    try:
        import requests

        print(f"📥 Загружаю PDF из API: {pdf_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,*/*'
        }

        response = requests.get(pdf_url, headers=headers, timeout=60)
        response.raise_for_status()

        print(f"✅ PDF загружен: {len(response.content)} байт")

        # Создаем временный файл в памяти (не на диске!)
        pdf_content = io.BytesIO(response.content)

        try:
            import PyPDF2

            # Читаем PDF из памяти
            pdf_reader = PyPDF2.PdfReader(pdf_content)

            # Извлекаем текст из всех страниц
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"

            print(f"📄 Извлечено {len(full_text)} символов из {len(pdf_reader.pages)} страниц")

            # Парсим учебный план
            curriculum = extract_curriculum_data(full_text)

            # Очищаем память
            pdf_content.close()
            del pdf_content
            del response

            print(f"🎓 Обработано: {len(curriculum['all_courses'])} дисциплин")

            return {
                "curriculum": curriculum,
                "pdf_text_length": len(full_text),
                "pdf_pages": len(pdf_reader.pages)
            }

        except ImportError:
            print("❌ Для работы с PDF установите: pip install PyPDF2")
            return None
        except Exception as e:
            print(f"❌ Ошибка при парсинге PDF: {e}")
            return None

    except Exception as e:
        print(f"❌ Ошибка при скачивании PDF {pdf_url}: {e}")
        return None

def extract_js_urls_and_analyze(html_content: str, base_url: str) -> List[str]:
    """
    Извлекает все JavaScript файлы со страницы и анализирует их на предмет API endpoints
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import requests

    soup = BeautifulSoup(html_content, "html.parser")
    js_urls = []

    # Находим все script теги с src
    for script in soup.find_all("script", src=True):
        src = script.get("src")
        if src:
            if src.startswith("http"):
                js_urls.append(src)
            else:
                js_urls.append(urljoin(base_url, src))

    return js_urls

def analyze_js_for_api_endpoints(js_content: str) -> List[str]:
    """
    Анализирует JavaScript код на предмет API endpoints
    """
    endpoints = []

    # Ищем различные паттерны API endpoints
    patterns = [
        r'["\']([^"\']*api[^"\']*)["\']',  # Общие API пути
        r'["\']([^"\']*plans?[^"\']*\.pdf)["\']',  # PDF планы
        r'["\']([^"\']*curriculum[^"\']*\.pdf)["\']',  # Curriculum PDF
        r'["\']([^"\']*study[^"\']*plan[^"\']*\.pdf)["\']',  # Study plan PDF
        r'baseURL:\s*["\']([^"\']+)["\']',  # Base URL
        r'["\']([^"\']*file_storage[^"\']*)["\']',  # File storage paths
        r'/api/v\d+/[^"\']*',  # API версии
        r'https://abitlk\.itmo\.ru/api/[^"\']*',  # Прямые API ссылки
    ]

    for pattern in patterns:
        matches = re.findall(pattern, js_content, re.IGNORECASE)
        endpoints.extend(matches)

    return list(set(endpoints))  # Убираем дубликаты

def find_study_plan_via_api(base_url: str, program_slug: str = "ai") -> Optional[str]:
    """
    Универсальная функция для поиска учебного плана через API endpoints
    Работает с любыми программами ИТМО (ai, ai_product, highload_systems, etc.)
    """
    import requests

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Accept-Language': 'ru'
    }

    # Универсальный API endpoint для всех программ магистратуры
    api_endpoint = f"https://abitlk.itmo.ru/api/v1/programs/master/{program_slug}"

    try:
        print(f"🌐 Запрашиваем данные с API: {api_endpoint}")
        response = requests.get(api_endpoint, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Успешный ответ от API: {len(str(data))} символов")

            # Ищем academic_plan в результате
            if data.get('ok') and 'result' in data and 'academic_plan' in data['result']:
                pdf_url = data['result']['academic_plan']
                print(f"📋 Найден academic_plan: {pdf_url}")
                return pdf_url

            # Дополнительный поиск PDF ссылок в JSON для любых программ
            json_str = json.dumps(data, ensure_ascii=False)
            pdf_matches = re.findall(r'https?://[^\s"\']*\.pdf[^\s"\']*', json_str)
            if pdf_matches:
                # Фильтруем PDF, исключая экзамены
                for pdf_url in pdf_matches:
                    if 'plan' in pdf_url.lower() or 'curriculum' in pdf_url.lower():
                        print(f"📄 Найден PDF учебного плана: {pdf_url}")
                        return pdf_url

                # Если не нашли специфичные, берем первый (но не экзамены)
                for pdf_url in pdf_matches:
                    if 'exam' not in pdf_url.lower():
                        print(f"📄 Найден PDF (общий): {pdf_url}")
                        return pdf_url

        else:
            print(f"❌ API вернул ошибку: {response.status_code}")

    except Exception as e:
        print(f"❌ Ошибка при обращении к API: {e}")

    return None

def find_study_plan_url_advanced(html_content: str, base_url: str) -> Optional[str]:
    """
    Продвинутый поиск ссылки на учебный план с использованием различных методов
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import requests

    soup = BeautifulSoup(html_content, "html.parser")

    # Извлекаем slug программы из URL
    program_slug = "ai"  # по умолчанию
    if "/program/master/" in base_url:
        program_slug = base_url.split("/program/master/")[-1].split("/")[0]

    print(f"Определен slug программы: {program_slug}")

    # Метод 1: Поиск через API endpoints
    print("=== Метод 1: Поиск через API ===")
    api_result = find_study_plan_via_api(base_url, program_slug)
    if api_result:
        return api_result

    # Метод 2: Анализ JavaScript файлов
    print("=== Метод 2: Анализ JavaScript файлов ===")
    js_urls = extract_js_urls_and_analyze(html_content, base_url)
    print(f"Найдено {len(js_urls)} JavaScript файлов")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for js_url in js_urls[:10]:  # Анализируем первые 10 JS файлов
        try:
            print(f"Анализируем JS: {js_url}")
            js_response = requests.get(js_url, headers=headers, timeout=15)
            if js_response.status_code == 200:
                endpoints = analyze_js_for_api_endpoints(js_response.text)
                print(f"Найдено {len(endpoints)} потенциальных endpoints")

                for endpoint in endpoints:
                    if endpoint.endswith('.pdf') and any(keyword in endpoint.lower() for keyword in ["plan", "curriculum", "study"]):
                        if endpoint.startswith('http'):
                            return endpoint
                        else:
                            return urljoin(base_url, endpoint)

        except Exception as e:
            print(f"Ошибка при анализе JS {js_url}: {e}")
            continue

    # Метод 3: Поиск по известным паттернам ИТМО (оригинальный код)
    print("=== Метод 3: Стандартные паттерны ===")
    program_codes = [program_slug]

    # Из HTML контента
    title_elem = soup.find("h1")
    if title_elem:
        title = title_elem.get_text().lower()
        if "искусственный интеллект" in title and "продукт" not in title:
            program_codes.append("ai")
        elif "продукт" in title and "искусственный" in title:
            program_codes.append("ai_product")

    # Пробуем стандартные URL-ы для учебных планов ИТМО
    base_plan_url = "https://abit.itmo.ru/file_storage/file/plans/master/"
    for code in program_codes:
        potential_urls = [
            f"{base_plan_url}{code}.pdf",
            f"{base_plan_url}{code}_plan.pdf",
            f"{base_plan_url}plan_{code}.pdf"
        ]

        for url in potential_urls:
            try:
                response = requests.head(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    print(f"Найден учебный план по стандартному URL: {url}")
                    return url
            except:
                continue

    return None

def parse_from_urls(urls: List[str]) -> Dict[str, Any]:
    """
    Универсальная функция для парсинга программ с любых URL-ов
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        def fetch_webpage(url: str) -> Optional[str]:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
            except Exception as e:
                print(f"Ошибка при загрузке {url}: {e}")
                return None

        def parse_program_page(html_content: str, base_url: str = "") -> Dict[str, Any]:
            soup = BeautifulSoup(html_content, "html.parser")
            result = {}

            # Название программы
            title = soup.find("h1")
            result["title"] = title.text.strip() if title else ""

            # Описание
            result["description"] = ""
            desc_selectors = [
                'span[class*="AboutProgram_aboutProgram__lead"]',
                'span[class*="AboutProgram_aboutProgram__description"]'
            ]

            for selector in desc_selectors:
                desc_block = soup.select_one(selector)
                if desc_block:
                    result["description"] = desc_block.get_text(separator=" ", strip=True)
                    break

            # FAQ
            result["faq"] = []
            for item in soup.select(".Accordion_accordion__item__A6W5t"):
                question_elem = item.select_one("h5")
                answer_elem = item.select_one("div[class*='info']")

                if question_elem and answer_elem:
                    result["faq"].append({
                        "question": question_elem.get_text(strip=True),
                        "answer": answer_elem.get_text(" ", strip=True)
                    })

            # Поиск ссылки на учебный план - улучшенная версия
            result["study_plan_url"] = ""

            # Метод 1: Поиск прямых ссылок на PDF
            for link in soup.find_all("a", href=True):
                href = link.get("href")
                link_text = link.get_text().lower()

                if ("план" in link_text or "curriculum" in link_text) and href.endswith(".pdf"):
                    if href.startswith("http"):
                        result["study_plan_url"] = href
                    elif base_url:
                        result["study_plan_url"] = urljoin(base_url, href)
                    break

            # Метод 2: Поиск в JavaScript коде страницы
            if not result["study_plan_url"]:
                script_tags = soup.find_all("script")
                for script in script_tags:
                    if script.string:
                        script_content = script.string
                        # Ищем PDF ссылки в JavaScript
                        pdf_matches = re.findall(r'["\']([^"\']*\.pdf)["\']', script_content)
                        for pdf_url in pdf_matches:
                            if "plan" in pdf_url.lower() or "curriculum" in pdf_url.lower():
                                if pdf_url.startswith("http"):
                                    result["study_plan_url"] = pdf_url
                                elif base_url:
                                    result["study_plan_url"] = urljoin(base_url, pdf_url)
                                break
                        if result["study_plan_url"]:
                            break

            # Метод 3: Поиск кнопки "Скачать учебный план" и попытка найти связанную ссылку
            if not result["study_plan_url"]:
                study_plan_buttons = soup.find_all("button", string=re.compile(r"скачать.*план", re.IGNORECASE))
                for button in study_plan_buttons:
                    # Ищем родительский элемент с ссылкой
                    parent = button.parent
                    while parent and parent.name != "body":
                        if parent.name == "a" and parent.get("href"):
                            href = parent.get("href")
                            if href.endswith(".pdf"):
                                if href.startswith("http"):
                                    result["study_plan_url"] = href
                                elif base_url:
                                    result["study_plan_url"] = urljoin(base_url, href)
                                break
                        parent = parent.parent
                    if result["study_plan_url"]:
                        break

            # Метод 4: Поиск по data-атрибутам
            if not result["study_plan_url"]:
                elements_with_data = soup.find_all(attrs={"data-url": True})
                for element in elements_with_data:
                    data_url = element.get("data-url")
                    if data_url and data_url.endswith(".pdf"):
                        if "plan" in data_url.lower() or "curriculum" in data_url.lower():
                            if data_url.startswith("http"):
                                result["study_plan_url"] = data_url
                            elif base_url:
                                result["study_plan_url"] = urljoin(base_url, data_url)
                            break

            # Метод 5: Поиск всех PDF ссылок в HTML и выбор наиболее подходящей
            if not result["study_plan_url"]:
                all_pdf_links = []
                # Ищем все ссылки на PDF
                for element in soup.find_all(href=re.compile(r'.*\.pdf$')):
                    href = element.get("href")
                    if href:
                        if href.startswith("http"):
                            all_pdf_links.append(href)
                        elif base_url:
                            all_pdf_links.append(urljoin(base_url, href))

                # Также ищем PDF ссылки в тексте
                html_text = str(soup)
                pdf_matches = re.findall(r'https?://[^\s<>"]+\.pdf', html_text)
                all_pdf_links.extend(pdf_matches)

                # Выбираем наиболее подходящую ссылку
                for pdf_link in all_pdf_links:
                    if any(keyword in pdf_link.lower() for keyword in ["plan", "curriculum", "учебный", "образовательная"]):
                        result["study_plan_url"] = pdf_link
                        break

                # Если не нашли по ключевым словам, берем первую PDF ссылку
                if not result["study_plan_url"] and all_pdf_links:
                    result["study_plan_url"] = all_pdf_links[0]

            return result

        programs = {}

        for url in urls:
            print(f"\n=== Парсинг программы с URL: {url} ===")
            html_content = fetch_webpage(url)

            if html_content:
                try:
                    program_data = parse_program_page(html_content, url)
                    program_name = program_data.get("title", f"Программа_{len(programs)+1}")

                    programs[program_name] = program_data
                    programs[program_name]["source_url"] = url

                    print(f"Успешно спарсена программа: {program_name}")

                    # Игнорируем PDF с экзаменами из HTML, сразу ищем через API
                    study_plan_url = program_data.get("study_plan_url")
                    if study_plan_url and "exams" in study_plan_url:
                        print(f"⚠️ Найден PDF с экзаменами, игнорируем: {study_plan_url}")
                        study_plan_url = None

                    # Ищем настоящий учебный план через API
                    if not study_plan_url:
                        print("🔍 Ищем учебный план через API...")
                        study_plan_url = find_study_plan_url_advanced(html_content, url)
                        if study_plan_url:
                            programs[program_name]["study_plan_url"] = study_plan_url

                    # Если есть ссылка на учебный план, скачиваем и парсим PDF
                    if study_plan_url:
                        print(f"📥 Найдена ссылка на учебный план: {study_plan_url}")
                        pdf_data = download_and_parse_pdf(study_plan_url)
                        if pdf_data and pdf_data["curriculum"]["all_courses"]:
                            programs[program_name]["curriculum"] = pdf_data["curriculum"]
                            programs[program_name]["pdf_info"] = {
                                "text_length": pdf_data["pdf_text_length"],
                                "pages": pdf_data["pdf_pages"]
                            }
                            print(f"✅ Успешно загружен и обработан учебный план: {len(pdf_data['curriculum']['all_courses'])} дисциплин")
                        else:
                            print("❌ Не удалось загрузить или обработать PDF")
                    else:
                        print("❌ Ссылка на учебный план не найдена")

                except Exception as e:
                    print(f"Ошибка при парсинге {url}: {e}")
                    programs[f"Ошибка_{len(programs)+1}"] = {
                        "title": f"Ошибка парсинга",
                        "error": str(e),
                        "source_url": url
                    }
            else:
                print(f"Не удалось загрузить данные с {url}")

        return programs

    except ImportError:
        print("Для работы с URL-ами установите: pip install requests beautifulsoup4")
        return {}

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python final_parser.py <url1> [url2] [url3] ...")
        return

    # Режим парсинга URL-ов
    urls = sys.argv[1:]
    print(f"Парсинг {len(urls)} URL-ов...")

    programs = parse_from_urls(urls)

    # Сохраняем результат
    output_file = "parsed_programs.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(programs, f, indent=2, ensure_ascii=False)

    print(f"\nРезультаты сохранены в {output_file}")

    # Выводим статистику
    for program_name, data in programs.items():
        if "error" in data:
            print(f"❌ {program_name}: {data['error']}")
        else:
            faq_count = len(data.get('faq', []))
            print(f"✅ {program_name}: {faq_count} FAQ")

if __name__ == "__main__":
    main()

