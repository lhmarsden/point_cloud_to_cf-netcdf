from flask import Flask, render_template, request, Blueprint, send_file, flash, redirect
from werkzeug.utils import secure_filename
import os
from website.lib.read_data import ascii_to_df
from website.lib.create_netcdf import df_to_netcdf

point_cloud_to_netcdf = Blueprint('point_cloud_to_netcdf', __name__)

UPLOAD_FOLDER = '/tmp/'
ALLOWED_EXTENSIONS = {'txt', 'csv', 'ascii', 'tsv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@point_cloud_to_netcdf.route('/')
def home():
    return render_template('home.html', filename=None)  # Pass filename=None initially

@point_cloud_to_netcdf.route('/', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', category='error')
        return redirect('/')
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', category='error')
        return redirect('/')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)  # Use the Blueprint's UPLOAD_FOLDER
        file.save(file_path)

        # Read in the file to a pandas dataframe
        df = ascii_to_df(file_path)

        # Write the data to a NetCDF file
        netcdf_filepath = os.path.join(UPLOAD_FOLDER, 'test.nc')

        global_attributes = {
            'title': 'test'
        }

        netcdf_file = df_to_netcdf(df, netcdf_filepath, global_attributes)
        # Return the modified file to the user
        return send_file(netcdf_filepath, as_attachment=True)
    else:
        flash('Uploaded file is in the wrong format', category='error')
        return render_template('home.html', filename=filename)  # Pass filename back to template

if __name__ == '__main__':
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.register_blueprint(point_cloud_to_netcdf)
    app.secret_key = 'your_secret_key'  # Set a secret key for flashing messages
    app.run(debug=True)
