import pandas as pd

def ascii_to_df(filepath):
    df = pd.read_csv(filepath, header=None, names=['longitude', 'latitude', 'altitude'])
    return df