import telegram
from telegram.error import BadRequest
from telegram.ext import Updater, MessageHandler, Filters, CallbackQueryHandler
from telegram.ext import CommandHandler

from datetime import datetime, timedelta
import app
import db

from screen import *


@debug_requests
def authorization(update, context):
    bot = context.bot

    try:
        update.message.delete()
    except BadRequest:
        pass

    tg_user = update.effective_user

    # Если пользователь уже авторизовался
    if tg_user.id in app.users:
        return

    # Если у пользователя есть фамилия, заменить ее на первый символ с точкой
    last_name = f' {tg_user.last_name[0]}.' if tg_user.last_name is not None else ''
    username = tg_user.first_name + last_name

    user: app.User = app.User(user_id=tg_user.id,
                              username=username)
    app.users.update({user.id: user})

    send_screen('active', user, bot)


@debug_requests
def msg_handler(update, context):
    # Удалить сообщение отправленное пользователем, так как оно не представляет важности
    # и нужно лишь для того, чтобы изменить состояние системы
    update.message.delete()

    tg_user = update.effective_user

    # Не выполнять команду, если сообщение отправлено от неавторизованного пользователя
    if tg_user.id not in app.users:
        return

    user = app.users[tg_user.id]

    # Получить команду, которую отправил пользователь
    command = update.message.text

    if not validate_command(command, user):
        return

    execute_command(user, command, context.bot)


def validate_command(command: str, user: app.User):
    state = user.state

    if command in app.commands[state]:
        return True

    get_valid_commands = {'create room': user.get_list_scenario_names,
                          'enter room':  app.room_codes.values,
                          'select role': user.get_list_not_selected_roles,
                          'voting':      user.get_list_suspected_roles}

    if command in get_valid_commands[state]():
        return True

    return False


def execute_command(user: app.User, command: str, bot):
    if command == 'Выйти':
        # Если пользователь хочет выйти, когда он находится в комнате
        if user.room is not None:
            user.room.del_user(user.id)
            update_room_screen_for_all(user.room, bot)

        # Удаление всех экранов пользователя
        for message_id in list(user.screens.values()):
            bot.deleteMessage(chat_id=user.id, message_id=message_id)

        del app.users[user.id]

        return

    if user.state == 'start':
        if command == 'Создать комнату':
            user.state = 'create room'
        elif command == 'Войти в комнату':
            user.state = 'enter room'

        send_screen('active', user, bot)

        # Так как пользователь уже переведен в следующее состояние
        return

    elif user.state == 'create room':
        scenario_name = command
        scenario_id = int(db.Scenario.get_id_by_name(scenario_name))
        user.create_room(scenario_id)

        app.room_codes.update({user.room.id: generate_code()})

        send_screen('scenario_description', user, bot)

    elif user.state == 'read description':
        send_screen('role', user, bot)
        send_screen('room', user, bot)

    elif user.state == 'enter room':
        room_code = command

        # Получить id комнаты через код
        room_id = list(app.room_codes.keys())[list(app.room_codes.values()).index(room_code)]

        room: app.Room = app.rooms[room_id]
        # В комнату нельзя зайти, если она заполнена
        if room.count_user() == room.numbers_of_roles:
            return

        user.enter_room(room_id)

        send_screen('scenario_description', user, bot)

    elif user.state == 'select role':
        role_name = command
        user.role_name = role_name

        role_id = int(db.Role.get_id_by_name(role_name))
        user.role_id = role_id

        update_room_screen_for_all(user.room, bot)

        user_with_role = user.room.count_user_with_role()
        numbers_of_roles = user.room.numbers_of_roles

        # Если все роли выбраны
        if user_with_role == numbers_of_roles:
            user.room.transfer_users_to_state('read info')
            user.room.increment_round()

            update_active_screen_for_all(user, bot)
            update_room_screen_for_all(user.room, bot, with_code=False)

            # Так как пользователь уже переведен в следующее состояние
            return

        # Обновить список доступных ролей для остальных игроков
        update_active_screen_for_all(user, bot, send_myself=False)

    elif user.state == 'wait role':
        # Вернуть пользователя к состоянию выбора роли
        user.go_next_state()

        # Сбросить прежний выбор
        user.role_id = None
        user.role_name = None

        # Обновить список игроков
        update_room_screen_for_all(user.room, bot)

        # Обновить список доступных ролей
        update_active_screen_for_all(user, bot)

    elif user.state == 'read info':
        send_screen('role_info', user, bot)

        # Игрок получил воспоминание
        user.go_next_state()
        send_screen('active', user, bot)

        if user.room.is_every_users_in_state('discussion'):
            room_timers.update({user.room.id: datetime.now() + timedelta(minutes=user.room.minutes_to_discuss)})

            updater.job_queue.start()
            job = updater.job_queue
            job.run_repeating(discussion_timer, interval=1, first=0, context=user.room)

            create_timer(user.room, bot)
            update_active_screen_for_all(user, bot)

    elif user.state == 'discussion':
        # Игрок хочет перейти к голосованию
        user.go_next_state()
        send_screen('active', user, bot)

        if user.room.is_every_users_in_state('voting'):
            update_active_screen_for_all(user, bot)

            del room_timers[user.room.id]
            delete_screen_for_all('timer', user.room, bot)

    elif user.state == 'voting':
        # Игрок проголосовал
        user.go_next_state()
        send_screen('active', user, bot)

        role_name = command
        user.room.voting(role_name)

        if user.room.is_every_users_in_state('read info'):
            for another_user in user.room.users:
                if another_user.votes >= another_user.room.votes_to_lose and another_user.state != 'killed':
                    another_user.state = 'killed'
                    send_screen('active', another_user, bot)

            if user.room.current_round == user.room.numbers_of_rounds:
                user.room.transfer_users_to_state('finish')
                update_active_screen_for_all(user, bot, to_killed_too=True)

                # Так как последний раунд - игра закончена
                return

            user.room.increment_round()
            update_active_screen_for_all(user, bot)

    # Все эти состояния относятся к тем, где происходит взаимодействие с другими игроками
    # Пользователю необходимо понять последний ли он - выбрал роль, получил воспоминание, проголосовал
    # А для того, чтобы это понять, нужно изменить состояние во время выполнения команды, а не после нее.
    if user.state not in ['wait role', 'read info', 'discussion', 'voting']:
        user.go_next_state()
        send_screen('active', user, bot)


