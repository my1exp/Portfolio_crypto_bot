from requests import Session
from aiogram import Bot, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import json
import api_config
import os
from dotenv import load_dotenv

load_dotenv()

bot = Bot(os.getenv('BOT_TOKEN'))
db_path = '\\app_data\\db.db'

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class AssetStates(StatesGroup):
    asset_check_name = State()
    asset_add_currency = State()
    asset_delete_currency = State()
    asset_supply = State()
    asset_price = State()
    asset_id_for_edit = State()
    user_action_for_edit = State()
    user_value_for_edit = State()
    user_value_for_delete = State()


class User:
    def __init__(self, telegram_id) -> None:
        self.telegram_id = telegram_id

    def check_user_record(self):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('create table if not exists users (telegram_id INTEGER primary key)')
        cursor.execute('select telegram_id from users where telegram_id = ?', (self.telegram_id,))
        result = cursor.fetchone()
        return result

    def create_user_record(self):
        inserted_id = None
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('create table if not exists users (telegram_id INTEGER primary key)')
        cursor.execute('insert into users (telegram_id) values (?)', (self.telegram_id,))
        conn.commit()
        inserted_id = cursor.lastrowid
        conn.close()
        return inserted_id

    def check_portfolio(self):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''create table if not exists portfolio (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          ticker TEXT,
                          price REAL,
                          supply real,
                          r_telegram_id INTEGER,
                          FOREIGN KEY(r_telegram_id) REFERENCES users(telegram_id)
                          )''')
        cursor.execute('''select sum(price * supply)/ sum(supply) as avg_, sum(supply) as supply, ticker
                               from portfolio where r_telegram_id = ?
                               group by ticker
                               order by sum(price) * sum(supply) desc''',
                       (self.telegram_id,))
        result = cursor.fetchall()
        conn.close()
        return result

    def last_added_asset(self):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''select ticker, price, supply, r_telegram_id
                                from(
                                select *, row_number() over (order by id desc) as r_w
                                from portfolio
                                where r_telegram_id = ?)
                                where r_w = 1''',
                       (self.telegram_id,))
        result = cursor.fetchone()
        conn.close()
        return result

    def check_asset_in_portfolio(self, asset_name):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''select ticker
                                from portfolio
                                where r_telegram_id = ?
                                and ticker = ?''',
                       (self.telegram_id, asset_name))
        result = cursor.fetchone()
        conn.close()
        return result

    def delete_asset_from_portfolio(self, asset_name):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''delete from portfolio
                                where r_telegram_id = ?
                                and ticker = ?''',
                       (self.telegram_id, asset_name))
        conn.commit()
        conn.close()

    def check_all_user_assets(self):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''create table if not exists portfolio (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          ticker TEXT,
                          price REAL,
                          supply real,
                          r_telegram_id INTEGER,
                          FOREIGN KEY(r_telegram_id) REFERENCES users(telegram_id)
                          )''')
        cursor.execute('''select row_number() over (order by id), ticker, price, supply, id
                                from portfolio
                                where r_telegram_id = ?
                                ''',
                       (self.telegram_id,))
        result = cursor.fetchall()
        conn.close()
        return result

    def update_supply_chosen_asset(self, chosen_row, chosen_value):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''update portfolio
                                set supply = ?
                                where id = ?
                                and r_telegram_id = ?
                                ''',
                       (chosen_value, chosen_row, self.telegram_id,))
        conn.commit()
        conn.close()

    def update_price_chosen_asset(self, chosen_row, chosen_value):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''update portfolio
                                set price = ?
                                where id = ?
                                and r_telegram_id = ?
                                ''',
                       (chosen_value, chosen_row, self.telegram_id,))
        conn.commit()
        conn.close()

    def delete_row_chosen_asset(self, chosen_row):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''delete from portfolio
                                where id = ?
                                and r_telegram_id = ?
                                ''',
                       (chosen_row, self.telegram_id,))
        conn.commit()
        conn.close()


