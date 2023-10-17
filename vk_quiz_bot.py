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


def start(event, vk_api):
    greeting_message = "Привет, я бот для викторин! " \
                       "Чтобы начать - нажми кнопку Новый вопрос"
    send_answer(event, vk_api, greeting_message)


def handle_new_question_request(event, vk_api, database, quiz):
    user = event.user_id
    number_question = choice(list(quiz.keys()))    
    database.set(user, number_question)
    attempt = True
    send_answer(event, vk_api, quiz[number_question]['Вопрос'])
    print(quiz_set[number_question]['Ответ'])
    return attempt

def handle_solution_attempt(event, vk_api, database, quiz, attempt, user_score):
    user_answer = event.text
    user = event.user_id
    number_question = int(database.get(user))
    if not attempt:
        message = 'Нажмите "Новый вопрос"'
        send_answer(event, vk_api, message)   
        return attempt, user_score
    answer_match = fuzz.WRatio(user_answer, quiz[number_question]['Ответ'])    
    if answer_match > 70:
        message = 'Правильно! Поздравляю! Для следующего вопроса нажмите "Новый вопрос"' 
        user_score += 1
        attempt = False
    else:        
        message = 'Неправильно! Попробуйте ещё раз'
    send_answer(event, vk_api, message)
    return attempt, user_score     


def show_user_score(event, vk_api, user_score):
    message = f'Вы дали {user_score} правильных ответов'
    send_answer(event, vk_api, message)    


def show_right_answer(event, vk_api, database, quiz):
    user = event.user_id
    attempt = False     
    number_question = int(database.get(user))  
    send_answer(
        event,
        vk_api,        
        quiz[number_question]['Ответ']        
    )
    return attempt


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
    attempt = False
    user_score = 0    
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text == 'Старт':
                start(event, vk_api)
            elif event.text == 'Новый вопрос':
                attempt = handle_new_question_request(event, vk_api, database, quiz)
            elif event.text == 'Сдаться':
                attempt = show_right_answer(event, vk_api, database, quiz)
            elif event.text == 'Мой счёт':
                show_user_score(event, vk_api, user_score)
            else:
                attempt, user_score = handle_solution_attempt(event, vk_api, database, quiz, attempt, user_score)           
   

if __name__ == '__main__':
    main()