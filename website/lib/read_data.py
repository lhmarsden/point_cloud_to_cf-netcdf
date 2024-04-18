import pandas as pd

def ascii_to_df(filepath, header_row, data_start_row):
    gap = data_start_row-(header_row+1)
    if header_row == 0:
        df = pd.read_csv(filepath, header=None, skiprows=data_start_row-header_row)
    elif gap == 0:
        df = pd.read_csv(filepath, header=header_row-1)
    else:
        df = pd.read_csv(filepath, header=header_row, skiprows=data_start_row-(header_row+1))
    return df