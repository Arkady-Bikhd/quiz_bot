import argparse


def forming_quiz(filename):
    with open(filename, encoding='KOI8-R') as quiz_file:
        quiz = quiz_file.read().split('\n'*2)       
    quiz_set = dict()
    question_answer = dict()
    number_queston = 1            
    for line in quiz:        
        is_answer = False            
        if 'Вопрос' in line:
            question_answer['Вопрос'] = line.split(':\n')[1]                    
        if 'Ответ' in line:
            question_answer['Ответ'] = line.split(':\n')[1]
            is_answer = True                   
        if is_answer:
            quiz_set[number_queston] = question_answer
            number_queston += 1
            question_answer = dict()             
    return quiz_set  


def get_quiz_file():
    parser = argparse.ArgumentParser(
        description='Формирование вопросов викторины',               
    )
    parser.add_argument('-qf', '--qwest_file', default='leti16bl.txt', help='Путь к файлу с вопросами')
    args = parser.parse_args()
    return args.qwest_file
