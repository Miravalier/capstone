#!/usr/bin/env python3

# S&P500: https://pkgstore.datahub.io/core/s-and-p-500-companies/constituents_json/data/87cab5b5abab6c61eafa6dfdfa068a42/constituents_json.json
# Ticker Values: https://polygon.io

import json
import random
import requests
from argparse import ArgumentParser
from datetime import date, timedelta
from pathlib import Path

API_KEY_PATH=Path("~/.stocks-api-key").expanduser()
API_BASE_URL="https://api.polygon.io/v1/open-close/{}/{}?apiKey={}"
API_KEY = API_KEY_PATH.read_text().strip()

INPUT_PATH = Path("data/S&P500.json")
OUTPUT_PATH = Path("data/snapshots.json")


def get_stock_data(symbol: str, day: date):
    url = API_BASE_URL.format(symbol, day.isoformat(), API_KEY)
    return requests.get(url).json()


def main():
    parser = ArgumentParser()
    parser.add_argument("-c", "--count", type=int, default=None, help="Number of different symbols to query.")
    parser.add_argument("-d", "--days", type=int, default=1825, help="Days back to start querying.")
    parser.add_argument("-s", "--symbol", type=str, default=None, help="Specific symbol to query.")
    parser.add_argument("-o", "--output", type=str, default=OUTPUT_PATH, help="JSON output path.")
    args = parser.parse_args()

    if args.symbol is not None and args.count is not None:
        parser.error("--count and --symbol are mutually exclusive")

    if args.symbol is None:
        if args.count is None:
            args.count = 5

        with open(INPUT_PATH) as f:
            all_symbols = [datum['Symbol'] for datum in json.load(f)]

        symbols = set()
        while len(symbols) < args.count:
            added_symbols = random.sample(all_symbols, args.count - len(symbols))
            for symbol in added_symbols:
                stock_data = get_stock_data(symbol, date(2015, 6, 1))
                print(stock_data)
                if stock_data['status'] == 'OK':
                    symbols.add(symbol)
    else:
        symbols = {args.symbol}

    today = date.today()
    data = {}
    for symbol in symbols:
        symbol_snapshots = []
        # Start 5 years ago
        day = today - timedelta(days=args.days)
        # Run until today
        while day < today:
            # Skip weekends
            while day.isoweekday() > 5:
                day += timedelta(days=1)
            # Get stock data for the day
            stock_data = get_stock_data(symbol, day)
            print(symbol, day, stock_data)
            # If the day has no data, skip it
            if stock_data['status'] != 'OK':
                day += timedelta(days=3)
                continue
            # Append the stock data to the list
            symbol_snapshots.append(stock_data['open'])
            # Advance 30 days
            day += timedelta(days=30)
        data[symbol] = symbol_snapshots

    with open(args.output, "w") as f:
        json.dump(data, f)


if __name__ == '__main__':
    main()
