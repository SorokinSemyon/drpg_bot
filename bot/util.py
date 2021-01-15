from telegram import KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from logging import getLogger
import random
import app


# Декоратор для отладки событий от телеграма
def debug_requests(f):
    logger = getLogger(__name__)

    def inner(*args, **kwargs):
        try:
            logger.debug('Обращение в функцию {}'.format(f.__name__))
            return f(*args, **kwargs)
        except Exception:
            logger.exception('Ошибка в обработчике {}'.format(f.__name__))
            raise

    return inner


def resize_keyboard(keyboard: list):
    odd_len = len(keyboard) % 2 != 0

    resized_keyboard = []
    for i in range(len(keyboard) // 2):
        resized_keyboard.append([keyboard[2 * i], keyboard[2 * i + 1]])

    if odd_len:
        resized_keyboard.append([keyboard[-1]])

    return resized_keyboard


def get_base_keyboard(buttons: list):
    resized_keyboard = resize_keyboard(buttons)

    keyboard = [[KeyboardButton(button) for button in rows] for rows in resized_keyboard]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True)


def get_inline_keyboard(buttons: list):
    buttons = resize_keyboard(buttons)
    keyboard = [[InlineKeyboardButton(button, callback_data=button) for button in rows] for rows in buttons]

    return InlineKeyboardMarkup(keyboard)


def strike_string(string):
    strike_sir = ''
    for char in string:
        strike_sir += (char + '̶')
    return strike_sir


def align_string(string: str, length: int):
    string += (' ' * (length - len(string)))
    return string


def generate_code():
    numbers = '0123456789'
    code = ''.join(random.choice(numbers) for i in range(5))
    print(code)
    if code in list(app.room_codes.values()):
        print('repeat: ', code)
        code = generate_code()
    return code


def seconds_to_timer(seconds: int):
    sec = seconds % 60
    if sec < 10:
        sec = '0' + str(sec)
    else:
        sec = str(sec)

    return f"{seconds // 60}:{sec}"


def shorten_string(string):
    return string[:250] + '...'
