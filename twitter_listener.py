"""Monitors @biorxivpreprint to watch for new preprint articles and enters
each into the mysql database

This is temporary until biorxiv develops an actual API.

Modified from https://github.com/dataquestio/twitter-scrape/blob/master/scraper.py
"""

import os.path
import re

import tweepy

class StreamListener(tweepy.StreamListener):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_status(self, status):
        self.callback(status)

    def on_error(self, status_code):
        if status_code == 420:
            #returning False in on_data disconnects the stream
            return False
