
# Danbooru Updates Checker


## Overview

This telegram bot checks the danbooru website and sends all new posts according to the tags specified by the user. All tags stored in json file


## Features

- Add or delete tags to your tag list
- Check new posts by your favorite tags excluding banned tags
- Send pictures right to your telegram channel
- Proxy usage if Danbooru is blocked in your whereabouts
- ~~Community version of bot~~ (WIP)

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`ADMIN` - Chat id of bot user. No one will be able to use the bot except the user specified here

`TOKEN` - Token of your bot

`BOORU_LOGIN` - Danbooru login

`BOORU_API` - Danbooru API key

`TELEGRAM_CHANNEL_ID` - "@example" like id of channel where the bot can send images. Leave it empty if this function is unnecessary


## Run Locally

- Clone the project

```bash
  git clone https://github.com/Hajlan125/DanbooruUpdatesChecker
```

- Go to the project directory

```bash
  cd my-project
```

- Install requirements

```bash
  pip install -r requirements.txt
```

- Add environment varibles



- Start the bot

```bash
  python bot.py
```


## FAQ

### -How enable proxy?

In [bot.py](bot.py) file need to find next line:
```
  booru = DanbooruChecker(tags_path='tags.json', login=booru_login, api_key=booru_api, proxy_list_path=None, banned_tag='male_focus')
```
Then specify the path to list of your proxy servers in .csv file.

Like this you also can change the banned tag.




## Roadmap

- [ ]  Add banned tag changing function in telegram interface
- [ ]  Add code documentation
- [ ]  Finish community version of bot

