import os
from dotenv import load_dotenv
from bot import start_bot

# Загрузите переменные среды из файла .env
load_dotenv()

# Получите токен из переменной среды
TOKEN = os.getenv("TOKEN")

if __name__ == "__main__":
    start_bot(TOKEN)
