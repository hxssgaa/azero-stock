import glob

import pandas as pd
from dateutil import relativedelta

from ib_api import *
from utils import *


def get_earliest_time(app, contract):
    earliest_time = '%s 00:00:00' % app.req_head_time_stamp(500, contract)[0][1].split()[0]
    earliest_time = (datetime.datetime.strptime(earliest_time, '%Y%m%d %H:%M:%S') + relativedelta
                     .relativedelta(months=2)).strftime("%Y%m%d 00:00:00")
    return max('20120201 00:00:00', earliest_time)


def next_time(time):
    return (datetime.datetime.strptime(time, '%Y%m%d %H:%M:%S') + relativedelta
            .relativedelta(months=2)).strftime("%Y%m%d 00:00:00")


def make_contract(symbol, exchange):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = exchange
    return contract


def read_stock_contracts():
    stock_codes = pd.read_csv('stock_code.csv')
    codes = [make_contract(''.join(stock_code[1][3:]), 'SMART')
             for i, stock_code in enumerate(stock_codes.values)]
    return codes


def earliest_dt_for_symbol(symbol):
    earliest_file = sorted(glob.glob('ib_data/%s*.log' % symbol))
    if not earliest_file:
        return None
    return '%s 00:00:00' % earliest_file[0].split('_')[2]


def sync_stock(app, contract):
    client_id = int(app.clientId)
    symbol = contract.symbol
    logger_map = {}
    dt = datetime.datetime.today().strftime("%Y%m%d 00:00:00")
    early_dt = earliest_dt_for_symbol(symbol)
    if early_dt:
        dt = early_dt

    while True:
        hist_data = app.req_historical_data(client_id, contract, dt,
                                            "2 M", "1 min")
        for data in hist_data:
            if data[1] == 'historical_data':
                bar = data[2]
                sd = bar.date.split()[0]
                if '%s_%s' % (symbol, sd) not in logger_map:
                    logger_map['%s_%s' % (symbol, sd)] = setup_logger('%s_%s_1M' % (symbol, sd), 'ib_data/%s_%s_1M.log'
                                                                      % (symbol, sd))
                ib_logger = logger_map['%s_%s' % (symbol, sd)]
                ib_logger.info('%s~%s~%s~%s~%s~%s' % (
                    bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume))
            elif data[1] == 'historical_data_end':
                dt = data[2]

        client_id += 1
        if not hist_data:
            app.disconnect()
            break


def main():
    if len(sys.argv) != 4:
        raise RuntimeError('Argument is not right')

    client_id = sys.argv[1]
    contract_name = sys.argv[2]
    contract_exchange = sys.argv[3]

    app = IBApp("localhost", 4001, client_id)
    sync_stock(app, make_contract(contract_name, contract_exchange))


if __name__ == '__main__':
    main()
