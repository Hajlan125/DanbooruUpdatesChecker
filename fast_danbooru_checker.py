import asyncio
import copy
import itertools
import json
import aiohttp
import prettytable as pt
from datetime import datetime


class FastDanbooruChecker:
    def __init__(self, login: str = None, api_key: str = None, banned_tag: str = None):
        if (login is None and api_key is not None) or (login is not None and api_key is None):
            raise ValueError("Need login and api key or neither")

        self.login = login
        self.api_key = api_key
        self.banned_tag = banned_tag

    async def get_updates(self, tags_path: str, limit=50) -> list:
        try:
            with open(tags_path, 'r') as f:
                tags = json.load(f)
        except FileNotFoundError:
            raise

        upd_tags_dates = tags

        if not tags:
            print('No tags')
            # return []
            raise Exception("Tags was not found. Check your tags path")

        unseen_posts = []
        tasks = []
        site = 'https://danbooru.donmai.us/posts.json'
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(value=10)  # change if needed
            for tag, last_check in tags.items():
                tasks.append(self.danbooru_request(site=site, tag=tag, last_check=last_check,
                                                   session=session, limit=limit, tags_to_upd=upd_tags_dates,
                                                   semaphore=sem))
                # updates = await self.danbooru_request (site, params=params, session=session)

            htmls = await asyncio.gather(*tasks, return_exceptions=False)
            updates = list(itertools.chain(*htmls))

            for post in updates:
                post_id = post.get('id')

                url = self.get_post_url_under_five_mb(post)

                if url not in map(lambda x: x[1], unseen_posts):
                    unseen_posts.append((post_id, url))

        with open(tags_path, 'w') as json_file:
            json.dump(upd_tags_dates, json_file)

        return unseen_posts

    async def danbooru_request(self, tag: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore,
                               last_check: str = None, tags_to_upd: dict = None, limit: int = 50, site: str = None,
                               retries: int = 0):
        if not site:
            site = 'https://danbooru.donmai.us/posts.json'

        auth = aiohttp.BasicAuth(self.login, self.api_key) if self.login else None

        edited_tag = copy.deepcopy(tag)
        if tag == ' ':
            edited_tag = ''

        if last_check:
            edited_date = 'date:>' + last_check[:-9] + '999'
            edited_tag += f' {edited_date}'

        if self.banned_tag:
            edited_tag += f' -{self.banned_tag}'

        params = {
            'tags': edited_tag,
            'limit': limit
        }

        async with semaphore:
            if retries == 3:
                return []

            resp = await session.request(method='GET', url=site, params=params, auth=auth)

            if not resp.ok:
                data = await self.danbooru_request(site=site, tag=tag, last_check=last_check,
                                                   session=session, limit=limit,
                                                   semaphore=semaphore, retries=retries + 1)
            else:
                data = await resp.json()

        if tags_to_upd and data:
            tags_to_upd[tag] = max(data, key=lambda x: int(x['id']))['created_at']

        return data

    async def add_new_tag(self, tags_path, new_tag):
        try:
            with open(tags_path, 'r') as file:
                tags = json.load(file)
        except ValueError:
            tags = dict()
        except FileNotFoundError:
            raise

        if new_tag in tags.keys():
            return False, 'Tag already added'

        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore()
            last_post_list = await self.danbooru_request(tag=new_tag, limit=1, session=session, semaphore=sem)

        if not last_post_list:
            return False, 'Tag was not found'

        tags[new_tag] = last_post_list[0]['created_at']

        with open(tags_path, 'w') as file:
            json.dump(tags, file)

        return True, 'Tag added successfully'

    @staticmethod
    def delete_tag(tags_path, tag) -> (bool, str):
        try:
            with open(tags_path, 'r') as f:
                tags = json.load(f)
        except FileNotFoundError:
            raise

        if not tags.pop(tag, None):
            return False, 'The tag has not been deleted, it may not be in the list'

        with open(tags_path, 'w') as file:
            json.dump(tags, file)

        return True, 'Tag successfully deleted'

    async def post_show(self, post_id: int) -> dict:
        site = f'https://danbooru.donmai.us/posts/{post_id}.json'
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore()
            post = await self.danbooru_request(site=site, tag=' ', session=session, semaphore=sem)
        return post[-1]

    @staticmethod
    def show_tag_list(tags_path):
        try:
            with open(tags_path, 'r') as f:
                tags = json.load(f)
        except FileNotFoundError:
            raise
        return sorted(list(tags.keys()))

    @staticmethod
    def show_tags_table(tags_path):
        try:
            with open(tags_path, 'r') as f:
                tags: dict = json.load(f)
        except FileNotFoundError:
            raise

        table = pt.PrettyTable(['Tag', 'Last check'])
        table.align['Tag'] = 't'
        table.align['Last check'] = 'l'

        for tag, last_check in sorted(tags.items()):
            lst = datetime.fromisoformat(last_check)

            table.add_row([tag, f'{lst.hour}:{lst.minute} {lst.day}.{lst.month}.{lst.year}'])

        return table

    @staticmethod
    def get_post_url_under_five_mb(danbooru_post_json: dict):
        size = int(danbooru_post_json.get('file_size'))

        if (size > 4_999_999 or
                int(danbooru_post_json.get('image_width')) + int(danbooru_post_json.get('image_height')) >= 10000):
            url = danbooru_post_json.get('large_file_url', danbooru_post_json.get('file_url'))
        else:
            url = danbooru_post_json.get('file_url')

        return url
