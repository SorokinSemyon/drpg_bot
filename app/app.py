from db import Scenario, Role, RoleInfo
from util import *

# Комнаты, в которых сейчас проходит игра {room_id: obj app.Room}
rooms = {}
# Авторизованные пользователи {user_id: obj app.User}
users = {}
# Коды для доступа в комнаты {room_id: code}
room_codes = {}

# {Состояние пользователя: Следующее состояние}
next_state = {'create room':      'read description',
              'enter room':       'read description',
              'read description': 'select role',
              'select role':      'wait role',
              'wait role':        'select role',
              'read info':        'discussion',
              'discussion':       'voting',
              'voting':           'read info'}

# {Состояние пользователя: Команды, которые он может отправлять}
commands = {'start':            ['Создать комнату', 'Войти в комнату'],
            'create room':      ['<scenario_names>', 'Выйти'],
            'enter room':       ['<room_code>', 'Выйти'],
            'read description': ['Перейти к выбору роли', 'Выйти'],
            'select role':      ['<not_selected_roles>', 'Выйти'],
            'wait role':        ['Изменить выбор', 'Выйти'],
            'read info':        ['Получить воспоминание'],
            'discussion':       ['Завершить обсуждение'],
            'voting':           ['<suspected_roles>'],
            'finish':           ['Выйти'],
            'killed':           ['Выйти']}


# Комната, это сущность, которая объединяет игроков играющих партию, и дает им доступ к сценарию
class Room:
    def __init__(self, room_id: int, scenario):
        self.id = room_id
        self.scenario_id = scenario.id

        self.numbers_of_rounds = scenario.numbers_of_rounds
        self.numbers_of_roles = scenario.numbers_of_roles
        self.current_round = 0

        self.votes_to_lose = scenario.votes_to_lose
        self.killer_role_name = scenario.killer_role_name
        self.minutes_to_discuss = scenario.minutes_to_discuss

        self.killer_win_msg = scenario.killer_win_msg
        self.people_win_msg = scenario.people_win_msg

        self.scenario_description = scenario.description
        self.supplement_description()
        self.users = []

    def supplement_description(self):
        self.scenario_description = f'Данный сценарий расчитан на *{self.numbers_of_roles} человек*\n' \
                                     'Длительность игры: ' \
                                    f'*~{self.numbers_of_rounds * self.minutes_to_discuss} минут*\n\n' \
                                    f'*Предыстория:*\n{self.scenario_description}'

    def add_user(self, user):
        self.users.append(user)

    def del_user(self, user_id: int):
        number_users = self.count_user()

        if number_users == 1:
            del rooms[self.id]
            del self
            return

        for i in range(number_users):
            if self.users[i].id == user_id:
                del self.users[i]
                return

    def get_list_roles(self):
        return Role.get_list_roles(self.scenario_id)

    def get_users_id(self):
        users_id = []
        for user in self.users:
            users_id.append(user.id)
        return users_id

    def count_user(self):
        return len(self.users)

    def count_user_with_role(self):
        count = 0
        for user in self.users:
            if user.role_id is not None:
                count += 1
        return count

    def increment_round(self):
        self.current_round += 1

    def transfer_users_to_state(self, state):
        for user in self.users:
            if user.state != 'killed':
                user.state = state

    def is_every_users_in_state(self, state):
        for user in self.users:
            if user.state != state and user.state != 'killed':
                return False
        return True

    def voting(self, role_name):
        for user in self.users:
            if user.role_name == role_name:
                user.votes += 1
                break

    def get_outcome_text(self):
        win_msg = ''
        distribution_of_votes = 'Распределение голосов:'
        for user in self.users:
            votes_str = f'{user.role_name} ({user.name}): {user.votes} голосов'
            if user.state == 'killed':
                votes_str = strike_string(votes_str)

                if user.role_name == self.killer_role_name:
                    win_msg = user.room.people_win_msg
            distribution_of_votes += ('\n' + votes_str)

        if win_msg == '':
            win_msg = self.killer_win_msg

        return win_msg + '\n\n' + distribution_of_votes


class User:
    def __init__(self, user_id: int, username: str):
        self.id = user_id
        self.name = username
        self.state = 'start'

        self.room: Room = None
        self.role_id = None
        self.role_name = None
        self.votes = 0

        self.screens = {}

    def go_next_state(self):
        self.state = next_state[self.state]

    def create_room(self, scenario_id: int):
        scenario = Scenario.get_scenario_by_id(scenario_id)
        self.room = Room(len(rooms) + 1, scenario)

        self.room.add_user(self)

        rooms.update({self.room.id: self.room})

    def enter_room(self, room_id: int):
        self.room = rooms[room_id]
        self.room.add_user(self)

    @staticmethod
    def get_list_scenario_names():
        scenario_list = Scenario.get_list_scenario_names()
        scenario_names = []

        for scenario in scenario_list:
            scenario_names.append(scenario['name'])

        return scenario_names

    # Возвращает dict в формате {role_name: role_description}
    def get_list_roles(self) -> dict:
        role_list = self.room.get_list_roles()

        roles = {}
        for role in role_list:
            roles.update({role["name"]: role["description"]})

        return roles

    def get_list_not_selected_roles(self) -> list:
        not_selected_roles = list(self.get_list_roles().keys())

        for another_user in self.room.users:
            if another_user.role_name in not_selected_roles:
                index = not_selected_roles.index(another_user.role_name)
                del not_selected_roles[index]

        return not_selected_roles

    def get_list_suspected_roles(self) -> list:
        suspected_roles = []

        for another_user in self.room.users:
            if another_user.id != self.id and another_user.state != 'killed':
                suspected_roles.append(another_user.role_name)

        return suspected_roles

    def get_info(self, round_number):
        return RoleInfo.get_info(self.role_id, round_number)

    def create_screen(self, message_id: int, screen_type: str):
        self.screens.update({screen_type: message_id})

    def update_screen_message_id(self, message_id: int, screen_type: str):
        self.screens[screen_type] = message_id

    def get_screen_message_id(self, screen_type: str):
        try:
            return self.screens[screen_type]
        except KeyError:
            return None

    def get_screen_type_by_message_id(self, message_id):
        for screen_type, msg_id in self.screens.items():
            if msg_id == message_id:
                return screen_type