class Asset:
    def __init__(self, ticker, price, supply, telegram_id) -> None:
        self.ticker = ticker
        self.price = price
        self.supply = supply
        self.r_telegram_id = telegram_id

    def add_asset(self):
        inserted_id = None
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''create table if not exists portfolio (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          ticker TEXT,
                          price REAL,
                          supply real,
                          r_telegram_id INTEGER,
                          FOREIGN KEY(r_telegram_id) REFERENCES users(telegram_id)
                          )''')
        cursor.execute('insert into portfolio (ticker, price, supply, r_telegram_id) values (?,?,?,?)',
                       (self.ticker, self.price, self.supply, self.r_telegram_id))
        conn.commit()
        inserted_id = cursor.lastrowid
        conn.close()
        return inserted_id


def check_connection():
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    session = Session()
    session.headers.update(api_config.headers)
    response = session.get(url, params=api_config.parameters)

    if response.status_code == 200:
        data = json.loads(response.text).get('data')
        return data
    else:
        return None


def check_asset_existence(asset_name, data):
    b = []
    for i in range(len(data)):
        if data[i].get('symbol') == asset_name:
            b.append(i)
    if not b:
        return None
    else:
        return b[0]


def get_asset_price(data, asset_name):
    for i in range(len(data)):
        if data[i].get('symbol') == asset_name:
            asset_price = round(data[i].get('quote').get('USD').get('price'), 2)
            return asset_price


def actual_portfolio_price(data):
    asset_list = []
    for row in data:
        asset_list.append(row[2])

    asset_prices = []
    actual_data = check_connection()
    for asset in asset_list:
        asset_prices.append(get_asset_price(actual_data, asset))
    return asset_prices


def check_portfolio_text(data, actual_asset_prices):
    actual_sum = 0
    buy_sum = []
    for i in range(len(data)):
        actual_sum += data[i][1] * actual_asset_prices[i]
        buy_sum.append(data[i][1] * data[i][0])
    text = (f"Ваш портфель: {round(actual_sum, 2)} $" +
            f" / {round(((actual_sum - sum(buy_sum)) / sum(buy_sum))*100, 2)}% \n")
    for i in range(len(data)):
        actual_sum_asset = data[i][1] * actual_asset_prices[i]
        buy_sum_asset = data[i][1] * data[i][0]
        text += (
                f"{round(data[i][1], 2)} {data[i][2]} на сумму {round(actual_sum_asset)} "
                "USD / " + f"{round(((actual_sum_asset - buy_sum_asset) / actual_sum_asset) * 100,2)} % \n")
    return text


def all_user_added_assets_to_str(data):
    text = ''
    for row in data:
        text += f"{row[0]}. {row[3]} {row[1]} по цене {row[2]} USD\n"
    return text


def user_chosen_asset_for_edit(data):
    text = f"{data[0]}. {data[3]} {data[1]} по цене {data[2]} USD\n"
    return text


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user = User(message.from_user.id)
    if user.check_user_record() is None:
        user.create_user_record()
    await message.reply('Привет! Я бот "трекер криптопортфеля"! \n'
                        "/info - узнать что я умею")


@dp.message_handler(commands=['info'])
async def info_command(message: types.Message):
    await message.answer("Info: \n"
                         "/checkCurrency - узнать стоимость криптоактива\n"
                         "Работа с портфелем:\n "
                         "/checkPortfolio - просмотреть текущий портфель\n"
                         "/addCurrency - добавить новый актив\n"
                         "/deleteCurrency - удалить актив\n"
                         "/editCurrency - редактировать актив"
                         )


@dp.message_handler(commands=['checkCurrency'])
async def check_command(message: types.Message, state: FSMContext):
    await bot.send_message(message.chat.id, 'Введите идентификатор актива')
    await state.set_state(AssetStates.asset_check_name.state)


@dp.message_handler(state=AssetStates.asset_check_name)
async def check_command(message: types.Message, state: FSMContext):
    asset_name = message.text.upper()
    data = check_connection()
    if data is None:
        await bot.send_message(message.chat.id, 'Не удалось сделать запрос, попробуйте снова\n'
                                                '/checkCurrency')
        await state.finish()
    elif check_asset_existence(asset_name, data) is None:
        await bot.send_message(message.chat.id, 'Не удалось найти указанный тикер актива, попробуйте снова \n'
                                                '/checkCurrency')
        await state.finish()
    else:
        await bot.send_message(message.chat.id,
                               "Стоимость актива " + asset_name + " - " + str(
                                   get_asset_price(data, asset_name)) + " $")
        await state.finish()


@dp.message_handler(commands=['addCurrency'])
async def add_command(message: types.Message, state: FSMContext):
    await bot.send_message(message.chat.id, 'Введите идентификатор актива')
    await state.set_state(AssetStates.asset_add_currency.state)


@dp.message_handler(state=AssetStates.asset_add_currency)
async def add_command(message: types.Message, state: FSMContext):
    await state.update_data(chosen_asset=message.text.upper())
    asset_name = message.text.upper()
    data = check_connection()
    asset_index = check_asset_existence(asset_name, data)
    if data is None:
        await bot.send_message(message.chat.id, 'Не удалось сделать запрос, попробуйте снова\n'
                                                '/addCurrency')
        await state.finish()
    elif asset_index is None:
        await bot.send_message(message.chat.id, 'Не удалось найти указанный тикер актива, попробуйте снова\n'
                                                '/addCurrency')
        await state.finish()
    else:
        await bot.send_message(message.chat.id, 'Введите количество актива')
        await state.update_data(index=asset_index)
        await state.update_data(inf=data)
        await state.set_state(AssetStates.asset_supply.state)


@dp.message_handler(state=AssetStates.asset_supply)
async def add_command(message: types.Message, state: FSMContext):
    try:
        await state.update_data(chosen_supply=float(message.text))
        await bot.send_message(message.chat.id, 'Введите стоимость покупки актива за 1 единицу в $\n'
                                                'Добавить актив по текущей стоимости - '
                                                'введите 0')
        await state.set_state(AssetStates.asset_price.state)
    except ValueError:
        await bot.send_message(message.chat.id, 'Введите количество актива числом. Пример  = "1.01" \n'
                                                '/addCurrency попробуйте снова')
        await state.finish()


@dp.message_handler(state=AssetStates.asset_price)
async def add_command(message: types.Message, state: FSMContext):
    try:
        await state.update_data(chosen_price=float(message.text))
        user_asset = await state.get_data()
        if user_asset.get('chosen_price') == 0:
            asset_price = round(user_asset.get('inf')[user_asset.get('index')].get('quote').get('USD').get('price'), 2)
            asset = Asset(user_asset.get('chosen_asset'), asset_price,
                          user_asset.get('chosen_supply'), message.from_user.id)
            asset.add_asset()
        else:
            asset_price = user_asset.get('chosen_price')
            asset = Asset(user_asset.get('chosen_asset'), asset_price,
                          user_asset.get('chosen_supply'), message.from_user.id)
            asset.add_asset()

        user = User(message.from_user.id)
        added_asset = user.last_added_asset()
        await bot.send_message(message.chat.id,
                               'Вы добавили ' + str(added_asset[2]) + ' ' + str(added_asset[0])
                               + ' на общую стоимость ' + str(round(added_asset[2] * added_asset[1], 2))
                               + ' $ в портфель! \n'
                                 '/checkPortfolio посмотреть свой текущий портфель\n'
                                 '/addCurrency добавить еще один актив в портфель\n'
                                 '/deleteCurrency удалить актив из портфеля\n'
                                 '/editCurrency изменить добавленный актив')
        await state.finish()
    except ValueError:
        await bot.send_message(message.chat.id, 'Введите количество актива числом. Пример  = "1.01"\n'
                                                '/addCurrency попробуйте снова')
        await state.finish()
    finally:
        await state.finish()


@dp.message_handler(commands=['checkPortfolio'])
async def add_command(message: types.Message):
    user = User(message.from_user.id)
    data = user.check_portfolio()
    if len(data) == 0:
        await bot.send_message(message.chat.id, 'Ваш портфель пуст!\n'
                                                '/addCurrency добавить новый актив')
    else:
        actual_asset_prices = actual_portfolio_price(data)
        text = check_portfolio_text(data, actual_asset_prices)
        await bot.send_message(message.chat.id, text)


@dp.message_handler(commands=['deleteCurrency'])
async def check_command(message: types.Message, state: FSMContext):
    await bot.send_message(message.chat.id, 'Введите идентификатор актива')
    await state.set_state(AssetStates.asset_delete_currency.state)


@dp.message_handler(state=AssetStates.asset_delete_currency)
async def check_command(message: types.Message, state: FSMContext):
    user = User(message.from_user.id)
    data = user.check_portfolio()
    if data is None:
        await bot.send_message(message.chat.id, 'Ваш портфель пуст!\n'
                                                '/addCurrency добавить новый актив')
        await state.finish()
    else:
        await state.update_data(chosen_asset=message.text.upper())
        asset = await state.get_data()
        data = user.check_asset_in_portfolio(asset.get('chosen_asset'))
        if data is None:
            await bot.send_message(message.chat.id, f"Актива {asset.get('chosen_asset')} в вашем портфеле нет!\n"
                                                    f"/checkPortfolio")
            await state.finish()
        else:
            user.delete_asset_from_portfolio(asset.get('chosen_asset'))
            await bot.send_message(message.chat.id, f"Актив {asset.get('chosen_asset')} удален из вашего портфеля!\n"
                                                    f"/checkPortfolio")
            await state.finish()


@dp.message_handler(commands=['editCurrency'])
async def check_command(message: types.Message, state: FSMContext):
    user = User(message.from_user.id)
    data = user.check_all_user_assets()
    if len(data) == 0:
        await bot.send_message(message.chat.id, 'Редактировать нечего, Ваш портфель пуст!\n'
                                                '/addCurrency для добавления актива')
    else:
        text = all_user_added_assets_to_str(data)
        await bot.send_message(message.chat.id, 'Ваши добавленные активы:\n' + text)
        await bot.send_message(message.chat.id, 'Введите номер строки из представленных для редактирования')
        await state.set_state(AssetStates.asset_id_for_edit.state)
        await state.update_data(user_asset_data=data)


@dp.message_handler(state=AssetStates.asset_id_for_edit)
async def check_command(message: types.Message, state: FSMContext):
    try:
        await state.update_data(user_asset_id=int(message.text))
        data = await state.get_data()
        if len(data.get('user_asset_data')) < data.get('user_asset_id'):
            await bot.send_message(message.chat.id, 'Такой строки не существует\n'
                                                    '/editCurrency попробуйте снова')
            await state.finish()
        else:
            output_text = user_chosen_asset_for_edit(data.get('user_asset_data')[data.get('user_asset_id') - 1])
            await bot.send_message(message.chat.id, 'Вы выбрали:\n'
                                   + output_text)
            await bot.send_message(message.chat.id, 'Выберите, что необходимо изменить\n'
                                                    '1 - количество, '
                                                    '2 - цена покупки, '
                                                    '3 - удалить запись')
            await state.set_state(AssetStates.user_action_for_edit.state)
    except ValueError:
        await bot.send_message(message.chat.id, 'Введите номер выбранной записи целым числом. Пример  = "1"\n'
                                                '/editCurrency попробуйте снова')
        await state.finish()


@dp.message_handler(state=AssetStates.user_action_for_edit)
async def check_command(message: types.Message, state: FSMContext):
    try:
        user = User(message.from_user.id)
        await state.update_data(user_action=int(message.text))
        data = await state.get_data()
        if data.get('user_action') not in [1, 2, 3]:
            await bot.send_message(message.chat.id, 'Такое действие не предусмотрено, введите число от 1 до 3\n'
                                                    '/editCurrency попробуйте снова')
            await state.finish()
        elif data.get('user_action') == 3:
            chosen_row = data.get('user_asset_data')[data.get('user_asset_id') - 1][4]
            user.delete_row_chosen_asset(chosen_row)
            await bot.send_message(message.chat.id, 'Строка удалена!\n'
                                                    '/checkPortfolio посмотреть свой текущий портфель')
            await state.finish()
        else:
            await bot.send_message(message.chat.id, 'Введите необходимое значение')
            await state.set_state(AssetStates.user_value_for_edit.state)
    except ValueError:
        await bot.send_message(message.chat.id, 'Введите номер выбранной записи целым числом. Пример  = "1"\n'
                                                '/editCurrency попробуйте снова')
        await state.finish()


@dp.message_handler(state=AssetStates.user_value_for_edit)
async def check_command(message: types.Message, state: FSMContext):
    try:
        await state.update_data(user_value=float(message.text))
        user = User(message.from_user.id)
        data = await state.get_data()
        chosen_row = data.get('user_asset_data')[data.get('user_asset_id') - 1][4]
        chosen_value = data.get('user_value')
        if data.get('user_action') == 1:
            user.update_supply_chosen_asset(chosen_row, chosen_value)
            await bot.send_message(message.chat.id, 'Значение обновлено!\n'
                                                    '/checkPortfolio посмотреть свой текущий портфель')
            await state.finish()
        else:
            user.update_price_chosen_asset(chosen_row, chosen_value)
            await bot.send_message(message.chat.id, 'Значение обновлено!\n'
                                                    '/checkPortfolio посмотреть свой текущий портфель\n'
                                                    '/addCurrency - добавить новый актив')
            await state.finish()
    except ValueError:
        await bot.send_message(message.chat.id, 'Введите номер выбранной записи целым числом. Пример  = "1"\n'
                                                '/editCurrency попробуйте снова')
        await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
