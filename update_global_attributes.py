#!/usr/bin/env python3

import os
from website.lib.global_attributes import global_attributes_update

errors = global_attributes_update()

if len(errors) > 0:
    for error in errors:
        print(error)
else:
    print('success')
