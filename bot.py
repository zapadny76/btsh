import logging
import qrcode
from telegram import ForceReply, Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from datetime import datetime
from utils import load_data, save_data

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Установите более высокий уровень логирования для httpx, чтобы избежать логирования всех GET и POST запросов
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Путь к JSON-файлам
USERS_FILE = 'users.json'
METER_DATA_FILE = 'meter_data.json'

# Состояния разговора
REGISTER, RECORD_METER_DATA, ENTER_COLD_WATER, ENTER_HOT_WATER = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отправьте сообщение при выполнении команды /start."""
    user = update.effective_user
    user_id = user.id
    users = load_data(USERS_FILE)

    await update.message.reply_text(
        'Здравствуйте! Вас приветствует телеграмм бот ЖСК Западный для передачи показаний счетчиков воды.'
    )

    if str(user_id) in users:
        meter_data = load_data(METER_DATA_FILE)
        if str(user_id) in meter_data and meter_data[str(user_id)]:
            last_entry = meter_data[str(user_id)][-1]
            await update.message.reply_text(
                f'Предыдущие показания счетчиков:\n'
                f'Холодная вода: {last_entry["cold_water"]}\n'
                f'Горячая вода: {last_entry["hot_water"]}\n'
                f'Дата: {last_entry["date"]}'
            )

        await update.message.reply_text(
            f'Вы уже зарегистрированы с номером квартиры {users[str(user_id)]}. '
            'Теперь вы можете ввести данные по показаниям счетчиков воды. '
            'Отправьте данные в формате: "холодная_вода горячая_вода".'
        )
        return RECORD_METER_DATA
    else:
        await update.message.reply_html(
            rf"Hi {user.mention_html()}! Отправьте ваш номер квартиры для регистрации.",
            reply_markup=ForceReply(selective=True),
        )
        return REGISTER

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправьте сообщение при выполнении команды /help."""
    await update.message.reply_text("Help!")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Зарегистрируйте пользователя с его номером квартиры."""
    user_id = update.message.from_user.id
    apartment_number = update.message.text

    try:
        apartment_number = int(apartment_number)
        if 129 <= apartment_number <= 255:
            users = load_data(USERS_FILE)
            if str(user_id) in users:
                meter_data = load_data(METER_DATA_FILE)
                if str(user_id) in meter_data and meter_data[str(user_id)]:
                    last_entry = meter_data[str(user_id)][-1]
                    await update.message.reply_text(
                        f'Предыдущие показания счетчиков:\n'
                        f'Холодная вода: {last_entry["cold_water"]}\n'
                        f'Горячая вода: {last_entry["hot_water"]}\n'
                        f'Дата: {last_entry["date"]}'
                    )

                await update.message.reply_text(
                    f'Вы уже зарегистрированы с номером квартиры {users[str(user_id)]}. '
                    'Теперь вы можете ввести данные по показаниям счетчиков воды. '
                    'Отправьте данные в формате: "холодная_вода горячая_вода".'
                )
                return RECORD_METER_DATA
            else:
                users[str(user_id)] = apartment_number
                save_data(USERS_FILE, users)
                await update.message.reply_text(f'Вы успешно зарегистрированы с номером квартиры {apartment_number}.')
                await update.message.reply_text('Теперь вы можете ввести данные по показаниям счетчиков воды. Отправьте данные в формате: "холодная_вода горячая_вода".')
                return RECORD_METER_DATA
        else:
            await update.message.reply_text('Номер квартиры должен быть в диапазоне от 129 до 255. Пожалуйста, попробуйте снова.')
            return REGISTER
    except ValueError:
        await update.message.reply_text('Номер квартиры должен быть целым числом. Пожалуйста, попробуйте снова.')
        return REGISTER

async def record_meter_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запишите данные счетчиков для пользователя."""
    user_id = update.message.from_user.id
    message_text = update.message.text

    users = load_data(USERS_FILE)
    if str(user_id) not in users:
        await update.message.reply_text('Вы не зарегистрированы. Пожалуйста, отправьте ваш номер квартиры для регистрации.')
        return REGISTER

    try:
        cold_water, hot_water = map(int, message_text.split())
    except ValueError:
        await update.message.reply_text('Пожалуйста, отправьте данные в формате: "холодная_вода горячая_вода". Показания должны быть только цифрами.')
        return RECORD_METER_DATA

    meter_data = load_data(METER_DATA_FILE)
    if str(user_id) in meter_data:
        last_entry = meter_data[str(user_id)][-1]
        if cold_water < last_entry["cold_water"] or hot_water < last_entry["hot_water"]:
            await update.message.reply_text('Введенные показания счетчиков должны быть больше или равны предыдущим показаниям. Пожалуйста, проверьте данные и попробуйте снова.')
            return RECORD_METER_DATA

        cold_water_diff = cold_water - last_entry["cold_water"]
        hot_water_diff = hot_water - last_entry["hot_water"]
        await update.message.reply_text(
            f'Изменения по сравнению с предыдущими показаниями:\n'
            f'Холодная вода: +{cold_water_diff}\n'
            f'Горячая вода: +{hot_water_diff}'
        )

    apartment_number = users[str(user_id)]
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if str(user_id) not in meter_data:
        meter_data[str(user_id)] = []

    meter_data[str(user_id)].append({
        "apartment_number": apartment_number,
        "date": date,
        "cold_water": cold_water,
        "hot_water": hot_water
    })

    save_data(METER_DATA_FILE, meter_data)

    await update.message.reply_text(f'Данные по счетчикам воды успешно сохранены для квартиры {apartment_number} на {date}.')

    # Завершение сеанса работы с пользователем
    await update.message.reply_text('Спасибо за использование нашего бота!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def generate_qr_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создайте QR-код для поиска бота и сохраните его в файле qr.png."""
    # Создание QR-кода
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data('https://t.me/your_bot_username')  # Замените на ваш username бота
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("qr.png")

    # Отправка QR-кода
    with open("qr.png", "rb") as photo:
        await update.message.reply_photo(photo, caption="QR-код для поиска бота успешно создан и сохранен в файле qr.png.")

def start_bot(token: str) -> None:
    """Запустите бота."""
    # Создайте приложение и передайте ему токен вашего бота.
    application = Application.builder().token(token).build()

    # Обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register)],
            RECORD_METER_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, record_meter_data)],
        },
        fallbacks=[CommandHandler("help", help_command)],
        per_user=True,  # Устанавливаем per_user=True для отслеживания состояния для каждого пользователя
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("qr", generate_qr_code))

    # Запустите бота до тех пор, пока пользователь не нажмет Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
