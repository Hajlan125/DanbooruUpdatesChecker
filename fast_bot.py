from os import getenv

from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from dotenv import load_dotenv

import asyncio
import logging
import requests

from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.filters.state import StatesGroup, State

from fast_danbooru_checker import FastDanbooruChecker as DanbooruChecker

load_dotenv()
admin = getenv('ADMIN')  # Chat id of bot user
token = getenv('TOKEN')  # Telegram bot token
booru_login = getenv('BOORU_LOGIN')  # Danbooru login
booru_api = getenv('BOORU_API')  # Danbooru api key
telegram_channel_id = getenv('TELEGRAM_CHANNEL_ID')  # ID of telegram channel
tags_path = getenv('TAGS_PATH')

booru = DanbooruChecker(login=booru_login, api_key=booru_api, banned_tag='male_focus')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=token)
dp = Dispatcher()


@dp.message(Command("start"), F.func(lambda message: message.chat.id == int(admin)))
async def cmd_start(message: types.Message):
    await message.reply("Checking for updates...")

    updates = await booru.get_updates(tags_path=tags_path, limit=75)
    updates = sorted(updates)

    for post_id, url in updates:
        if url:
            upd = url + '\n' + f'https://danbooru.donmai.us/posts/{post_id}'
            if telegram_channel_id:
                builder = InlineKeyboardBuilder()
                builder.add(types.InlineKeyboardButton(
                    text="Send",
                    callback_data=f"{post_id}")
                )
                await message.answer(upd, reply_markup=builder.as_markup())
            else:
                await message.answer(upd)

        # time.sleep(0.2)


@dp.callback_query(F.data.isalnum())
async def send_random_value(callback: types.CallbackQuery):
    post_id = callback.data
    site = f'https://danbooru.donmai.us/posts/{post_id}.json'

    post = requests.get(url=site).json()
    url = booru.get_post_url_under_five_mb(post)

    await bot.send_photo(chat_id=telegram_channel_id, photo=url, disable_notification=True)
    # await callback.message.send(callback.data)
    await callback.answer()


class Form(StatesGroup):
    adding_state = State()
    deleting_state = State()


@dp.message(Command('add'), F.func(lambda message: message.chat.id == int(admin)))
async def start(message: types.Message, state: FSMContext):
    await message.answer('Write new tag to check on updates:')
    await state.set_state(Form.adding_state)


@dp.message(Form.adding_state)
async def start(message: types.Message, state: FSMContext):
    success, msg = await booru.add_new_tag(tags_path=tags_path, new_tag=message.text)
    await message.answer(msg)
    await state.clear()


@dp.message(Command('list'))
async def cmd_list(message: types.Message):
    table = booru.show_tags_table(tags_path)
    info = table.paginate(page_length=50, line_break=",").split(',')

    for i in info:
        await message.answer(f'<pre>{i}</pre>', parse_mode=ParseMode.HTML)


@dp.message(Command('delete'))
async def cmd_del(message: types.Message):
    tag = message.text
    status, msg = booru.delete_tag(tags_path=tags_path, tag=tag)
    await message.answer(msg)


async def main():
    bot_commands = [
        BotCommand(command="/start", description="Check for updates"),
        BotCommand(command="/add", description="Add new tag"),
        BotCommand(command="/delete", description="Delete tag"),
        BotCommand(command="/list", description="List of your tags")
    ]
    await bot.set_my_commands(bot_commands)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
