from matplotlib import pyplot as plt
from matplotlib.dates import WeekdayLocator, MONDAY, DayLocator, DateFormatter, date2num
from mpl_finance import candlestick_ohlc

import futu_api as api
import pandas as pd
import numpy as np
import argparse


class StockAnalyser(object):
    def _get_stock_kline(self, stock, start, end, ktype, autype):
        res = api.get_history_kline(stock, start, end, ktype, autype)
        if not res or res[0] != 0:
            raise RuntimeError('Get stock kline error: %s' % res[1])
        return res[1].set_index(pd.DatetimeIndex(res[1].values[:, 1]))

    def _get_stocks_kline(self, args):
        result = map(lambda e: self._get_stock_kline(e, args.start, args.end, args.ktype, args.autype),
                     args.stocks.split(','))
        return list(filter(lambda e: len(e.values) > 0, result))

    def pandas_candlestick_ohlc(self, dat, stick="day", otherseries=None):
        """
        :param dat: pandas DataFrame object with datetime64 index, and float columns "Open", "High", "Low", and "Close",
                    likely created via DataReader from "yahoo"
        :param stick: A string or number indicating the period of time covered by a single candlestick. Valid string
                    inputs include "day", "week", "month", and "year", ("day" default), and any numeric input indicates
                    the number of trading days included in a period
        :param otherseries: An iterable that will be coerced into a list, containing the columns of dat that hold other
                    series to be plotted as lines

        This will show a Japanese candlestick plot for stock data stored in dat, also plotting other series if passed.
        """
        mondays = WeekdayLocator(MONDAY)  # major ticks on the mondays
        alldays = DayLocator()  # minor ticks on the days
        dayFormatter = DateFormatter('%d')  # e.g., 12

        # Create a new DataFrame which includes OHLC data for each period specified by stick input
        transdat = dat.loc[:, ["open", "high", "low", "close"]]
        plotdat = None
        if type(stick) == str:
            if stick == "day":
                plotdat = transdat
                stick = 1  # Used for plotting
            elif stick in ["week", "month", "year"]:
                if stick == "week":
                    transdat["week"] = pd.to_datetime(transdat.index).map(
                        lambda x: x.isocalendar()[1])  # Identify weeks
                elif stick == "month":
                    transdat["month"] = pd.to_datetime(transdat.index).map(lambda x: x.month)  # Identify months
                transdat["year"] = pd.to_datetime(transdat.index).map(lambda x: x.isocalendar()[0])  # Identify years
                grouped = transdat.groupby(list({"year", stick}))  # Group by year and other appropriate variable
                plotdat = pd.DataFrame({"open": [], "high": [], "low": [],
                                        "close": []})  # Create empty data frame containing what will be plotted
                for name, group in grouped:
                    plotdat = plotdat.append(pd.DataFrame({"open": group.iloc[0, 0],
                                                           "high": max(group.High),
                                                           "low": min(group.Low),
                                                           "close": group.iloc[-1, 3]},
                                                          index=[group.index[0]]))
                if stick == "week":
                    stick = 5
                elif stick == "month":
                    stick = 30
                elif stick == "year":
                    stick = 365

        elif type(stick) == int and stick >= 1:
            transdat["stick"] = [np.floor(i / stick) for i in range(len(transdat.index))]
            grouped = transdat.groupby("stick")
            plotdat = pd.DataFrame({"open": [], "high": [], "low": [],
                                    "close": []})  # Create empty data frame containing what will be plotted
            for name, group in grouped:
                plotdat = plotdat.append(pd.DataFrame({"open": group.iloc[0, 0],
                                                       "high": max(group.High),
                                                       "low": min(group.Low),
                                                       "close": group.iloc[-1, 3]},
                                                      index=[group.index[0]]))

        else:
            raise ValueError(
                'Valid inputs to argument "stick" include the strings "day", "week", "month", "year", or a '
                'positive integer')

        # Set plot parameters, including the axis object ax used for plotting
        fig, ax = plt.subplots()
        fig.subplots_adjust(bottom=0.2)
        # fig.set_size_inches(38.4, 21.6)
        if plotdat.index[-1] - plotdat.index[0] < pd.Timedelta('730 days'):
            weekFormatter = DateFormatter('%b %d')  # e.g., Jan 12
            ax.xaxis.set_major_locator(mondays)
            ax.xaxis.set_minor_locator(alldays)
        else:
            weekFormatter = DateFormatter('%b %d, %Y')
        ax.xaxis.set_major_formatter(weekFormatter)

        ax.grid(True)

        # Create the candelstick chart
        candlestick_ohlc(ax, list(
            zip(list(date2num(plotdat.index.tolist())), plotdat["open"].tolist(), plotdat["high"].tolist(),
                plotdat["low"].tolist(), plotdat["close"].tolist())),
                         colorup="red", colordown="green", width=stick * .4)

        # Plot other series (such as moving averages) as lines
        if otherseries is not None:
            if type(otherseries) != list:
                otherseries = [otherseries]
            dat.loc[:, otherseries].plot(ax=ax, lw=1.3, grid=True)

        ax.xaxis_date()
        plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
        plt.savefig('b.png', dpi=200)

    def draw_stocks(self, args):
        stocks = self._get_stocks_kline(args)
        num_stock = len(stocks)
        self.pandas_candlestick_ohlc(stocks[0], otherseries=np.round(
            stocks[0]["close"].rolling(window=5, center=False).mean(), 2))

    def dispatch(self):
        parser = argparse.ArgumentParser(description='Stock analyser argument parser.')
        parser.add_argument("-command", "--command", type=str, required=True)
        parser.add_argument("-stocks", "--stocks", type=str, required=True)
        parser.add_argument("-start", "--start", type=str, required=False)
        parser.add_argument("-end", "--end", type=str, required=False)
        parser.add_argument("-ktype", "--ktype", type=str, required=False)
        parser.add_argument("-autype", "--autype", type=str, required=False)
        args = parser.parse_args()
        getattr(self, args.command)(args)
        print('%s done' % args.command)


if __name__ == '__main__':
    StockAnalyser().dispatch()