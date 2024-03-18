import pandas as pd
import xarray as xr

# Sample DataFrame
data = {
    'Year': [2024, 2024, 2024, 2024],
    'Month': [3, 3, 3, 3],
    'Day': [15, 16, 17, 18],
    'SnowDepth': [0.16, 0.15, 0.15, 0.14]
}

df = pd.DataFrame(data)

# Convert Year, Month, and Day to datetime
df['Date'] = pd.to_datetime(df[['Year', 'Month', 'Day']])

# Find the minimum date
start_date = df['Date'].min()

# Calculate the difference in days
df['Days since start'] = (df['Date'] - start_date).dt.days

# Drop the 'Date' column if needed
df.drop(columns=['Date'], inplace=True)

xrds = xr.Dataset(
    coords = dict(
        time = df['Days since start']
    ),
    data_vars = dict(
        snow_depth = ("time", df['SnowDepth'])
    )
)

xrds['time'].attrs['standard_name'] = 'time'
xrds['time'].attrs['long_name'] = 'time'
xrds['time'].attrs['units'] = f'days since {start_date.date()}'
xrds['time'].attrs['coverage_content_type'] = 'coordinate'

print(xrds['time'])
