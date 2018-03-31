"""Monitors @biorxivpreprint to watch for new preprint articles and enters
each into the mysql database

This is temporary until biorxiv develops an actual API.

Modified from https://github.com/dataquestio/twitter-scrape/blob/master/scraper.py
"""

import re

import tweepy
from sqlalchemy.exc import ProgrammingError

class StreamListener(tweepy.StreamListener):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_status(self, status):
        try:
            text = re.sub(r'[^\x00-\x7f]',r'', status.text)
            self.callback(
                text=text,
                user_id=status.user.id,
                id=status.id,
                created=status.created_at,
            )
            print(status.id_str, text[:25], end='\r')
        except ProgrammingError as err:
            print(err)

    def on_error(self, status_code):
        if status_code == 420:
            #returning False in on_data disconnects the stream
            return False
