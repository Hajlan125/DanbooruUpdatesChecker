import csv
import json
import time
import requests


class DanbooruChecker:
    def __init__(self, tags_path, login, api_key, proxy_list_path=None, banned_tag=None):

        try:
            with open(tags_path, 'r'):
                self.tags_path = tags_path
        except FileNotFoundError:
            raise

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

    def post_list(self, tag, date=None, limit=25):
        if tag == ' ':
            tag = ''

        edited_tag = (tag.replace('(', '%28')
                      .replace(')', '%29')
                      .replace(':', '%3A'))
        if self.banned_tag:
            edited_tag += f'+-{self.banned_tag}'

        if date:
            edited_date = '+date%3A>' + date.replace('+03:00', '').replace(':', '%3A')[:-2] + '99'
            # call = (
            #     f'https://danbooru.donmai.us/posts.json?tags={edited_tag}+date%3A>{edited_date}&limit={limit}'
            #     f'&login={self.login}&api_key={self.api_key}')
        else:
            edited_date = ''

        call = (f'https://danbooru.donmai.us/posts.json?tags={edited_tag}{edited_date}&limit={limit}'
                f'&login={self.login}&api_key={self.api_key}')

        posts = self.danbooru_request(call, proxy_path=self.proxy_list_path)
        # print(posts)
        # print(current_proxy['https'])
        # print(call)

        return posts

    def post_show(self, post_id):
        call = f'https://danbooru.donmai.us/posts/{post_id}.json'
        post = self.danbooru_request(call, self.proxy_list_path)
        return post

    def danbooru_request(self, call, proxy_path):
        if proxy_path:
            for proxy in self.proxy_csv:
                current_proxy = {
                    'http': proxy[0],
                    'https': proxy[0]
                }
                try:
                    response = requests.get(call, proxies=current_proxy)
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
                response = requests.get(call)
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
            print(f'<<{tag}>> -- {len(updates)} posts')
            if not updates:
                continue

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
