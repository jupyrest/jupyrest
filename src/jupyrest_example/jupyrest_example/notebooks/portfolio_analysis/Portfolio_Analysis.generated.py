# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernel_info:
#     name: python3
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Portfolio Analysis
#
# Adapted from LastAncientOne's Github repository [Stock_Analysis_For_Quant](https://github.com/LastAncientOne/Stock_Analysis_For_Quant/blob/master/Python_Stock/Portfolio_Analysis.ipynb)

# %% inputHidden=false outputHidden=false
import datetime
from jupyrest_example import load_data_from_object, Portfolio

# %% tags=["parameters"]
# default parameters
portfolio = Portfolio(
    start_date = datetime.date.fromisoformat("2022-04-26"),
    end_date = datetime.date.fromisoformat("2023-04-26"),
    holdings={'AAPL': 0.25,'MSFT': 0.25,'AMD': 0.25,'NVDA': 0.25}
)

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

# %% inputHidden=false outputHidden=false
dataset, weights = load_data_from_object(portfolio)
dataset

# %% inputHidden=false outputHidden=false
# Calculate Daily Returns
returns = dataset.pct_change()

# %% inputHidden=false outputHidden=false
returns = returns.dropna()

# %% inputHidden=false outputHidden=false
returns.head()

# %% inputHidden=false outputHidden=false
# Calculate mean returns
meanDailyReturns = returns.mean()
print(meanDailyReturns)

# %% inputHidden=false outputHidden=false
# Calculate std returns
stdDailyReturns = returns.std()
print(stdDailyReturns)

# %% inputHidden=false outputHidden=false
# Define weights for the portfolio
weights = np.array(weights)

# %% inputHidden=false outputHidden=false
# Calculate the covariance matrix on daily returns
cov_matrix = (returns.cov())*250
print (cov_matrix)

# %% inputHidden=false outputHidden=false
# Calculate expected portfolio performance
portReturn = np.sum(meanDailyReturns*weights)

# %% inputHidden=false outputHidden=false
# Print the portfolio return
print(portReturn)

# %% inputHidden=false outputHidden=false
# Create portfolio returns column
returns['Portfolio'] = returns.dot(weights)

# %% inputHidden=false outputHidden=false
returns.head()

# %% inputHidden=false outputHidden=false
# Calculate cumulative returns
daily_cum_ret=(1+returns).cumprod()
print(daily_cum_ret.tail())

# %% inputHidden=false outputHidden=false
returns['Portfolio'].hist()
plt.show()

# %% inputHidden=false outputHidden=false
import matplotlib.dates

# Plot the portfolio cumulative returns only
fig, ax = plt.subplots()
ax.plot(daily_cum_ret.index, daily_cum_ret.Portfolio, color='purple', label="portfolio")
ax.xaxis.set_major_locator(matplotlib.dates.YearLocator())
plt.legend()
plt.show()

# %% inputHidden=false outputHidden=false
# Print the mean
print("mean : ", returns['Portfolio'].mean()*100)

# Print the standard deviation
print("Std. dev: ", returns['Portfolio'].std()*100)

# Print the skewness
print("skew: ", returns['Portfolio'].skew())

# Print the kurtosis
print("kurt: ", returns['Portfolio'].kurtosis())

# %% inputHidden=false outputHidden=false
# Calculate the standard deviation by taking the square root
port_standard_dev = np.sqrt(np.dot(weights.T, np.dot(weights, cov_matrix)))

# Print the results 
print(str(np.round(port_standard_dev, 4) * 100) + '%')

# %% inputHidden=false outputHidden=false
# Calculate the portfolio variance
port_variance = np.dot(weights.T, np.dot(cov_matrix, weights))

# Print the result
print(str(np.round(port_variance, 4) * 100) + '%')

# %% inputHidden=false outputHidden=false
# Calculate total return and annualized return from price data 
total_return = (returns['Portfolio'][-1] - returns['Portfolio'][0]) / returns['Portfolio'][0]

# Annualize the total return over 1 year 
annualized_return = ((total_return + 1.0)**(1/1))-1.0

# %% inputHidden=false outputHidden=false
# Calculate annualized volatility from the standard deviation
vol_port = returns['Portfolio'].std() * np.sqrt(250)

# %% inputHidden=false outputHidden=false
# Calculate the Sharpe ratio 
rf = 0.01
sharpe_ratio = ((annualized_return - rf) / vol_port)
print (sharpe_ratio)

# %% [markdown]
# If the analysis results in a negative Sharpe ratio, it either means the risk-free rate is greater than the portfolio's return, or the portfolio's return is expected to be negative. 

# %% inputHidden=false outputHidden=false
# Create a downside return column with the negative returns only
target = 0
downside_returns = returns.loc[returns['Portfolio'] < target]

# Calculate expected return and std dev of downside
expected_return = returns['Portfolio'].mean()
down_stdev = downside_returns.std()

# Calculate the sortino ratio
rf = 0.01
sortino_ratio = (expected_return - rf)/down_stdev

# Print the results
print("Expected return: ", expected_return*100)
print('-' * 50)
print("Downside risk:")
print(down_stdev*100)
print('-' * 50)
print("Sortino ratio:")
print(sortino_ratio)

# %% inputHidden=false outputHidden=false
# Calculate the max value 
roll_max = returns['Portfolio'].rolling(center=False,min_periods=1,window=252).max()

# Calculate the daily draw-down relative to the max
daily_draw_down = returns['Portfolio']/roll_max - 1.0

# Calculate the minimum (negative) daily draw-down
max_daily_draw_down = daily_draw_down.rolling(center=False,min_periods=1,window=252).min()

# Plot the results
plt.figure(figsize=(15,15))
plt.plot(returns.index, daily_draw_down, label='Daily drawdown')
plt.plot(returns.index, max_daily_draw_down, label='Maximum daily drawdown in time-window')
plt.legend()
plt.show()

# %%
output_df = pd.concat({"DownsideRisk":down_stdev*100, "SortinoRatio": sortino_ratio}, axis=1)
output_df

# %%
import json
from jupyrest import save_output

save_output(output_df.to_dict())
