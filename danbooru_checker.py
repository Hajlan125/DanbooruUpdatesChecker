import csv
import json
import time
import requests
from requests.auth import HTTPBasicAuth


class DanbooruChecker:
    def __init__(self, tags_path, login=None, api_key=None, proxy_list_path=None, banned_tag=None):
        try:
            with open(tags_path, 'r'):
                self.tags_path = tags_path
        except FileNotFoundError:
            raise

        if (login is None and api_key is not None) or (login is not None and api_key is None):
            raise ValueError("Need login and api key or neither")

        self.login = login
        self.api_key = api_key

        self.banned_tag = banned_tag
        self.proxy_list_path = proxy_list_path

        try:
            with open(proxy_list_path, encoding='utf-8') as r_file:
                file_reader = csv.reader(r_file, delimiter=",")
                self.proxy_csv = list(file_reader)
        except FileNotFoundError:
            raise "Proxy list was specified, but file was not found"
        except TypeError:
            pass
        except Exception:
            raise

    def post_list(self, tag: str, date: str = None, limit: int = 25) -> list:
        """
        Returns a list of json objects that store information about each danbooru post founded by specified tag and
        created after specified date

        :param tag: the tag by which the search will be performed
        :param date: parameter for searching for a post later than the specified date
        :param limit: how many posts will be stored in the returned list
        :return: a list of json objects that contains post information
        """
        if tag == ' ':
            tag = ''

        if self.banned_tag:
            tag += f' -{self.banned_tag}'

        if date:
            edited_date = 'date:>' + date[:-8] + '99'
            tag += f' {edited_date}'

        params = {
            'tags': tag,
            'limit': limit
        }

        # call = (f'https://danbooru.donmai.us/posts.json?tags={edited_tag}{edited_date}&limit={limit}'
        #         f'&login={self.login}&api_key={self.api_key}')
        site = 'https://danbooru.donmai.us/posts.json'
        posts = self.danbooru_request(site=site, proxy_path=self.proxy_list_path, params=params)
        return posts

    def post_show(self, post_id: int) -> dict:
        site = f'https://danbooru.donmai.us/posts/{post_id}.json'

        post = self.danbooru_request(site=site, proxy_path=self.proxy_list_path)
        return post

    def danbooru_request(self, site, proxy_path, params=None):
        auth = HTTPBasicAuth(self.login, self.api_key) if self.login else None
        if proxy_path:
            for proxy in self.proxy_csv:
                current_proxy = {
                    'http': proxy[0],
                    'https': proxy[0]
                }
                try:
                    response = requests.get(site, params=params, proxies=current_proxy, auth=auth)
                    if not response.ok:
                        continue
                    break
                except requests.exceptions.ConnectionError:
                    continue
            else:
                # print("NO PROXY")
                return []
        else:
            try:
                response = requests.get(site, params=params, auth=auth)
                if not response.ok:
                    return []
            except requests.exceptions.ConnectionError:
                return []

        posts = response.json()
        return posts

    def get_updates(self):
        with open(self.tags_path, 'r') as json_file:
            tags = json.load(json_file)

        if not tags:
            return []

        unseen_posts = []
        for tag, last_check in tags.items():
            updates = self.post_list(tag=tag, date=last_check)

            if not updates:
                continue

            print(f'<<{tag}>> -- {len(updates)} posts')

            tags[tag] = max(updates, key=lambda x: int(x['id']))['created_at']

            for post in updates:
                post_id = post.get('id')

                url = self.get_post_url_under_five_mb(post)

                if url not in map(lambda x: x[1], unseen_posts):
                    unseen_posts.append((post_id, url))
            time.sleep(2)

        with open(self.tags_path, 'w') as json_file:
            json.dump(tags, json_file)

        return unseen_posts

    def add_new_tag(self, new_tag):
        try:
            with open(self.tags_path, 'r') as file:
                tags = json.load(file)
        except ValueError:
            tags = dict()

        if new_tag in tags.keys():
            return False, 'Tag already added'

        last_post_list = self.post_list(tag=new_tag, limit=1)

        if not last_post_list:
            return False, 'Tag was not found'

        tags[new_tag] = last_post_list[0]['created_at']

        with open(self.tags_path, 'w') as file:
            json.dump(tags, file)

        return True, 'Tag added successfully'

    def delete_tag(self, tag):
        with open(self.tags_path, 'r') as file:
            tags = json.load(file)

        if not tags.pop(tag, None):
            return False, 'The tag has not been deleted, it may not be in the list'

        with open(self.tags_path, 'w') as file:
            json.dump(tags, file)

        return True, 'Tag successfully deleted'

    def show_tag_list(self):
        with open(self.tags_path, 'r') as file:
            tags = json.load(file)

        return list(tags.keys())

    @staticmethod
    def get_post_url_under_five_mb(danbooru_post_json):
        size = int(danbooru_post_json.get('file_size'))

        if (size > 4_999_999 or
                int(danbooru_post_json.get('image_width')) + int(danbooru_post_json.get('image_height')) >= 10000):
            url = danbooru_post_json.get('large_file_url', danbooru_post_json.get('file_url'))
        else:
            url = danbooru_post_json.get('file_url')

        return url
