#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import request, send_file, render_template, flash, redirect, url_for
from website import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
