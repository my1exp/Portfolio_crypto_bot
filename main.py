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
    asset_price = State()


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

    def lastAddedAsset(self):
        conn = sqlite3.connect('C:\\Users\\Nikita\\IdeaProjects\\bot_test_1\\db.db')
        cursor = conn.cursor()
        cursor.execute('''select ticker, price, supply, r_telegram_id
                                from(
                                select *, row_number() over (order by id desc) as r_w
                                from portfolio
                                where r_telegram_id = ?)
                                where r_w = 1''',
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


def actualPortfolioPrice(data):
    asset_list = []
    for row in data:
        asset_list.append(row[3])

    asset_prices = []
    actual_data = checkConnection()
    for asset in asset_list:
        asset_prices.append(getAssetPrice(actual_data, asset))
    return asset_prices


def checkPortfoliotext(data, actual_asset_prices):
    actual_sum = 0
    buy_sum = []
    for i in range(len(data)):
        actual_sum += data[i][2] * actual_asset_prices[i]
        buy_sum.append(data[i][2] * data[i][0])

    text = (f"Ваш портфель: {round(actual_sum, 2)} USD" +
            f" / {round((actual_sum - sum(buy_sum)) / sum(buy_sum), 2)}% \n")

    for i in range(len(data)):
        text += (
                f"{round(data[i][2], 2)} {data[i][3]} на сумму {round(float(data[i][2]) * actual_asset_prices[i], 2)} USD / " +
                f"{round((float(data[i][2]) * actual_asset_prices[i] - float(data[i][0]) * float(data[i][2])) / (float(data[i][0]) * float(data[i][2])), 2)}" +
                f"%\n")
    return text


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
    await state.update_data(chosen_asset=message.text.upper())
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
        await bot.send_message(message.chat.id, 'Введите стоимость покупки актива за 1 единицу \n'
                                                'В случае, если вы хотите добавить актив по текущей стоимости - '
                                                'введите 0')
        await state.set_state(AssetStates.asset_price.state)
    except ValueError:
        await bot.send_message(message.chat.id, 'Введите количество актива числом. Пример  = "1.01"\n'
                                                '/addCurrency попробуйте снова')
        await state.finish()


@dp.message_handler(state=AssetStates.asset_price)
async def add_command(message: types.Message, state: FSMContext):
    try:
        await state.update_data(chosen_price=float(message.text))
        user_asset = await state.get_data()
        if user_asset.get('chosen_asset') == 0:
            asset_price = round(user_asset.get('inf')[user_asset.get('index')].get('quote').get('USD').get('price'), 2)
            asset = Asset(user_asset.get('chosen_asset'), asset_price,
                          user_asset.get('chosen_supply'), message.from_user.id)
            asset.addCurrency()
        else:
            asset_price = user_asset.get('chosen_price')
            asset = Asset(user_asset.get('chosen_asset'), asset_price,
                          user_asset.get('chosen_supply'), message.from_user.id)
            asset.addCurrency()

        user = User(message.from_user.id)
        added_asset = user.lastAddedAsset()
        await bot.send_message(message.chat.id,
                               'Вы добавили ' + str(added_asset[0][2]) + ' ' + str(added_asset[0][0])
                               + ' на общую стоимость ' + str(added_asset[0][2] * added_asset[0][1])
                               + ' USD в портфель! \n'
                                 'Выберите /checkPortfolio чтобы посмотреть свой текущий портфель\n'
                                 'Выберите /addCurrency чтобы добавить еще один актив в портфель')
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
    data = user.checkPortfolio()
    actual_asset_prices = actualPortfolioPrice(data)
    text = checkPortfoliotext(data, actual_asset_prices)
    await bot.send_message(message.chat.id, text)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
