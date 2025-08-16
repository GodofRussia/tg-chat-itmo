import json
import logging
import re
from typing import Dict, List, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import difflib
from dataclasses import dataclass
from final_parser import generate_recommendations, categorize_subjects, get_profile_examples

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    """Профиль пользователя для персонализации рекомендаций"""
    background: str = ""  # Бэкграунд пользователя
    interests: List[str] = None  # Интересы
    experience_level: str = ""  # Уровень опыта
    preferred_program: str = ""  # Предпочитаемая программа

    def __post_init__(self):
        if self.interests is None:
            self.interests = []

class ITMOChatBot:
    def __init__(self, token: str, data_file: str = "parsed_programs.json"):
        self.token = token
        self.data_file = data_file
        self.programs_data = self.load_programs_data()
        self.user_profiles: Dict[int, UserProfile] = {}

        # Расширенные ключевые слова для фильтрации релевантных вопросов
        self.relevant_keywords = {
            # Поступление и обучение
            'поступление', 'поступить', 'экзамен', 'экзамены', 'магистратура', 'обучение', 'программа', 'программы',
            'диплом', 'стипендия', 'карьера', 'образование', 'учеба', 'учебный', 'план', 'планы',
            'курс', 'курсы', 'предмет', 'предметы', 'дисциплина', 'дисциплины', 'проект', 'практика', 'стажировка',

            # Программы ИТМО
            'искусственный интеллект', 'ии', 'ai', 'машинное обучение', 'ml', 'продукт', 'продуктовый',
            'высоконагруженные', 'системы', 'highload', 'программное обеспечение', 'по',

            # Университет
            'итмо', 'itmo', 'университет', 'вуз', 'институт',

            # Общие вопросы об обучении
            'содержание', 'содержании', 'что изучают', 'что изучается', 'чему учат', 'чему обучают',
            'количество', 'сколько', 'места', 'мест', 'бюджет', 'бюджетные', 'платные',
            'стоимость', 'цена', 'оплата', 'стоит', 'стоимости',
            'требования', 'условия', 'как поступить', 'документы',
            'длительность', 'срок', 'года', 'лет', 'семестр', 'семестры',
            'преподаватели', 'кафедра', 'факультет', 'направление',
            'выпускники', 'трудоустройство', 'работа', 'карьера'
        }

    def load_programs_data(self) -> Dict[str, Any]:
        """Загружает данные о программах из JSON файла"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Файл {self.data_file} не найден. Запустите сначала: python final_parser.py <urls>")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Ошибка при чтении JSON из {self.data_file}")
            return {}

    def is_relevant_question(self, question: str) -> bool:
        """Проверяет, является ли вопрос релевантным для магистерских программ"""
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in self.relevant_keywords)

    def find_best_answer(self, question: str) -> Optional[Dict[str, str]]:
        """Находит лучший ответ на вопрос пользователя с улучшенным алгоритмом"""
        if not self.is_relevant_question(question):
            return None

        question_lower = question.lower()
        best_match = None
        best_score = 0

        # Извлекаем ключевые слова из вопроса
        question_words = set(question_lower.split())

        for program_name, program_data in self.programs_data.items():
            if 'faq' not in program_data:
                continue

            for faq_item in program_data['faq']:
                faq_question = faq_item['question'].lower()
                faq_answer = faq_item['answer'].lower()
                faq_words = set(faq_question.split())

                # 1. Базовое сходство строк
                similarity = difflib.SequenceMatcher(None, question_lower, faq_question).ratio()

                # 2. Пересечение ключевых слов в вопросах
                common_words = question_words.intersection(faq_words)
                word_overlap = len(common_words) / max(len(question_words), 1)

                # 3. Поиск ключевых слов в ответе (для более широкого поиска)
                answer_matches = sum(1 for word in question_words if word in faq_answer)
                answer_score = answer_matches / max(len(question_words), 1)

                # 4. Специальные бонусы за важные совпадения
                bonus = 0

                # Бонус за точные совпадения важных слов
                important_words = {'содержание', 'программа', 'количество', 'места', 'стоимость', 'поступление', 'экзамен'}
                for word in important_words:
                    if word in question_lower and word in faq_question:
                        bonus += 0.2

                # Бонус за совпадение типа вопроса
                question_types = {
                    'что': ['что', 'какое', 'какая', 'какие'],
                    'сколько': ['сколько', 'количество'],
                    'как': ['как', 'каким образом'],
                    'когда': ['когда', 'срок', 'время']
                }

                for q_type, variants in question_types.items():
                    if any(v in question_lower for v in variants) and any(v in faq_question for v in variants):
                        bonus += 0.15

                # Итоговый скор с весами
                total_score = (
                    similarity * 0.4 +           # Сходство строк
                    word_overlap * 0.3 +         # Пересечение слов в вопросах
                    answer_score * 0.2 +         # Совпадения в ответе
                    bonus                        # Бонусы
                )

                # Понижаем порог для более гибкого поиска
                if total_score > best_score and total_score > 0.2:
                    best_score = total_score
                    best_match = {
                        'question': faq_item['question'],
                        'answer': faq_item['answer'],
                        'program': program_name,
                        'score': total_score,
                        'matched_words': list(common_words)
                    }

        return best_match

    def get_program_comparison(self, user_id: int) -> str:
        """Возвращает персонализированное сравнение программ"""
        if not self.programs_data:
            return "❌ Данные о программах не загружены. Запустите: python final_parser.py <urls>"

        profile = self.user_profiles.get(user_id, UserProfile())

        comparison = f"🔍 **Сравнение программ магистратуры ИТМО:**\n\n"

        programs = list(self.programs_data.items())

        for i, (prog_name, prog_data) in enumerate(programs, 1):
            comparison += f"**{i}. {prog_name}**\n"
            comparison += f"• Описание: {prog_data.get('description', 'Не указано')[:100]}...\n"

            # Показываем количество дисциплин если есть curriculum
            if 'curriculum' in prog_data and prog_data['curriculum'].get('all_courses'):
                total_courses = len(prog_data['curriculum']['all_courses'])
                elective_courses = len(prog_data['curriculum']['elective_courses'])
                comparison += f"• Всего дисциплин: {total_courses} (выборных: {elective_courses})\n"

            comparison += f"• FAQ вопросов: {len(prog_data.get('faq', []))}\n"

            # Персонализированная оценка соответствия
            if profile.background:
                match_score = self.calculate_program_match(profile.background, prog_data)
                comparison += f"• Соответствие вашему профилю: {match_score}%\n"

            comparison += "\n"

        if profile.background:
            comparison += "💡 **Рекомендация основана на вашем профиле**\n"
        else:
            comparison += "💡 Настройте профиль (/profile) для персональных рекомендаций\n"

        return comparison

    def calculate_program_match(self, background: str, program_data: Dict) -> int:
        """Вычисляет соответствие программы профилю пользователя (0-100%)"""
        background_lower = background.lower()
        score = 50  # Базовый балл

        # Анализ по ключевым словам в описании программы
        description = program_data.get('description', '').lower()

        # Бонусы за совпадения
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

    def get_recommendations(self, user_id: int) -> str:
        """Генерирует персонализированные рекомендации на основе реальных данных"""
        profile = self.user_profiles.get(user_id, UserProfile())

        if not profile.background:
            return ("Для получения персонализированных рекомендаций, пожалуйста, "
                   "расскажите о своем бэкграунде с помощью команды /profile")

        recommendations = f"🎯 *Персональные рекомендации для вас:*\n\n"

        # Ищем программу с curriculum для рекомендаций
        program_with_curriculum = None
        for prog_name, prog_data in self.programs_data.items():
            if 'curriculum' in prog_data and prog_data['curriculum'].get('all_courses'):
                program_with_curriculum = prog_data
                break

        if program_with_curriculum:
            # Используем реальную систему рекомендаций из final_parser.py
            try:
                recs = generate_recommendations(profile.background, program_with_curriculum['curriculum'])

                recommendations += f"👤 *Определенный профиль:* {recs.get('user_profile', 'Не определен')}\n"

                # Показываем найденные ключевые слова
                matched_keywords = recs.get('matched_keywords', [])
                if matched_keywords:
                    keywords_text = ', '.join(matched_keywords[:5])
                    recommendations += f"🔍 *Найденные ключевые слова:* {keywords_text}\n"

                recommendations += "\n"

                recommendations += "📚 *Рекомендуемые дисциплины:*\n"
                for i, rec in enumerate(recs.get('recommendations', [])[:8], 1):
                    priority_icon = "⭐" if rec.get('priority', 0) >= 3 else "📖"
                    # Экранируем специальные символы в названии дисциплины
                    course_name = rec['name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
                    recommendations += f"{i}. {priority_icon} *{course_name}* ({rec['credits']} кредитов)\n"
                    recommendations += f"   📂 Категория: {rec['category']}\n"
                    recommendations += f"   💡 {rec['reason']}\n\n"

                # Анализ и статистика
                analysis = recs.get('analysis', {})
                if analysis:
                    recommendations += "📊 *Анализ учебного плана:*\n"
                    recommendations += f"• Всего дисциплин: {analysis.get('total_courses', 0)}\n"
                    recommendations += f"• Выборных дисциплин: {analysis.get('elective_courses', 0)}\n"
                    recommendations += f"• Найдено категорий: {analysis.get('categories_found', 0)}\n\n"

                # Топ категории
                cat_dist = recs.get('category_distribution', {})
                if cat_dist:
                    # Сортируем категории по количеству дисциплин
                    sorted_categories = sorted(cat_dist.items(), key=lambda x: x[1], reverse=True)
                    top_categories = [f"{cat}: {count}" for cat, count in sorted_categories[:5] if count > 0]
                    if top_categories:
                        recommendations += "🏆 *Топ категории дисциплин:*\n"
                        recommendations += f"• {' • '.join(top_categories)}\n"

            except Exception as e:
                logger.error(f"Ошибка при генерации рекомендаций: {e}")
                recommendations += "❌ Ошибка при генерации рекомендаций. Попробуйте позже."
        else:
            recommendations += "❌ Данные о дисциплинах не загружены. Запустите парсер с URL программ."

        return recommendations

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        keyboard = [
            [InlineKeyboardButton("🔍 Сравнить программы", callback_data="compare")],
            [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question")],
            [InlineKeyboardButton("👤 Настроить профиль", callback_data="setup_profile")],
            [InlineKeyboardButton("🎯 Получить рекомендации", callback_data="get_recommendations")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Динамически формируем список программ
        program_names = list(self.programs_data.keys()) if self.programs_data else ["Данные не загружены"]
        programs_text = "\n".join([f"• {name}" for name in program_names])

        welcome_text = (
            "🤖 **Добро пожаловать в универсальный чат-бот ИТМО!**\n\n"
            f"Я помогу вам выбрать между программами магистратуры:\n{programs_text}\n\n"
            "Что вы хотите узнать?"
        )

        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()

        if query.data == "compare":
            comparison = self.get_program_comparison(query.from_user.id)
            await query.edit_message_text(comparison, parse_mode='Markdown')

        elif query.data == "ask_question":
            await query.edit_message_text(
                "❓ **Задайте ваш вопрос о программах магистратуры ИТМО:**\n\n"
                "Например:\n"
                "• Как поступить на программу?\n"
                "• Какие экзамены нужно сдавать?\n"
                "• Сколько стоит обучение?\n"
                "• Какие карьерные возможности?\n\n"
                "Просто напишите ваш вопрос в следующем сообщении.",
                parse_mode='Markdown'
            )

        elif query.data == "setup_profile":
            examples_text = get_profile_examples()
            profile_message = (
                "👤 **Настройка профиля**\n\n"
                "Расскажите о себе, чтобы получить персонализированные рекомендации:\n\n"
                "**Команда:** `/profile ваш_бэкграунд`\n\n"
                f"{examples_text}"
            )
            await query.edit_message_text(profile_message, parse_mode='Markdown')

        elif query.data == "get_recommendations":
            recommendations = self.get_recommendations(query.from_user.id)
            await query.edit_message_text(recommendations, parse_mode='Markdown')

    async def profile_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /profile"""
        user_id = update.effective_user.id

        if not context.args:
            await update.message.reply_text(
                "Пожалуйста, укажите ваш бэкграунд после команды.\n"
                "Например: `/profile Я программист на Python с опытом 3 года`",
                parse_mode='Markdown'
            )
            return

        background = " ".join(context.args)

        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile()

        self.user_profiles[user_id].background = background

        await update.message.reply_text(
            f"✅ **Профиль обновлен!**\n\n"
            f"Ваш бэкграунд: {background}\n\n"
            f"Теперь вы можете получить персонализированные рекомендации с помощью кнопки 'Получить рекомендации' или команды /recommendations",
            parse_mode='Markdown'
        )

    async def recommendations_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /recommendations"""
        recommendations = self.get_recommendations(update.effective_user.id)
        await update.message.reply_text(recommendations, parse_mode='Markdown')

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений (вопросов пользователя)"""
        question = update.message.text

        if not self.is_relevant_question(question):
            await update.message.reply_text(
                "🚫 **Извините, я отвечаю только на вопросы, связанные с магистерскими программами ИТМО.**\n\n"
                "Попробуйте спросить о:\n"
                "• Поступлении и экзаменах\n"
                "• Содержании программ\n"
                "• Карьерных возможностях\n"
                "• Стоимости и стипендиях\n"
                "• Особенностях обучения",
                parse_mode='Markdown'
            )
            return

        answer_data = self.find_best_answer(question)

        if answer_data:
            response = f"💡 **Ответ найден** (программа: {answer_data['program']}):\n\n"
            response += f"**Вопрос:** {answer_data['question']}\n\n"
            response += f"**Ответ:** {answer_data['answer']}\n\n"

            # Показываем совпавшие ключевые слова если есть
            matched_words = answer_data.get('matched_words', [])
            if matched_words:
                response += f"🔍 **Совпавшие слова:** {', '.join(matched_words[:5])}\n"

            response += f"_Релевантность: {answer_data['score']:.2f}_"
        else:
            response = (
                "🤔 **К сожалению, я не нашел точного ответа на ваш вопрос.**\n\n"
                "Попробуйте:\n"
                "• Переформулировать вопрос более конкретно\n"
                "• Использовать ключевые слова: содержание, программа, поступление, количество мест, стоимость\n"
                "• Посмотреть сравнение программ с помощью кнопки 'Сравнить программы'\n"
                "• Получить персональные рекомендации через /profile\n\n"
                "Примеры вопросов:\n"
                "• 'Сколько мест на программе ИИ?'\n"
                "• 'Какая стоимость обучения?'\n"
                "• 'Содержание программы искусственный интеллект'\n\n"
                "Или обратитесь к менеджерам программ ИТМО"
            )

        await update.message.reply_text(response, parse_mode='Markdown')

    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        program_count = len(self.programs_data)
        programs_list = "\n".join([f"• {name}" for name in self.programs_data.keys()]) if self.programs_data else "• Данные не загружены"

        help_text = (
            "🆘 **Справка по использованию бота:**\n\n"
            "**Команды:**\n"
            "• `/start` - Главное меню\n"
            "• `/profile <ваш_бэкграунд>` - Настроить профиль\n"
            "• `/recommendations` - Получить рекомендации\n"
            "• `/help` - Эта справка\n\n"
            "**Возможности:**\n"
            "• 🔍 Сравнение программ магистратуры\n"
            "• ❓ Ответы на вопросы о поступлении и обучении\n"
            "• 🎯 Персональные рекомендации дисциплин\n"
            "• 📚 Анализ учебных планов\n\n"
            f"**Загружено программ: {program_count}**\n"
            f"{programs_list}\n\n"
            "Просто задавайте вопросы или используйте кнопки!"
        )

        await update.message.reply_text(help_text, parse_mode='Markdown')

    def run(self):
        """Запуск бота"""
        if not self.token:
            logger.error("Токен бота не указан!")
            return

        if not self.programs_data:
            logger.error("Данные о программах не загружены! Запустите: python final_parser.py <urls>")
            return

        application = Application.builder().token(self.token).build()

        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_handler))
        application.add_handler(CommandHandler("profile", self.profile_handler))
        application.add_handler(CommandHandler("recommendations", self.recommendations_handler))
        application.add_handler(CallbackQueryHandler(self.button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))

        logger.info(f"Бот запущен! Загружено программ: {len(self.programs_data)}")
        application.run_polling()

if __name__ == "__main__":
    # Замените на ваш токен бота
    BOT_TOKEN = "8268067812:AAHBkAbew6jPzAbhdOSEQGWMzNiCRxcCFbA"

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️  Пожалуйста, укажите токен вашего Telegram бота в переменной BOT_TOKEN")
        print("Получить токен можно у @BotFather в Telegram")
        print("\n📋 Для тестирования бота:")
        print("1. Сначала запустите парсер: python final_parser.py https://abit.itmo.ru/program/master/ai https://abit.itmo.ru/program/master/ai_product")
        print("2. Получите токен у @BotFather")
        print("3. Замените YOUR_BOT_TOKEN_HERE на ваш токен")
        print("4. Запустите: python bot.py")
    else:
        bot = ITMOChatBot(BOT_TOKEN)
        bot.run()