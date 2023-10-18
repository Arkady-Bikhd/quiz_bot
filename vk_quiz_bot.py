import random

from os import environ
from dotenv import load_dotenv
from random import choice

import vk_api as vk
import redis
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from thefuzz import fuzz
from quiz import forming_quiz, get_quiz_file


def create_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
    return keyboard


def send_answer(event, vk_api, bot_answer):
    keyboard = create_keyboard()    
    vk_api.messages.send(
        user_id=event.user_id,
        message=bot_answer,
        keyboard=keyboard.get_keyboard(),
        random_id=random.randint(1,1000)
    )


def start(event, vk_api, database):
    greeting_message = "Привет, я бот для викторин! " \
                       "Чтобы начать - нажми кнопку Новый вопрос"
    attempt = False
    user_score = 0
    number_question = -1 
    user = event.user_id
    database.set(user, f'{number_question},{attempt},{user_score}')
    send_answer(event, vk_api, greeting_message)


def handle_new_question_request(event, vk_api, database, quiz):
    user = event.user_id
    user_status = database.get(user)
    user_score = user_status.split(',')[2]
    number_question = choice(list(quiz.keys()))
    attempt = True    
    database.set(user, f'{number_question},{attempt},{user_score}')    
    send_answer(event, vk_api, quiz[number_question]['Вопрос'])    
    return attempt


def handle_solution_attempt(event, vk_api, database, quiz):
    user_answer = event.text
    user = event.user_id
    user_status = database.get(user).split(',')
    number_question = int(user_status[0])
    attempt = bool(user_status[1])
    user_score = int(user_status[2])
    if not attempt:
        message = 'Нажмите "Новый вопрос"'
        send_answer(event, vk_api, message)   
        return
    answer_match = fuzz.WRatio(user_answer, quiz[number_question]['Ответ'])    
    if answer_match > 70:
        message = 'Правильно! Поздравляю! Для следующего вопроса нажмите "Новый вопрос"' 
        user_score += 1
        attempt = False
        database.set(user, f'{number_question},{attempt},{user_score}')
    else:        
        message = 'Неправильно! Попробуйте ещё раз'
    send_answer(event, vk_api, message)        


def show_user_score(event, vk_api, database):
    user = event.user_id
    user_status = database.get(user)
    user_score = user_status.split(',')[2]
    message = f'Вы дали {user_score} правильных ответов'
    send_answer(event, vk_api, message)    


def show_right_answer(event, vk_api, database, quiz):
    user = event.user_id
    user_status = database.get(user).split(',')
    number_question = int(user_status[0])
    user_score = user_status[2]
    attempt = False
    database.set(user, f'{number_question},{attempt},{user_score}')  
    send_answer(
        event,
        vk_api,        
        quiz[number_question]['Ответ']        
    )    


def main():
    load_dotenv()
    vk_access_token = environ['VK_ACCESS_TOKEN']
    redis_host = environ['REDIS_HOST']
    redis_port = environ['REDIS_PORT']
    redis_password = environ['REDIS_PASSWORD']       
    vk_session = vk.VkApi(token=vk_access_token)
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)
    database = redis.StrictRedis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        charset='utf-8',
        decode_responses=True
        )
    quiz = forming_quiz(get_quiz_file())       
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text == 'Старт':
                start(event, vk_api, database)
            elif event.text == 'Новый вопрос':
                handle_new_question_request(event, vk_api, database, quiz)
            elif event.text == 'Сдаться':
                show_right_answer(event, vk_api, database, quiz)
            elif event.text == 'Мой счёт':
                show_user_score(event, vk_api, database)
            else:
                handle_solution_attempt(event, vk_api, database, quiz)           
   

if __name__ == '__main__':
    main()