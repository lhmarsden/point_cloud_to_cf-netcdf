from flask import Flask, render_template, request, Blueprint, send_file, flash, redirect, session
from werkzeug.utils import secure_filename
import os
from lib.read_data import ascii_to_df
from lib.create_netcdf import df_to_netcdf
from lib.global_attributes import global_attributes_to_df
from lib.check_global_attributes import check_global_attributes
import numpy as np
from datetime import datetime, timezone
import json


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
    filename = secure_filename(file.filename)
    if file and allowed_file(filename):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Read in the file to a pandas dataframe

        session['filename'] = filename
        session['filepath'] = filepath
        session['header_row'] = int(request.form['header_row'])
        session['data_start_row'] = int(request.form['first_row_that_contains_data'])

        return redirect('/preview_dataframe')

        # Write the data to a NetCDF file
        #netcdf_filepath = os.path.join(UPLOAD_FOLDER, 'test.nc')


        #netcdf_file = df_to_netcdf(df, netcdf_filepath, global_attributes)
        # Return the modified file to the user
        #return send_file(netcdf_filepath, as_attachment=True)
    else:
        flash('Uploaded file is in the wrong format', category='error')
        return render_template('home.html', filename=filename)  # Pass filename back to template


@point_cloud_to_netcdf.route('/preview_dataframe', methods=['GET', 'POST'])
def preview_dataframe():

    filepath = session.get('filepath')
    filename = session.get('filename')
    header_row = session.get('header_row')
    data_start_row = session.get('data_start_row')
    df = ascii_to_df(filepath, header_row=header_row, data_start_row=data_start_row)

    if request.method == 'GET':

        # Get DataFrame rows as a list of dictionaries
        df_rows = df.head().to_dict(orient='records')
        # Get DataFrame headers as a list
        column_headers = df.columns.tolist()

        return render_template('preview_dataframe.html', df_rows=df_rows, column_headers=column_headers, filename=filename)

    if request.method == 'POST':

        action = request.form.get('action')

        if action == 'home':
            return redirect('/')

        else:
            # Handle form submission and update column headers
            new_headers = {}
            for key, value in request.form.items():
                if key.startswith('header_'):
                    index = int(key.split('_')[1])
                    new_headers[index] = value

            # Sort the new headers dictionary by keys to ensure consistency with DataFrame columns order
            new_headers_list = []
            for index in sorted(new_headers.keys()):
                new_headers_list.append(new_headers[index])

            df.columns = new_headers_list

            filename = 'updated_headers.csv'
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            df.to_csv(filepath, index=False)

            session['filename'] = filename
            session['filepath'] = filepath
            session['header_row'] = 1
            session['data_start_row'] = 2

            if action == 'continue':
                #TODO: Need to add checks and restrictions
                # One column must be called latitude, one longitude, one z
                # What about other columns? CF standard names?
                return redirect('/global_attributes')

            else:
                return redirect('/preview_dataframe')

@point_cloud_to_netcdf.route('/global_attributes', methods=['GET', 'POST'])
def global_attributes():

    filepath = session.get('filepath')
    filename = session.get('filename')
    header_row = session.get('header_row')
    data_start_row = session.get('data_start_row')

    session['filename'] = filename
    session['filepath'] = filepath
    session['header_row'] = header_row
    session['data_start_row'] = data_start_row

    df_metadata = global_attributes_to_df()
    df_metadata['value'] = df_metadata['value'].fillna('')
    df_metadata['choices'] = df_metadata['choices'].fillna('')
    df_metadata['Comment'] = df_metadata['Comment'].fillna('')
    json_string = df_metadata.to_json(orient='records')
    json_data = json.loads(json_string)

    current_time_utc = datetime.now(timezone.utc)
    iso8601_time_utc = current_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    df_metadata.loc[df_metadata['Attribute'] == 'date_created', 'value'] = iso8601_time_utc

    if request.method == 'POST':
        logged_attributes_list = []
        for key, value in request.form.items():
            if value:  # Check if a value has been entered
                logged_attributes_list.append(key)
            for item in json_data:
                if item['Attribute'] == key:
                    if item['format'] == 'number':
                        item['value'] = float(value)
                    else:
                        item['value'] = value

        logged_attributes = {}
        for item in json_data:
            attribute = item['Attribute']
            value = item['value']
            logged_attributes[attribute] = value

        required_attributes = df_metadata.loc[df_metadata['Requirement'] == 'Required', 'Attribute'].tolist()
        missing_attributes = [attr for attr in required_attributes if attr not in logged_attributes_list]

        if missing_attributes:
            flash(f'Required attributes not filled in: {missing_attributes}', category='error')
            return render_template('global_attributes.html', json_data=json_data)

        #TODO: checker now works on dataframe not dictionary
        errors = check_global_attributes(logged_attributes)
        if errors:
            for error in errors:
                flash(error, category='error')

            return render_template('global_attributes.html', json_data=json_data)

        else:
            # TODO: proceed to next page, preview of netCDF file
            flash('Success!', category='success')
            return render_template('global_attributes.html', json_data=json_data)

    #TODO: Placeholder for history?
    #TODO: keywords from vocabulary to drop-down?
    #TODO: Play around with session parameters that should be there until the user closes their browser

    return render_template('global_attributes.html', json_data=json_data)


if __name__ == '__main__':
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.register_blueprint(point_cloud_to_netcdf)
    app.secret_key = 'your_secret_key'  # Set a secret key for flashing messages
    app.run(debug=True)
