import os
from dotenv import load_dotenv

load_dotenv()

parameters = {
    'start': '1',
    'limit': '30',
    'convert': 'USD'
}
headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': os.getenv('API_TOKEN'),
}
