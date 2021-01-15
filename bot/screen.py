import app
from util import *

screen_text = {'start':            'Перед тем как начать игру, всем игрокам нужно собраться в одной комнате.\n'
                                   'Создайте комнату, если ее ещё нет, или войдите в уже существующую',

               'create room':      'Выбери сценарий',

               'enter room':       'Откройте клавиатуру и введите код комнаты:',

               'read description': 'Прочтите описание сценария и затем перейдите к выбору роли',

               'wait role':        'Ожидаем пока присоединятся остальные игроки',

               'select role':      'Прочитайте описание персонажей и выбирите того, за кого вы хотите играть',

               'read info':        'Ждем пока проголосуют другие',

               'discussion':       'Ждем пока остальные откроют воспоминания',

               'voting':           'Для того, чтобы завершить обсуждение, нужно чтобы это подтвердили все',

               'killed':           'Вы выбыли из игры.\n'
                                   'Больше вы не можете получать воспоминания и участвовать в голосовании'}

# Текст активного экрана, который отправляется всем
common_screen_text = {'select role': 'Прочитайте описание персонажей и выбирите того, за кого вы хотите играть',

                      'read info':   'Начинается {room.current_round} раунд.\n'
                                     'Получите воспоминание и перескажите его своими словами.\n'
                                     'Обсуждение начнется, когда каждый игрок получит воспоминание',

                      'discussion':  'Обсуждение началось.\n'
                                     'Вы можете завершить его досрочно, если все игроки согласны с этим',

                      'voting':      'Выберите того, кого вы подозреваете больше всего',

                      'finish':      '_Игра закончилась. Убийцей был *{room.killer_role_name}*\n'}


def get_common_screen_text(state: str, room: app.Room):
    text = common_screen_text[state] \
        .replace('{room.current_round}', str(room.current_round)) \
        .replace('{room.minutes_to_discuss}', str(room.minutes_to_discuss)) \
        .replace('{room.killer_role_name}', room.killer_role_name)

    return text


# Экран с действиями (кнопками) доступными игроку и поясненем к доступным действиям.
# Говорит игроку о состоянии в котором он находится
def get_active_screen(user: app.User, is_screen_personal=True):
    if user.state == 'killed':
        print('KILLED')

    btn = app.commands[user.state]

    if is_screen_personal:
        text = screen_text[user.state]

        if user.state in ['read info', 'discussion', 'voting', 'killed']:
            btn = ['😏']

    else:
        if user.state == 'killed' and user.room.current_round == user.room.numbers_of_rounds:
            text = get_common_screen_text('finish', user.room)
        else:
            text = get_common_screen_text(user.state, user.room)

        if user.state in ['finish', 'killed']:
            text += user.room.get_outcome_text() + '_'

    get_group_btn = {'<scenario_names>': user.get_list_scenario_names,
                     '<room_code>': lambda: [],
                     '<not_selected_roles>': user.get_list_not_selected_roles,
                     '<suspected_roles>': user.get_list_suspected_roles}

    group_btn = btn[0]
    if group_btn in get_group_btn:
        btn = get_group_btn[group_btn]() + btn[1:]

    markup = get_base_keyboard(btn)

    return f'_{text}_', markup


# Экран с информацией о комнате, не связанную со сценарием, Код для входа в комнату, Список игроков
def get_room_screen(user: app.User, with_code=True):
    room = user.room
    users = list(room.users)

    if with_code:
        text = f'*Код для входа в комнату: *{app.room_codes[room.id]}\n' \
               f'*Список игроков: ({room.count_user_with_role()}/{room.numbers_of_roles})*'
    else:
        text = '*Список игроков:*'

    role_names = [user.role_name for user in users if user.role_name is not None]
    if role_names:
        len_max_role_name = len(max(role_names, key=len))
        if len_max_role_name < len('Нет роли'):
            len_max_role_name = len('Нет роли')
    else:
        len_max_role_name = len('Нет роли')

    players_list = ''
    for user in users:
        if user.role_id is None:
            role_name = 'Нет роли: '
        else:
            role_name = user.role_name + ': '

        players_list += f'{align_string(role_name, len_max_role_name + 2)}'
        players_list += user.name + '\n'

    return f'{text}\n`{players_list}`', None


# Экран с информацией, доступной конкретному игроку
def get_role_info_screen(user: app.User, round_number=None):
    if round_number is None:
        round_number = user.room.current_round

    if round_number != 'Скрыть':
        text = user.get_info(round_number)
    else:
        text = '🙈'

    markup = get_inline_keyboard([str(number + 1) for number in range(user.room.current_round)] + ['Скрыть'])
    return text, markup


# Экран с описанием персонажей
def get_role_screen(user: app.User, role=None):
    roles = user.get_list_roles()
    role_names = list(roles.keys())

    if role is None:
        role = role_names[0]

    description = roles[role]
    text = f'*Описание персонажа* {role}:\n' \
           f'{description}\n\n' \
           f'Для просмотра описания другого персонажа, нажмите на кнопку'

    del role_names[role_names.index(role)]

    markup = get_inline_keyboard(role_names)

    return text, markup


# Экран с описанием сценария (на сколько человек расчитан, продолжительность, предыстория)
def get_scenario_description_screen(user: app.User, data: str = 'Показать описание польностью'):
    text = user.room.scenario_description
    if len(text) < 250:
        return text, None

    if data == 'Показать описание полностью':
        button_string = 'Cкрыть'
    else:
        button_string = 'Показать описание полностью'
        text = shorten_string(text)

    markup = get_inline_keyboard([button_string])

    return text, markup
