import logging
from os import environ
from enum import Enum, auto
from random import choice

import redis
from dotenv import load_dotenv
from more_itertools import chunked
from telegram import Bot, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler, Updater
from thefuzz import fuzz
from quiz import forming_quiz, get_quiz_file
from logging_api import TelegramLogsHandler


logger = logging.getLogger('quiz_bot')


class States(Enum):    
    CHOISE_BUTTON = auto()   


def start(update, context):    
    keyboard_captions = ['Новый вопрос', 'Сдаться', 'Мой счёт',]
    message_keyboard = list(chunked(keyboard_captions, 2))
    markup = ReplyKeyboardMarkup(
        message_keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    context.user_data['markup'] = markup
    context.user_data['user_score'] = 0
    menu_msg = 'Привет! Я - бот викторин!'
    update.message.reply_text(text=menu_msg, reply_markup=markup)
    return States.CHOISE_BUTTON


def handle_new_question_request(update, context):
    database = context.bot_data['redis']
    context.user_data['user'] = update.message.chat_id     
    quiz = context.bot_data['quiz']
    number_question = choice(list(quiz.keys()))    
    database.set(context.user_data['user'], number_question)
    context.user_data['attempt'] = True        
    update.message.reply_text(quiz[number_question]['Вопрос'], reply_markup=context.user_data['markup'])
    return States.CHOISE_BUTTON


def handle_solution_attempt(update, context):
    database = context.bot_data['redis']    
    user_answer = update.message.text
    quiz = context.bot_data['quiz']     
    number_question = int(database.get(context.user_data['user']))
    if not context.user_data['attempt']:
        message = 'Нажмите "Новый вопрос"'
        update.message.reply_text(message, reply_markup=context.user_data['markup'])   
        return States.CHOISE_BUTTON 
    answer_match = fuzz.WRatio(user_answer, quiz[number_question]['Ответ'])    
    if answer_match > 70:
        message = 'Правильно! Поздравляю! Для следующего вопроса нажмите "Новый вопрос"' 
        context.user_data['user_score'] += 1
        context.user_data['attempt'] = False
    else:        
        message = 'Неправильно! Попробуйте ещё раз'
    update.message.reply_text(message, reply_markup=context.user_data['markup'])          
    return States.CHOISE_BUTTON


def show_user_score(update, context):
    user_score = context.user_data['user_score']
    message = f'Вы дали {user_score} правильных ответов'
    update.message.reply_text(message, reply_markup=context.user_data['markup'])    
    return States.CHOISE_BUTTON


def show_right_answer(update, context):
    database = context.bot_data['redis']
    quiz = context.bot_data['quiz']
    context.user_data['attempt'] = False     
    number_question = int(database.get(context.user_data['user']))  
    update.message.reply_text(
        quiz[number_question]['Ответ'], 
        reply_markup=context.user_data['markup']
    )
    return States.CHOISE_BUTTON


def send_error(update, context):
    logger.error('Случилась ошибка')


def main():
    load_dotenv()
    tg_bot_token = environ['TG_BOT_TOKEN']
    notice_bot_token = environ['NOTICE_BOT_TOKEN']
    notice_chat_id = environ['NOTICE_CHAT_ID']
    redis_host = environ['REDIS_HOST']
    redis_port = environ['REDIS_PORT']
    redis_password = environ['REDIS_PASSWORD']    
    notice_bot = Bot(token=notice_bot_token)
    logger.setLevel(logging.WARNING)       
    logger.addHandler(
        TelegramLogsHandler(
            tg_bot=notice_bot,
            chat_id=notice_chat_id,
        )
    )  
    database = redis.StrictRedis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        charset='utf-8',
        decode_responses=True
        )
    updater = Updater(token=tg_bot_token, use_context=True)
    dispatcher = updater.dispatcher       
    dispatcher.bot_data['quiz'] = forming_quiz(get_quiz_file())
    dispatcher.bot_data['redis'] = database
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={            
            States.CHOISE_BUTTON: [
                MessageHandler(
                    Filters.text("Новый вопрос"), handle_new_question_request,
                ),
                MessageHandler(
                    Filters.text("Мой счёт"), show_user_score,
                ),
                MessageHandler(
                    Filters.text("Сдаться"), show_right_answer,
                ),
                MessageHandler(
                    Filters.text, handle_solution_attempt
                ),
            ],       
        },
        fallbacks=[],
        allow_reentry=True,
        name='bot_conversation',
    )
    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(send_error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
