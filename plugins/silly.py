from __future__ import absolute_import
from __future__ import print_function

import re
import sys

import requests

from rtmbot.core import Plugin
from plugins.db import DataStore


class Silly(Plugin):
    def process_message(self, data):
        message = data['text']
        if 'groot' in message.lower():
            self.outputs.append([data['channel'], 'I AM GROOT'])
