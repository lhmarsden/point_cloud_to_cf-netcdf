#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 13 08:53:13 2022

@author: lukem
"""

import pandas as pd
import numpy as np
from lib.utils import validate_time_format

class Global_attributes_df():
    '''
    Class for pulling global attributes to a pandas dataframe
    Only try to pull latest global attributes if online
    Otherwise pull from existing CSV
    So the CSV overwrites each time the script runs if online
    '''

    def __init__(self, filepath='config/global_attributes_copy.csv'):
        """
        Parameters
        ----------
        filepath: string
            Location of the global attributes file
        """
        self.template_filepath = 'config/global_attributes.csv'
        self.filepath = filepath


    def pull_from_online(self):
        '''
        Script to harvest the global attributes to a pandas dataframe
        Take them from the ADC page

        Returns
        -------
        df: pandas dataframe
            global attributes in a dataframe

        '''
        url = 'https://adc.met.no/node/4'
        tables = pd.read_html(url)
        df1 = tables[0]
        df2 = tables[1]
        df2 = df2.set_axis(df2.iloc[0], axis=1)
        df2 = df2[1:]
        self.df = pd.concat([df1, df2], ignore_index=True)
        self.df = self.df.dropna(how='all')
        self.df.reset_index(inplace=True, drop=True)

    def add_recommendations_column(self):
        '''
        '''
        # Add a new column based on the values in the 'Comment' column
        conditions = [
            self.df['Comment'].str.contains('Required', case=False, na=False),
            self.df['Comment'].str.contains('Optional', case=False, na=False),
            self.df['Comment'].str.contains('Recommended', case=False, na=False),
            self.df['Comment'].str.contains('Yes if not hosted by MET', case=False, na=False)
        ]
        choices = ['Required', 'Optional', 'Recommended', 'Required']
        self.df['Requirement'] = np.select([c.values for c in conditions], choices, default='')

    def add_other_columns(self):

        self.df['min'] = np.nan
        self.df['max'] = np.nan
        self.df['format'] = 'text'
        self.df['choices'] = None
        self.df['value'] = ''

        self.df.loc[self.df['Attribute'] == 'license', 'value'] = 'https://creativecommons.org/licenses/by/4.0/'
        self.df.loc[self.df['Attribute'] == 'Conventions', 'value'] = 'CF-1.8, ACDD-1.3'
        self.df.loc[self.df['Attribute'] == 'operational_status', 'value'] = 'Scientific'
        self.df.loc[self.df['Attribute'] == 'operational_status', 'choices'] = 'Operational; Pre-Operational; Experimental; Scientific; Not available'

        self.df.loc[self.df['Attribute'] == 'iso_topic_category', 'choices'] = 'farming; biota; boundaries; climatologyMeteorologyAtmosphere; economy; elevation; environment; geoscientificInformation; health; imageryBaseMapsEarthCover; intelligenceMilitary; inlandWaters; location; oceans; planningCadastre; soceity; structure; transportation; utilitiesCommunications; Not available'

        self.df.loc[self.df['Attribute'] == 'geospatial_lat_min', 'min'] = -90
        self.df.loc[self.df['Attribute'] == 'geospatial_lat_min', 'max'] = 90
        self.df.loc[self.df['Attribute'] == 'geospatial_lat_max', 'min'] = -90
        self.df.loc[self.df['Attribute'] == 'geospatial_lat_max', 'max'] = 90

        self.df.loc[self.df['Attribute'] == 'geospatial_lon_min', 'min'] = -180
        self.df.loc[self.df['Attribute'] == 'geospatial_lon_min', 'max'] = 180
        self.df.loc[self.df['Attribute'] == 'geospatial_lon_max', 'min'] = -180
        self.df.loc[self.df['Attribute'] == 'geospatial_lon_max', 'max'] = 180

        number_atts = [
            'geospatial_lat_min',
            'geospatial_lat_max',
            'geospatial_lon_min',
            'geospatial_lon_max'
        ]
        for att in number_atts:
            self.df.loc[self.df['Attribute'] == att, 'format'] = 'number'

        atts_to_remove = [
            'featureType',
            'activity_type',
            'platform',
            'platform_vocabulary'
        ]
        for att in atts_to_remove:
            self.df = self.df[self.df['Attribute'] != att]

    def output_to_csv(self):
        '''
        '''
        self.df.to_csv(self.template_filepath, index=False)

    def read_csv(self):
        '''
        '''
        self.df = pd.read_csv(self.filepath, index_col=False)

    def check(self):
        '''
        Check the values that the user has provided for the global attributes
        '''
        # List of errors that will be appended to throughout this function.
        # If there are any errors, no CF-NetCDF file will be created
        errors = []

        # List of warnings that will be appended to throughout this function
        # Warnings will be flagged to the user but this alone will not stop a CF-NetCDF file from being created
        warnings = []

        # Attributes derived during the code that the user does not need to provide
        derived_attributes = [
            'date_created',
            'history',
            'geospatial_lat_min',
            'geospatial_lat_max',
            'geospatial_lon_min',
            'geospatial_lon_max',
        ]

        for _, row in self.df.iterrows():
            attribute = row['Attribute']
            value = row['value']
            requirement = row['Requirement']

            if value in ['nan', np.nan, None, '']:
                if requirement == 'Required' and attribute not in derived_attributes:
                    errors.append(f'"{attribute}" is a required global attribute. Please provide a value')
                else:
                    pass
            else:
                if attribute in ['time_coverage_start', 'time_coverage_end', 'date_created']:
                    if validate_time_format(value) == False:
                        errors.append(f'{attribute} must be in the format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ')

                if attribute in ['geospatial_lat_min', 'geospatial_lat_max']:
                    if -90 <= float(value) <= 90:
                        pass
                    else:
                        errors.append(f'{attribute} must be between -90 and 90 inclusive')

                if attribute in ['geospatial_lon_min', 'geospatial_lon_max']:
                    if -180 <= float(value) <= 180:
                        pass
                    else:
                        errors.append(f'{attribute} must be between -180 and 180 inclusive')

        geospatial_lat_min = self.df.loc[self.df['Attribute'] == 'geospatial_lat_min', 'value'].values[0]
        geospatial_lat_max = self.df.loc[self.df['Attribute'] == 'geospatial_lat_max', 'value'].values[0]
        geospatial_lon_min = self.df.loc[self.df['Attribute'] == 'geospatial_lon_min', 'value'].values[0]
        geospatial_lon_max = self.df.loc[self.df['Attribute'] == 'geospatial_lon_max', 'value'].values[0]
        time_coverage_start = self.df.loc[self.df['Attribute'] == 'time_coverage_start', 'value'].values[0]
        time_coverage_end = self.df.loc[self.df['Attribute'] == 'time_coverage_end', 'value'].values[0]

        if geospatial_lat_min > geospatial_lat_max:
            errors.append('geospatial_lat_max must be greater than or equal to geospatial_lat_min')

        if geospatial_lon_min > geospatial_lon_max:
            errors.append('geospatial_lon_max must be greater than or equal to geospatial_lon_min')

        if time_coverage_start > time_coverage_end:
            errors.append('time_coverage_end must be greater than or equal to time_coverage_start')

        return errors, warnings


def global_attributes_update():
    errors = []
    global_attributes = Global_attributes_df()
    try:
        global_attributes.pull_from_online()
    except:
        errors.append("Could not update. Couldn't access data from source URL")
        return errors
    try:
        global_attributes.add_recommendations_column()
    except:
        errors.append("Could not update. Error adding recommendations column")
        return errors
    try:
        global_attributes.add_other_columns()
    except:
        errors.append("Could not update. Error adding other columns")
        return errors
    try:
        global_attributes.output_to_csv()
    except:
        errors.append("Could not update. Couldn't save the CSV file.")
        return errors
    return errors
