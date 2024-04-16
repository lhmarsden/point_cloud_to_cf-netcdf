#!/usr/bin/env python3

import os
from website.lib.global_attributes import global_attributes_update

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
FIELDS_FILEPATH = os.path.join(BASE_PATH, 'config')

global_attributes_update(FIELDS_FILEPATH)

print('success')
