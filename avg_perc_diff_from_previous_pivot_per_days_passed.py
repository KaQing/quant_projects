# -*- coding: utf-8 -*-
"""
Created on Sun Aug 11 20:00:20 2024

@author: fisch
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import yfinance as yf
from datetime import datetime, timedelta
import seaborn as sns
from scipy.ndimage import gaussian_filter1d
import matplotlib.colors as mcolors

# PARAMETERS
ticker = "NG=F"
history = 15 #years
#cutoff percentage
zigzag_p = 5


# DOWNLOAD HISTORICAL DATA
# Assuming 'today' is a Pandas Timestamp
today = pd.to_datetime("today")
# Converting Timestamp to string
today_str = today.strftime('%Y-%m-%d')
# Define the end date as a datetime object
end_date = datetime.strptime(today_str, "%Y-%m-%d")
 #datetime.today() - timedelta(days=)
start_date = end_date - timedelta(days=history*365)
# Format the dates as strings
start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")   
# Download the Weekly data
df = yf.download(ticker, start=start_date_str, end=end_date_str, interval='1d')
df.index = pd.to_datetime(df.index)


#ZIGZAG CODE
#cutoff multiplier for zigzag calculation
zph = (100 + zigzag_p) / 100
zpl = (100 - zigzag_p) / 100
# Defining a temporary high and a dictionary for temporary highs
tmp_high = df["Adj Close"].iloc[0]
tmp_highs_d = {}

# Defining a temporary low and a dictionary for temporary lows
tmp_low = df["Adj Close"].iloc[0]
tmp_lows_d = {}

# Defining the zigzag dataframe for concatination of highs and lows
zigzag_df = pd.DataFrame({"date":df.index[0], "close": [df["Adj Close"].iloc[0]]})

# Iteration trough each row of the yfinance dataframe with price data 
for index, row in df.iterrows():
    # Defining date and close
    date = index
    date_str = date.strftime('%Y-%m-%d')
    close = row["Adj Close"]
    
    # if condition for filling the temporary high dictionary
    if close > tmp_high and close > tmp_low * zph:
            # condition is fulfilled close is now tmp_high
            tmp_high = close
            # new tmp_low threshold for collection of temporary lows
            tmp_low = close * zpl
            # adding new key value pair into tmp_highs_d
            tmp_highs_d[date_str] = tmp_high
            print("highs_d: ", tmp_highs_d)
            
            # make sure tmp_lows_d is not empty
            if not tmp_lows_d:
                print("lows_d is empty")
            # get the lowest value with date from the tmp_lows_d, turn it into a dataframe
            # concat the tl_df df to the zigzag_df
            else:
                lowest_key = min(tmp_lows_d, key=tmp_lows_d.get)
                lowest_value = tmp_lows_d[lowest_key]
                tl_df = pd.DataFrame({"date": [lowest_key], "close": [lowest_value]})
                zigzag_df = pd.concat([zigzag_df, tl_df])
                tmp_lows_d = {}
            
            

    if close < tmp_low and close < tmp_high * zpl: 
            tmp_low = close
            tmp_high = close * zph

            tmp_lows_d[date_str] = tmp_low
            
            
            if not tmp_highs_d:
                print("highs_d is empty")
            else:
                highest_key = max(tmp_highs_d, key=tmp_highs_d.get)
                highest_value = tmp_highs_d[highest_key]
                th_df = pd.DataFrame({"date": [highest_key], "close": [highest_value]})
                zigzag_df = pd.concat([zigzag_df, th_df])
                tmp_highs_d = {}

plt.plot(zigzag_df["date"], zigzag_df["close"])
plt.show()


# DATETIME CALCULATIONS AND PLOTTING
zigzag_df["date"] = pd.to_datetime(zigzag_df["date"])
zigzag_df = zigzag_df.set_index(zigzag_df["date"])
# Calculate the differnce with the date column
zigzag_df['time_diff'] = zigzag_df["date"].diff()
zigzag_df['time_diff'] = zigzag_df['time_diff'].dt.days
zigzag_df["close_ratio"] = zigzag_df["close"].pct_change()*100
zigzag_df = zigzag_df.dropna(subset="close_ratio")

# Iterate over the DataFrame using iterrows()
for idx, row in zigzag_df.iterrows():
    if row["close_ratio"] > 1:  # Positive close_ratio -> 'high'
        zigzag_df.at[idx, "pivot"] = "high"
    elif row["close_ratio"] < 1:  # Negative close_ratio -> 'low'
        zigzag_df.at[idx, "pivot"] = "low"

# Use shift to bring the next close in to the current to calculate the percentage differences of the closes
zigzag_df["next_close"] = zigzag_df["close"].shift(-1)
# Create column pivot to categorize lows and highs
zigzag_df.loc[zigzag_df["pivot"] == "low", "close_perc_diff"] = ((zigzag_df["next_close"] / zigzag_df["close"])-1)
zigzag_df.loc[zigzag_df["pivot"] == "high", "close_perc_diff"] = ((zigzag_df["close"]- zigzag_df["next_close"]) / zigzag_df["next_close"])

# Plot the percentage differences of pivots compared to days passed
sns.scatterplot(data=zigzag_df, x="time_diff", y="close_ratio", hue="pivot", style="pivot", palette="deep")
plt.title("Scatterplot of percentage differences compared to days passed")
plt.show()

# Normalize the percentage differences for size and transparancy adjustments based on the perenctage difference of previous gains
zigzag_df['norm_pd'] = (zigzag_df['close_perc_diff'] - zigzag_df['close_perc_diff'].min()) / (zigzag_df['close_perc_diff'].max() - zigzag_df['close_perc_diff'].min())
zigzag_df["alpha"] = zigzag_df['norm_pd']
zigzag_df = zigzag_df.dropna(subset="alpha")
zigzag_df['norm_pd'] = zigzag_df['norm_pd'] * 50

# Subset the zigzag_df to create dfs with only highs and lows
zz_high = zigzag_df[zigzag_df["pivot"] == "high"]
zz_low = zigzag_df[zigzag_df["pivot"] == "low"]

# Plot the percentage differences with curvefitting for lows and highs
# alpha and size are equivalent to the percentage gain which followed the low/high
sns.regplot(data=zz_high, x="time_diff", y="close_ratio", order=2, scatter_kws={"alpha":zz_high["alpha"], "s":zz_high["norm_pd"]})
plt.title("Average percentage extension from previous low per days passed")
plt.xscale('log')
plt.show()
sns.regplot(data=zz_low, x="time_diff", y="close_ratio", order=2, scatter_kws={"alpha":zz_low["alpha"], "s":zz_low["norm_pd"]})
plt.title("Average percentage retracement from previous high per days passed")
plt.xscale('log')
plt.show()