@debug_requests
def update_room_screen_for_all(room: app.Room, bot, with_code=True):
    users_id = room.get_users_id()

    some_user = room.users[0]
    text, markup = get_room_screen(some_user, with_code)

    for user_id in users_id:
        user = app.users[user_id]

        try:
            message_id = user.get_screen_message_id('room')
            bot.edit_message_text(chat_id=user_id,
                                  message_id=message_id,
                                  text=text,
                                  reply_markup=markup,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        except:
            pass


@debug_requests
def update_active_screen_for_all(user: app.User, bot, send_myself=True, to_killed_too=False):
    for another_user in user.room.users:
        # В этих состояниях пользователь не должен получать сообщения от других пользователей
        # Если только не установлен флаг to_killed_too
        if another_user.state not in ['killed', 'read description', 'wait role'] or to_killed_too:
            if another_user.id != user.id or send_myself:
                text, markup = get_active_screen(another_user, is_screen_personal=False)

                msg = bot.sendMessage(chat_id=another_user.id,
                                      text=text,
                                      reply_markup=markup,
                                      parse_mode=telegram.ParseMode.MARKDOWN)

                bot.deleteMessage(chat_id=another_user.id,
                                  message_id=another_user.get_screen_message_id('active'))

                another_user.update_screen_message_id(msg.message_id, 'active')


@debug_requests
def delete_screen_for_all(screen_type: str, room: app.Room, bot):
    for user in room.users:
        if user.state != 'killed':
            message_id = user.get_screen_message_id(screen_type)

            if message_id is None:
                continue

            bot.deleteMessage(chat_id=user.id, message_id=message_id)
            del user.screens[screen_type]


@debug_requests
def create_timer(room: app.Room, bot):
    for another_user in room.users:
        if another_user.state != 'killed':
            msg = bot.sendMessage(chat_id=another_user.id,
                                  text=f"До конца обсуждения осталось:",
                                  parse_mode=telegram.ParseMode.MARKDOWN)
            another_user.create_screen(msg.message_id, 'timer')


@debug_requests
def discussion_timer(context):
    room: app.Room = context.job.context
    users = room.users

    is_time_over = False
    if room.id in room_timers:
        is_time_over = datetime.now() > room_timers[room.id]

    # Завершение хода таймера может произойти в двух случаях, если время закончилось,
    # или если таймера нет - значит игроки решили досрочно завершить голосование
    if is_time_over or room.id not in room_timers:
        context.job.schedule_removal()

        if room.id in room_timers:
            del room_timers[room.id]

        delete_screen_for_all('timer', room, context.bot)

        room.transfer_users_to_state('voting')

        some_user = room.users[0]
        update_active_screen_for_all(some_user, context.bot)
        return

    timer = seconds_to_timer((room_timers[room.id] - datetime.now()).seconds)

    for user in users:
        if 'timer' in user.screens:
            timer_message_id = user.get_screen_message_id('timer')
            try:
                context.bot.edit_message_text(chat_id=user.id,
                                              message_id=timer_message_id,
                                              text="До конца обсуждения осталось: " + timer)
            except:
                pass


@debug_requests
def send_screen(screen_type, user: app.User, bot):
    if screen_type in user.screens:
        action = 'update'
    else:
        action = 'create'

    get_screen = {'active': get_active_screen,
                  'scenario_description': get_scenario_description_screen,
                  'role': get_role_screen,
                  'room': get_room_screen,
                  'role_info': get_role_info_screen}

    text, markup = get_screen[screen_type](user)

    if action == 'create':
        screen_msg = bot.sendMessage(chat_id=user.id,
                                     text=text,
                                     reply_markup=markup,
                                     parse_mode=telegram.ParseMode.MARKDOWN)

        user.create_screen(screen_msg.message_id, screen_type)

        # При создании 'экрана комнаты' для нового игрока, нужно обновить его для остальных игроков
        if screen_type == 'room':
            update_room_screen_for_all(user.room, bot)

    elif action == 'update':
        # id Сообщения, которое нужно изменить
        message_id = user.get_screen_message_id(screen_type)

        if screen_type == 'role_info':
            try:
                bot.edit_message_text(chat_id=user.id,
                                      message_id=message_id,
                                      text=text,
                                      reply_markup=markup,
                                      parse_mode=telegram.ParseMode.MARKDOWN)
            except BadRequest:
                pass

        # Обновление 'активного экрана' на самом деле является отправкой нового экрана и удаление предыдущего.
        # Так необходимо сделать, так как частью активного экрана является пользовательская клавиатура.
        # На данный момент Telegram не позволяет изменять пользовательскую клавиатуру,
        # кроме как отправкой нового сообщения.
        elif screen_type == 'active':
            active_msg = bot.sendMessage(chat_id=user.id,
                                         text=text,
                                         reply_markup=markup,
                                         parse_mode=telegram.ParseMode.MARKDOWN)
            bot.delete_message(user.id, message_id)
            user.update_screen_message_id(active_msg.message_id, 'active')


@debug_requests
def keyboard_callback_handler(update, context):
    tg_user = update.effective_user
    user = app.users[tg_user.id]

    query = update.callback_query
    data = query.data

    screen_type = user.get_screen_type_by_message_id(query.message['message_id'])

    get_screen = {'scenario_description': get_scenario_description_screen,
                  'role':                 get_role_screen,
                  'role_info':            get_role_info_screen}

    text, markup = get_screen[screen_type](user, data)

    query.edit_message_text(
        text=text,
        reply_markup=markup,
        parse_mode=telegram.ParseMode.MARKDOWN)


if __name__ == '__main__':
    TOKEN = '952700432:AAExo2EJ7xnxcfrTdNrbe2tKJfzNSoks__M'

    updater = Updater(token=TOKEN,
                      base_url="https://telegg.ru/orig/bot",
                      use_context=True)
    dispatcher = updater.dispatcher

    room_timers = {}

    start_handler = CommandHandler('start', authorization)
    dispatcher.add_handler(start_handler)

    message_handler = MessageHandler(Filters.text, msg_handler)
    dispatcher.add_handler(message_handler)

    buttons_handler = CallbackQueryHandler(callback=keyboard_callback_handler, pass_chat_data=True)
    dispatcher.add_handler(buttons_handler)

    updater.start_polling()
