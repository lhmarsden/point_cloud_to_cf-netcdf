from flask import Flask, session
import uuid
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = str(uuid.uuid4())

    from .views.point_cloud_to_netcdf import point_cloud_to_netcdf

    app.register_blueprint(point_cloud_to_netcdf, url_prefix='/')

    return app
