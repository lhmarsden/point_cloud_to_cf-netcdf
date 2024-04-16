#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 13 08:53:13 2022

@author: lukem
"""

import pandas as pd
import numpy as np

class ACDD_conventions_df():
    '''
    Class for pulling ACDD conventions to a pandas dataframe
    Only try to pull latest ACDD conventions if online
    Otherwise pull from existing CSV
    So the CSV overwrites each time the script runs if online
    '''

    def __init__(self, path):
        """
        Parameters
        ----------
        filename: string
            The name of the json file to be written
        """
        self.filename = path + '/global_attributes.csv'


    def pull_from_online(self):
        '''
        Script to harvest the ACDD conventions to a pandas dataframe
        Take them from the ADC page

        Returns
        -------
        df: pandas dataframe
            ACDD conventions in a dataframe

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

    def output_to_csv(self):
        '''
        '''
        self.df.to_csv(self.filename, index=False)

    def read_csv(self):
        '''
        '''
        self.df = pd.read_csv(self.filename, index_col=False)

def acdd_conventions_update(path):
    errors = []
    acdd = ACDD_conventions_df(path)
    try:
        acdd.pull_from_online()
    except:
        errors.append("Could not update ACDD configuration. Couldn't access data from source URL")
        return errors
    try:
        acdd.add_recommendations_column()
    except:
        errors.append("Could not update ACDD configuration. Error adding recommendations column")
        return errors
    try:
        acdd.output_to_csv()
    except:
        errors.append("Could not update ACDD configuration. Couldn't save the CSV file.")
        return errors
    return errors

def acdd_to_df(path):
    acdd = ACDD_conventions_df(path)
    acdd.read_csv()
    return acdd.df
