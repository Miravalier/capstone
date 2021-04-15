#!/usr/bin/env python3
import openpyxl
import json
from argparse import ArgumentParser
from pathlib import Path


INCOME_BRACKETS = (22500, 35000, 45000, 60000, 85000, 125000, 175000)


def main():
    parser = ArgumentParser()
    parser.add_argument("-d", "--data_dir", type=Path, required=True)
    args = parser.parse_args()

    data = {}
    for path in (args.data_dir / 'excel').iterdir():
        year = int(path.stem[-4:])
        data[str(year)] = workbook_to_json(path)

    data["income_brackets"] = INCOME_BRACKETS

    with open(args.data_dir / "expenses.json", "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def workbook_to_json(path):
    workbook = openpyxl.load_workbook(str(path))
    sheet = workbook.active
    excel_dir = path.parent
    data_dir = excel_dir.parent
    rows = []
    # Only lines that follow an empty separator line are used
    separator = False
    for i, line in enumerate(sheet.values):
        if i == 4:
            consumer_units = line[3:-1]
        row = [str(item).replace('\n', ' ') if item else "" for item in line]
        if not any(row):
            separator = True
        elif separator:
            separator = False
            rows.append(row)

    # Aggregate (A) = float(row[1]), in millions
    # Percentage (P) of aggregate spent by this income range = float(val), in percentage
    # Number (N) of consumer units at this income range = consumer_units[i], in thousands
    # Total = (A * 1,000,000 * (P/100)) / (C * 1000)
    # Total = (A * P * 10) / C
    totals = {row[0]: [(float(row[1]) * float(val) * 10) / consumer_units[i] for i, val in enumerate(row[3:-1])] for row in rows[13:-6]}

    # Income percentage = the total spent per CU / income
    percentages = {}
    for category in totals:
        percentages[category] = [(val / INCOME_BRACKETS[i]) * 100 for i, val in enumerate(totals[category])]

    # Save totals spent per CU and % of income spent
    return {
        "totals": totals,
        "percentages": percentages,
    }


if __name__ == '__main__':
    main()
