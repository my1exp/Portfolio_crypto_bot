from requests import Session
from aiogram import Bot, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import json

bot = Bot(token="6634602106:AAFfXFv-euy1IoWWj3eBNB7VGmW_Jce8asM")

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

parameters = {
    'start': '1',
    'limit': '30',
    'convert': 'USD'
}
headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': '7e11e445-d09a-474d-86c4-bdfd20f3b094',
}


class AssetStates(StatesGroup):
    asset_check_name = State()
    asset_add_currency = State()
    asset_supply = State()


class User:
    def __init__(self, telegram_id) -> None:
        self.telegram_id = telegram_id

    def checkUserRecord(self):
        conn = sqlite3.connect('C:\\Users\\Nikita\\IdeaProjects\\bot_test_1\db.db')
        cursor = conn.cursor()
        cursor.execute('create table if not exists users (telegram_id INTEGER primary key)')
        cursor.execute('select * from users where telegram_id = ?', (self.telegram_id,))
        result = cursor.fetchone()
        return result

    def createUserRecord(self):
        inserted_id = None
        conn = sqlite3.connect('C:\\Users\\Nikita\\IdeaProjects\\bot_test_1db.db')
        cursor = conn.cursor()
        cursor.execute('create table if not exists users (telegram_id INTEGER primary key)')
        cursor.execute('insert into users (telegram_id) values (?)', (self.telegram_id,))
        conn.commit()
        inserted_id = cursor.lastrowid
        conn.close()
        return inserted_id

    def checkPortfolio(self):
        conn = sqlite3.connect('C:\\Users\\Nikita\\IdeaProjects\\bot_test_1\\db.db')
        cursor = conn.cursor()
        cursor.execute('''create table if not exists portfolio (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          ticker TEXT,
                          price REAL,
                          supply real,
                          r_telegram_id INTEGER,
                          FOREIGN KEY(r_telegram_id) REFERENCES users(telegram_id)
                          )''')
        cursor.execute('''select round(avg(price),4), sum(price), sum(supply), ticker
                               from portfolio where r_telegram_id = ?
                               group by ticker''',
                       (self.telegram_id,))
        result = cursor.fetchall()
        return result


class Asset:
    def __init__(self, ticker, price, supply, telegram_id) -> None:
        self.ticker = ticker
        self.price = price
        self.supply = supply
        self.r_telegram_id = telegram_id

    def addCurrency(self):
        inserted_id = None
        conn = sqlite3.connect('C:\\Users\\Nikita\\IdeaProjects\\bot_test_1\\db.db')
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


def checkConnection():
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    session = Session()
    session.headers.update(headers)
    response = session.get(url, params=parameters)

    if response.status_code == 200:
        data = json.loads(response.text).get('data')
        return data
    else:
        return None


def checkAssetExistance(asset_name, data):
    b = []
    for i in range(len(data)):
        if data[i].get('symbol') == asset_name:
            b.append(i)
    if not b:
        return None
    else:
        return b[0]


def getAssetPrice(data, asset_name):
    for i in range(len(data)):
        if data[i].get('symbol') == asset_name:
            asset_price = round(data[i].get('quote').get('USD').get('price'), 2)
            return asset_price


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user = User(message.from_user.id)
    if user.checkUserRecord() is None:
        user.createUserRecord()
    await message.reply('Привет! Я бот "трекер криптопортфеля"! \n'
                        "/info - узнать что я умею")


@dp.message_handler(commands=['info'])
async def info_command(message: types.Message):
    await message.answer("Info: \n "
                         "/checkCurrency - узнать стоимость криптоактива\n"
                         "Работа с портфелем:\n"
                         "/checkPortfolio - просмотреть текущий портфель\n"
                         "/addCurrency - добавить новый актив\n"
                         "/deleteCurrency - удалить актив\n"
                         "/editCurrency - редактировать актив\n"
                         "Настройка уведомлений\n"
                         "/notifications - настроить уведомления"
                         )


@dp.message_handler(commands=['checkCurrency'])
async def check_command(message: types.Message, state: FSMContext):
    await bot.send_message(message.chat.id, 'Введите идентификатор актива')
    await state.set_state(AssetStates.asset_check_name.state)


@dp.message_handler(state=AssetStates.asset_check_name)
async def check_command(message: types.Message, state: FSMContext):
    asset_name = message.text.upper()
    data = checkConnection()
    if data is None:
        await bot.send_message(message.chat.id, 'Не удалось сделать запрос, попробуйте снова')
        await state.finish()
    elif checkAssetExistance(asset_name, data) is None:
        await bot.send_message(message.chat.id, 'Не удалось найти указанный тикер актива, попробуйте снова')
        await state.finish()
    else:
        await bot.send_message(message.chat.id,
                               "Стоимость актива " + asset_name + " - " + str(getAssetPrice(data, asset_name)) + " USD")
        await state.finish()


@dp.message_handler(commands=['addCurrency'])
async def add_command(message: types.Message, state: FSMContext):
    await bot.send_message(message.chat.id, 'Введите идентификатор актива')
    await state.set_state(AssetStates.asset_add_currency.state)


@dp.message_handler(state=AssetStates.asset_add_currency)
async def add_command(message: types.Message, state: FSMContext):
    await state.update_data(chosen_asset=message.text.upper())  # {'chosen_asset': 'BTC'}
    asset_name = message.text.upper()
    data = checkConnection()
    asset_index = checkAssetExistance(asset_name, data)
    if data is None:
        await bot.send_message(message.chat.id, 'Не удалось сделать запрос, попробуйте снова')
        await state.finish()
    elif asset_index is None:
        await bot.send_message(message.chat.id, 'Не удалось найти указанный тикер актива, попробуйте снова')
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
        user_asset = await state.get_data()
        print(user_asset.get('inf')[user_asset.get('index')].get('quote').get('USD').get('price'))
        asset_price = round(user_asset.get('inf')[user_asset.get('index')].get('quote').get('USD').get('price'), 2)
        asset = Asset(user_asset.get('chosen_asset'), asset_price,
                      user_asset.get('chosen_supply'), message.from_user.id)
        asset.addCurrency()
        await bot.send_message(message.chat.id,
                               'Вы добавили ' + str(user_asset.get('chosen_supply')) + ' ' + str(
                                   user_asset.get('chosen_asset'))
                               + ' на общую стоимость ' + str(
                                   round(float(user_asset.get('chosen_supply')) * asset_price, 2))
                               + ' USD в портфель! \n'
                                 'Выберите /checkPortfolio чтобы посмотреть свой текущий портфель\n'
                                 'Выберите /addCurrency чтобы добавить еще один актив в портфель')
        # await state.finish()
    except ValueError:
        await bot.send_message(message.chat.id, 'Введите количество актива числом. Пример  = "1.01"\n'
                                                '/addCurrency попробуйте снова')
        await state.finish()
    finally:
        await state.finish()


@dp.message_handler(commands=['checkPortfolio'])  # сделать запрос, распарсить для каждой монеты
async def add_command(message: types.Message):
    user = User(message.from_user.id)
    data = user.checkPortfolio()
    sum = 0
    for row in data:
        sum += float(row[1]) * float(row[2])
    text = f"Ваш портфель: {round(sum, 2)} USD\n"
    for row in data:
        text += f"{row[2]} {row[3]} на сумму {round(float(row[1]) * float(row[2]), 2)}, средняя {row[0]} \n"
    await bot.send_message(message.chat.id, text)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
