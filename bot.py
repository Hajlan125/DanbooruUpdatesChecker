import time
import telebot
from dotenv import load_dotenv
from os import getenv
from danbooru_checker import DanbooruChecker

load_dotenv()
admin = getenv('ADMIN')  # Chat id of bot user
token = getenv('TOKEN')  # Telegram bot token
booru_login = getenv('BOORU_LOGIN')  # Danbooru login
booru_api = getenv('BOORU_API')  # Danbooru api key
telegram_channel_id = getenv('TELEGRAM_CHANNEL_ID')  # ID of telegram channel

bot = telebot.TeleBot(token)
# old_booru = BooruChecker(login=booru_login, api_key=booru_api, banned_tag='male_focus')
# proxy_booru = BooruApiProxyCalls(proxy_list_path='proxies.csv', tags_path='tags_copy.json',
#                                  login=booru_login, api_key=booru_api)

# booru = DanbooruChecker(tags_path='tags_copy.json', login=booru_login, api_key=booru_api,
#                         proxy_list_path='data/proxies.csv', banned_tag='male_focus')
booru = DanbooruChecker(tags_path='data/tags.json', login=booru_login, api_key=booru_api,
                        proxy_list_path=None, banned_tag='male_focus')


@bot.message_handler(func=lambda message: str(message.chat.id) != admin)
def some(message):
    bot.send_message(message.chat.id, 'NO PERMISSION')


@bot.message_handler(commands=['start'])
def get_text_messages(message):
    bot.reply_to(message, "Checking for updates...")

    # updates = booru.show_booru_tags_updates()
    try:
        updates = booru.get_updates()
    except Exception as exc:
        bot.send_message(message.chat.id, str(exc))
        return
    print(updates)

    for post_id, url in updates:
        if url:
            if telegram_channel_id:
                keyboard = telebot.types.InlineKeyboardMarkup()
                btn = telebot.types.InlineKeyboardButton(text='Send to channel', callback_data=post_id)
                keyboard.add(btn)
                bot.send_message(message.chat.id, url, reply_markup=keyboard)
            else:
                bot.send_message(message.chat.id, url)

        time.sleep(0.2)

    # for index, url in enumerate(updates):
    #     if url:
    #         keyboard = telebot.types.InlineKeyboardMarkup()
    #         btn = telebot.types.InlineKeyboardButton(text='Send to channel', callback_data=str(index))
    #         keyboard.add(btn)
    #
    #         bot.send_message(message.chat.id, url, reply_markup=keyboard)
    #     time.sleep(0.2)


@bot.message_handler(commands=['add'])
def add_new_tag_command(message):
    bot.reply_to(message, 'Write new tag to check on updates')
    bot.register_next_step_handler(message, add_new_tag)


def add_new_tag(message):
    # bot.reply_to(message, booru.add_new_tag(message.text))
    success, msg = booru.add_new_tag(message.text)
    bot.reply_to(message, msg)


@bot.callback_query_handler(func=lambda call: True)
def inline(c):
    post_id = c.data
    post = booru.post_show(post_id)

    url = booru.get_post_url_under_five_mb(post)

    bot.send_photo(telegram_channel_id,
                   url,
                   disable_notification=True)


@bot.message_handler(commands=['delete'])
def delete_tag_command(message):
    bot.reply_to(message, 'Write new tag to check on updates')
    bot.register_next_step_handler(message, delete_tag)


def delete_tag(message):
    success, msg = booru.delete_tag(message.text)
    bot.reply_to(message, msg)


@bot.message_handler(commands=['list'])
def show_tag_list_command(message):
    tag_list = '\n'.join(sorted(booru.show_tag_list()))
    bot.send_message(message.chat.id, f'Tags:\n{tag_list}')


c1 = telebot.types.BotCommand(command='start', description='Check for updates')
c2 = telebot.types.BotCommand(command='add', description='Add new tag')
c3 = telebot.types.BotCommand(command='delete', description='Delete tag')
c4 = telebot.types.BotCommand(command='list', description='Show all tags')
bot.set_my_commands([c1, c2, c3, c4])
bot.set_chat_menu_button(menu_button=telebot.types.MenuButtonCommands('commands'))

while True:
    try:
        bot.polling(non_stop=True, interval=0)
    except Exception as e:
        print(e)
        bot.send_message(chat_id=admin, text=str(e))
        time.sleep(3)
        continue

# bot.infinity_polling(timeout=10, long_polling_timeout=5)
