import json
from datetime import datetime
from pathlib import Path

import telebot
from pybooru import Danbooru
from danbooru_checker import DanbooruChecker

from dotenv import load_dotenv
from os import getenv

load_dotenv()
admin = getenv('ADMIN')  # Chat id of admin
token = getenv('TOKEN')  # Telegram bot token
booru_login = getenv('BOORU_LOGIN')  # Danbooru login
booru_api = getenv('BOORU_API')  # Danbooru api key
telegram_channel_id = getenv('TELEGRAM_CHANNEL_ID')  # ID of telegram channel

bot = telebot.TeleBot(token)
client = Danbooru('danbooru')


@bot.message_handler(commands=['start'])
def get_text_messages(message):
    chat = message.chat.id
    bot.send_message(chat, 'Welcome! \n'
                           'To start using bot add your tags by using command /add')

    try:
        with open(f'users_tags/{chat}.json', 'r') as json_file:
            tags = json.load(json_file)

        tag_list = '\n'.join(tags.keys())
        bot.send_message(chat, f'You already have next tags:\n{tag_list}')
    except FileNotFoundError:
        with open(f'users_tags/{chat}.json', 'w') as json_file:
            tags = dict()
            json.dump(tags, json_file)


@bot.message_handler(commands=['add'])
def add_new_tag_command(message):
    chat = message.chat.id

    my_file = Path(f'users_tags/{chat}.json')
    if not my_file.is_file():
        bot.send_message(chat, 'Your profile was not found. Create profile by command /start')
        return

    msg = message.text.split()
    if len(msg) == 2:
        add_new_tag(message, some_tag=msg[-1])
    else:
        bot.reply_to(message, 'Write new tag to check on updates')
        bot.register_next_step_handler(message, add_new_tag)


def add_new_tag(message, some_tag=None):
    chat = message.chat.id
    if message.content_type != 'text':
        bot.send_message(chat, 'Wrong content type. Repeat /add command')
        return

    with open(f'users_tags/{chat}.json', 'r') as json_file:
        tags = json.load(json_file)

    if some_tag:
        new_tag = some_tag.lower()
    else:
        new_tag = message.text.lower()

    if new_tag in tags.keys():
        bot.send_message(chat, 'Tag already added')
        return

    try:
        new_tag_last_post = client.post_list(limit=1, tags=new_tag)[0]
    except IndexError:
        bot.send_message(chat, 'Wrong tag. Repeat /add command')
        return

    last_post_created_at = new_tag_last_post.get('created_at')
    tags[new_tag] = last_post_created_at if last_post_created_at else datetime.now()

    with open(f'users_tags/{chat}.json', 'w') as json_file:
        json.dump(tags, json_file)
    bot.send_message(chat, 'Tag added successfully')


@bot.message_handler(commands=['delete'])
def delete_tag_command(message):
    chat = message.chat.id

    try:
        with open(f'users_tags/{chat}.json', 'r') as json_file:
            tags = json.load(json_file)

        tag_list = '\n'.join(map(lambda x: f'<{x}>', tags.keys()))
        bot.reply_to(message, f'Your list of tags:\n{tag_list}.\nWrite tag to delete')
        bot.register_next_step_handler(message, delete_tag, tags)

    except FileNotFoundError:
        bot.send_message(chat, 'Your profile was not found. Create profile by command /start')


def delete_tag(message, tags):
    chat = message.chat.id
    tag_to_delete = message.text
    if not tags.pop(tag_to_delete, None):
        bot.send_message(chat, 'Tag was not found in your list')
        return

    with open(f'users_tags/{chat}.json', 'w') as json_file:
        json.dump(tags, json_file)
    bot.send_message(chat, 'Tag deleted successfully')


@bot.message_handler(commands=['check'])
def check_for_updates_command(message):
    chat = message.chat.id

    my_file = Path(f'users_tags/{chat}.json')
    if not my_file.is_file():
        bot.reply_to(message, 'Your profile was not found. Create profile by command /start')
        return

    with open(my_file, 'r') as json_file:
        tags = json.load(json_file)

    tags_list = list(tags.keys())
    if not tags_list:
        bot.reply_to(message, 'You dont have tags to check on updates. Add them using command /add')
        return

    new_pictures = []
    for tag in tags_list:
        posts = client.post_list(limit=25, tags=tag)
        post_list = [x for x in posts
                     if datetime.fromisoformat(x['created_at']) > datetime.fromisoformat(tags[tag])]

        if not post_list:
            continue

        tags[tag] = str(max(datetime.fromisoformat(d['created_at']) for d in posts))
        for post in reversed(post_list):
            url = post.get('file_url')
            if url not in new_pictures:
                new_pictures.append(url)

    if not new_pictures:
        bot.reply_to(message, 'No updates')
        return

    for url in new_pictures:
        if url:
            bot.send_message(chat, url)


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id,
                     'This is Danbooru updates checker bot.\n'
                     'Using this bot you can check on new posts in Danbooru by your favorite tags.'
                     'Add new tags (e.g. 1girl, fate(series), 92m, makise_kurisu), then bot can send you updates of '
                     'this tags')


c1 = telebot.types.BotCommand(command='start', description='Create profile')
c2 = telebot.types.BotCommand(command='add', description='Add new tag')
c3 = telebot.types.BotCommand(command='delete', description='Delete tag')
c4 = telebot.types.BotCommand(command='check', description='Check new posts for your tags')
bot.set_my_commands([c1, c2, c3, c4])
bot.set_chat_menu_button(menu_button=telebot.types.MenuButtonCommands('commands'))

bot.infinity_polling()
