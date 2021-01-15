from peewee import *

DATABASE = '../drpg.db'
DEBUG = True

database = SqliteDatabase(DATABASE)


class BaseModel(Model):
    class Meta:
        database = database


class Scenario(BaseModel):
    id = IntegerField(primary_key=True)
    name = TextField()
    description = TextField()

    numbers_of_roles = IntegerField()
    numbers_of_rounds = IntegerField()

    votes_to_lose = IntegerField()
    killer_role_name = TextField()
    minutes_to_discuss = IntegerField()

    killer_win_msg = TextField()
    people_win_msg = TextField()

    @staticmethod
    def get_scenario_by_id(scenario_id):
        return Scenario.get(Scenario.id == scenario_id)

    @staticmethod
    def get_list_scenario_names():
        query = Scenario.select().dicts()
        scenario_list = []
        for row in query:
            scenario_list.append(row)
        return scenario_list

    @staticmethod
    def get_id_by_name(name):
        return Scenario.get(Scenario.name == name).id


class Role(BaseModel):
    id = IntegerField(primary_key=True)
    scenario_id = IntegerField()
    name = TextField()
    description = TextField()

    @staticmethod
    def get_list_roles(scenario_id):
        query = Role.select().where(Role.scenario_id == scenario_id).dicts()
        role_list = []
        for row in query:
            role_list.append(row)
        return role_list

    @staticmethod
    def get_name(role_id):
        return Role.get(Role.id == role_id).name

    @staticmethod
    def get_id_by_name(name):
        return Role.get(Role.name == name).id


class RoleInfo(BaseModel):
    role_id = IntegerField()
    round_number = IntegerField()
    info = TextField()

    class Meta:
        primary_key = CompositeKey('role_id', 'round_number')

    @staticmethod
    def get_info(role_id, round_number):
        return RoleInfo.get((RoleInfo.role_id == role_id) & (RoleInfo.round_number == round_number)).info


def create_tables():
    with database:
        database.create_tables([Scenario, Role, RoleInfo])


def insert_data_to_table(model: BaseModel, data):
    for data_dict in data:
        model.create(**data_dict)


def init_test_scenario_data():
    description = "Дикий Запад. Придорожная гостиница. Вечер. Группа случайных путников" \
                  " оказывается внутри, чтобы переждать метель. Метель никак не затихает, поэтому все" \
                  " вынуждены остаться там заночевать. Поужинав и чуть-чуть поговорив люди" \
                  " разбредаются по своим комнатам.\n" \
                  " Это старое здание, в котором удается поддерживать тепло лишь с помощью" \
                  " большого камина на первом этаже. Там же находится столовая. На втором этаже" \
                  " оборудованы гостиничные номера - маленькие комнатушки, со скрипучими кроватями" \
                  " и жесткими подушками.\n" \
                  " Посреди ночи раздается громкий крик отца Мартина: “Скорее! Все сюда!”." \
                  " Сбежавшиеся постояльцы обнаруживают труп хозяина гостиницы, который лежит в" \
                  " луже крови около камина.\n" \
                  " Вы отделены от цивилизации двадцатью километрами заснеженной дороги. Метель" \
                  " по прежнему не утихает, поэтому определять убийцу придется вам самим."

    scenario_data = [
        {'id': 1, 'name': 'Дикий запад', 'description': description,
         'numbers_of_roles': 3, 'numbers_of_rounds': 2, 'votes_to_lose': 2, 'killer_role_name': 'Отец Мартин',
         'killer_win_msg': 'Убийца выжил, вы лохи, убийца молодец',
         'people_win_msg': 'Вы поймали нужного убийцу, молодцы', 'minutes_to_discuss': 1},
    ]
    insert_data_to_table(Scenario, scenario_data)

    role_data = [
        {'id': 1, 'scenario_id': 1, 'name': 'Отец Мартин',
         'description': 'Cвященник. Молодой мужчина, короткие волосы, бритый,'
                        'одежда священника. Выразительный шрам на щеке.\n'
                        '- Отправился на Запад вести миссионерскую деятельность среди индейцев'},
        {'id': 2, 'scenario_id': 1, 'name': 'Фрэнк Дженкинс',
         'description': 'Солдат. Мужчина средних лет, имеет пышные подкрученныеусы, одет в форму офицера армии. '
                        'Левая рука перебинтована.\n'
                        '- Временно отправлен в отпуск, в связи с полученным ранением, едет домой'},
        {'id': 3, 'scenario_id': 1, 'name': 'Патрик Суини',
         'description': 'Ирландец. Молодой мужчина, лысая голова и рыжие бакенбарды. Бедно одет. '
                        'Сбитые костяшки на кулаках.\n- Едет в соседний город в поисках работы, так как из-за репутации'
                        ' дебошира его никуда не берут.'},
    ]
    insert_data_to_table(Role, role_data)

    role_info_data = [
        {'role_id': 1, 'round_number': 1, 'info': 'Рандомный текст, воспоминание Отца Мартина, первый круг'},
        {'role_id': 1, 'round_number': 2, 'info': 'Рандомный текст, воспоминание Отца Мартина, второй круг'},
        {'role_id': 2, 'round_number': 1, 'info': 'Рандомный текст, воспоминание Фрэнкa Дженкинса, первый круг'},
        {'role_id': 2, 'round_number': 2, 'info': 'Рандомный текст, воспоминание Фрэнкa Дженкинса, второй круг'},
        {'role_id': 3, 'round_number': 1, 'info': 'Рандомный текст, воспоминание Патрика Суини, первый круг'},
        {'role_id': 3, 'round_number': 2, 'info': 'Рандомный текст, воспоминание Патрикa Суини, второй круг'},
    ]

    insert_data_to_table(RoleInfo, role_info_data)


if __name__ == '__main__':
    create_tables()
    init_test_scenario_data()

