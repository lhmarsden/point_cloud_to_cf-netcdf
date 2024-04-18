#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 13 08:53:13 2022

@author: lukem
"""

import pandas as pd
import numpy as np

class Global_attributes_df():
    '''
    Class for pulling global attributes to a pandas dataframe
    Only try to pull latest global attributes if online
    Otherwise pull from existing CSV
    So the CSV overwrites each time the script runs if online
    '''

    def __init__(self):
        """
        Parameters
        ----------
        filename: string
            The name of the json file to be written
        """
        self.filename = 'config/global_attributes.csv'


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
        self.df['placeholder'] = ''

        self.df.loc[self.df['Attribute'] == 'license', 'placeholder'] = 'https://creativecommons.org/licenses/by/4.0/'
        self.df.loc[self.df['Attribute'] == 'Conventions', 'placeholder'] = 'CF-1.8, ACDD-1.3'
        self.df.loc[self.df['Attribute'] == 'operational_status', 'placeholder'] = 'Scientific'
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
        self.df.to_csv(self.filename, index=False)

    def read_csv(self):
        '''
        '''
        self.df = pd.read_csv(self.filename, index_col=False)

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

def global_attributes_to_df():
    global_attributes = Global_attributes_df()
    global_attributes.read_csv()
    return global_attributes.df
