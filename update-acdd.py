#!/usr/bin/env python3

import os
from website.lib.pull_acdd_conventions import acdd_conventions_update

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
FIELDS_FILEPATH = os.path.join(BASE_PATH, 'config')

acdd_conventions_update(FIELDS_FILEPATH)

print('success')
