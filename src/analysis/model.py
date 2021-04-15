#!/usr/bin/env python3
import json
from argparse import ArgumentParser
from pathlib import Path
from pandas import DataFrame, concat
from keras.models import Sequential
from keras.layers import LSTM, Dense


def is_int(value):
    try:
        int(value)
        return True
    except:
        return False


def main():
    parser = ArgumentParser()
    parser.add_argument("-d", "--data_dir", type=Path, required=True)
    parser.add_argument("-n", "--neurons", type=int, default=1)
    parser.add_argument("-e", "--epochs", type=int, default=100)
    parser.add_argument("-i", "--income", type=int, default=80000)
    parser.add_argument("-b", "--batch-size", type=int, default=1)
    args = parser.parse_args()

    # Load data from file
    with open(args.data_dir / "expenses.json") as f:
        data = json.load(f)

    # Extract income brackets
    income_brackets = data['income_brackets']
    del data['income_brackets']

    # Select the greatest income bracket less than the given income
    i = 1
    while i < len(income_brackets):
        income_bracket = income_brackets[i]
        if income_bracket > args.income:
            break
        i += 1
    i -= 1

    # Find the set of all categories between all years
    categories = set()
    years = {int(year) for year in data}
    for year in range(min(years), max(years)+1):
        categories.update(data[str(year)]['totals'].keys())

    # For each category, add the total from each year to a list
    training_data = {}
    for category in categories:
        training_data[category] = []
        for year in range(min(years), max(years)+1):
            training_data[category].append(data[str(year)]['totals'][category][i])

        # Split values into training and testing values
        values = DataFrame(training_data[category]).values
        training_cutoff = int(0.66 * len(values))

        # Split training values into input and output
        training_input = values[:training_cutoff]
        training_output = values[1:training_cutoff+1]

        # Split testing values into input and output
        testing_input = values[training_cutoff:-1]
        testing_output = values[training_cutoff+1:]

        # Reshape inputs into 3D arrays for the model
        training_input = training_input.reshape((len(training_input), 1, 1))
        testing_input = testing_input.reshape((len(testing_input), 1, 1))

        # Reshape outputs to 1D arrays
        training_output = training_output.reshape((len(training_output),))
        testing_output = testing_output.reshape((len(testing_output),))

        print('----- Train Input -----')
        print(training_input)
        print('----- Train Output -----')
        print(training_output)
        print('----- Test Input -----')
        print(testing_input)
        print('----- Test Output -----')
        print(testing_output)
        print('-----')

        # Build model
        model = Sequential()
        model.add(LSTM(args.neurons, batch_input_shape=[args.batch_size, 1, 1], stateful=True))
        model.add(Dense(1))
        model.compile(loss='mean_squared_error', optimizer='adam')
        for i in range(args.epochs):
            model.fit(training_input, training_output, epochs=1, batch_size=args.batch_size, verbose=0, shuffle=False)
            model.reset_states()

        model.predict(training_input, batch_size=args.batch_size)

        for i in range(len(training_input)):
            prediction_input = training_input[i].reshape((1,1,1))
            guess = model.predict(prediction_input, batch_size=args.batch_size)
            guess = guess[0,0]
            expected = training_output[i]
            print("Guess:", guess)
            print("Expected:", expected)

        return


if __name__ == '__main__':
    main()
