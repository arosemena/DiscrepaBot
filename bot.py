# made for the /r/mexico subreddit

import configparser
import praw
import requests
import json
import redis
from urllib.parse import urlparse

# cache store to prevent multiple posts
cache = redis.StrictRedis()

# ini file with credentials
config = configparser.ConfigParser()
config.read('secrets.ini')

# allowed sites
whitelist = open("whitelist.txt").read().splitlines()

# smmry API secret
secret = config.get('smmry', 'secret')

reddit = praw.Reddit(user_agent='DiscrepaBot',
                     client_id=config.get('reddit', 'client_id'),
                     client_secret=config.get('reddit', 'client_secret'),
                     password=config.get('reddit', 'password'),
                     username=config.get('reddit', 'username'))

posts = reddit.subreddit('mexico').hot(limit=12)
for post in posts:
    hostname = urlparse(post.url).netloc
    if not (hostname in whitelist): continue  # if the hostname isn't in the whitelist ignore the post
    if cache.exists(post.id): continue  # if the post id is in the cache it means the bot already knew about it

    # The post is new and the url is inside the whitelist, begin the process
    cache.set(post.id, True)  # store the id inside the cache to avoid spam
    cache.expire(post.id, 60 * 60 * 24 * 14)  # expire in 2 weeks to clean old posts from the cache

    # SMMRY API service endpoint
    endpoint = f"http://api.smmry.com/?SM_API_KEY={secret}&SM_WITH_BREAK&SM_LENGTH=3&SM_URL={post.url}"
    response = requests.post(endpoint).text  # sending the API request
    json = json.loads(response)  # load the api response from smmry
    if 'sm_api_error' in json: exit(1)  # This key means our request to the service wasn't allowed, exit to avoid spam

    # All good so far, extract the title and content from the api response
    text = json['sm_api_content']
    excerpts = text.split("[BREAK]")[:-1]
    title = json['sm_api_title']

    disclaimer = open("disclaimer.txt", encoding='utf8').read()

    # Create a new comment inside the post
    comment = f"### {title}\n\n---\n"  # markdown title and separator
    for excerpt in excerpts:  # add a list item for every block of text
        comment += f"- {excerpt.strip()} \n"
    # and then comes the disclaimer
    comment += f"\n---\n^(**{disclaimer}**)"

    post.reply(comment)  # Finally we post the comment and the job of the bot is done, for now...

    exit(0)  # Only process one post per iteration, the SMMRY API has a once every 10 seconds restriction.
