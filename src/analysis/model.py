#!/usr/bin/env python3

import json
import numpy
import pandas
from argparse import ArgumentParser
from functools import partial
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error


class ExpenseModel:
    def __init__(self, neurons=1):
        # Import ML libraries here rather than at the top because
        # a lot of code is run at import time. Importlib will ensure
        # these imports only run once.
        from keras.models import Sequential
        from keras.layers import LSTM, Dense

        # Build model
        self.model = Sequential()
        self.model.add(LSTM(neurons, batch_input_shape=[1, 1, 1], stateful=True))
        self.model.add(Dense(1))
        self.model.compile(loss='mean_squared_error', optimizer='adam')

        # Create scaler fit to the training input
        self.scaler = PreservedScaler()

    def train(self, training_input, training_output, epochs=50):
        if len(training_input.shape) == 2:
            # Fit scaler before training model
            self.scaler.fit(training_input[0])
            # For each sample, go over the whole epoch of training
            for i, input_sample in enumerate(training_input):
                for _ in range(epochs):
                    output_sample = training_output[i]
                    input_sample = self.scaler.shrink(shape_3d(input_sample))
                    output_sample = self.scaler.shrink(shape_1d(output_sample))
                    self.model.fit(input_sample, output_sample, epochs=1, batch_size=1,
                            verbose=0, shuffle=False)
                    self.model.reset_states()
        elif len(training_input.shape) == 1:
            # Fit scaler before training model
            self.scaler.fit(training_input)
            # Train the model on the entire input sample per epoch
            for _ in range(epochs):
                self.model.fit(
                    self.scaler.shrink(shape_3d(training_input)),
                    self.scaler.shrink(shape_1d(training_output)),
                    epochs=1, batch_size=1, verbose=0, shuffle=False
                )
                self.model.reset_states()
        else:
            raise TypeError("Training input must be 1D or 2D with this model")

    def predict(self, input_value):
        scaled_output = self.model.predict(shape_3d(input_value), batch_size=1)
        return shape_0d(self.scaler.regrow(scaled_output))


class PreservedScaler:
    def __init__(self, arr=None, *, feature_range=(-1,1)):
        self.scaler = MinMaxScaler(feature_range=feature_range)
        if arr is not None:
            self.fit(arr)

    def fit(self, arr):
        self.scaler.fit(shape_2d(arr))

    def shrink(self, arr):
        shaper = get_shaper(arr)
        return shaper(self.scaler.transform(shape_2d(arr)))

    def regrow(self, arr):
        shaper = get_shaper(arr)
        return shaper(self.scaler.inverse_transform(shape_2d(arr)))


def get_shaper(arr):
    return partial(shape_nd, n=len(standardize_array(arr).shape))


def standardize_array(arr):
    if isinstance(arr, pandas.DataFrame):
        return arr.values
    elif isinstance(arr, numpy.ndarray):
        return arr
    elif isinstance(arr, (list, set, dict)):
        return pandas.DataFrame(arr).values
    else:
        return pandas.DataFrame([arr]).values


def shape_3d(arr):
    arr = standardize_array(arr)
    return arr.reshape((len(arr), 1, 1))


def shape_2d(arr):
    arr = standardize_array(arr)
    return arr.reshape((len(arr), 1))


def shape_1d(arr):
    arr = standardize_array(arr)
    return arr.reshape((len(arr),))


def shape_0d(arr):
    arr = shape_1d(arr)
    if len(arr) != 1:
        raise ValueError("This array hold too many values to collapse to 0d")
    return arr[0]


def shape_nd(arr, n):
    arr = standardize_array(arr)
    dimensions = [len(arr)]
    for _ in range(1, n):
        dimensions.append(1)
    return arr.reshape(dimensions)


def display_directions(arr):
    for value in arr:
        if value < 0:
            symbol = '🡓'
        elif value > 0:
            symbol = '🡑'
        else:
            symbol = '='
        print(symbol, end='')
    print()


def test_main():
    parser = ArgumentParser()
    parser.add_argument("-n", "--neurons", type=int, default=1)
    parser.add_argument("-e", "--epochs", type=int, default=50)
    args = parser.parse_args()

    # Load data from file
    with open("data/snapshots.json") as f:
        snapshots = json.load(f)

    # Take the difference at each timestep (~30 days)
    data = []
    for values in snapshots.values():
        datum = []
        prev = None
        for value in values:
            if prev is not None:
                datum.append(value - prev)
            prev = value
        data.append(datum)

    # Split values into training and testing values
    training_cutoff = int(0.8 * len(values))
    training_data = [datum[:training_cutoff] for datum in data]
    testing_data = [datum[training_cutoff:] for datum in data]

    # Split training values into input and output
    training_input = pandas.DataFrame(datum[:-1] for datum in training_data).values
    training_output = pandas.DataFrame(datum[1:] for datum in training_data).values

    # Split testing values into input and output
    testing_input = pandas.DataFrame(datum[:-1] for datum in testing_data).values
    testing_output = pandas.DataFrame(datum[1:] for datum in testing_data).values

    print("----------------")
    print("Compiling model.")
    print("----------------")

    model = ExpenseModel(neurons=args.neurons)

    print("---------------")
    print("Training model.")
    print("---------------")

    model.train(training_input, training_output, epochs=args.epochs)
    
    print("-------------------")
    print("Making predictions.")
    print("-------------------")

    # Make predictions
    predictions = []
    expectations = []

    for i, input_sample in enumerate(testing_input):
        # Shape the testing input and output to simple arrays for iterating over
        input_sample = shape_1d(input_sample)
        output_sample = shape_1d(testing_output[i])

        # Make predictions
        for j, value in enumerate(input_sample):
            predictions.append(model.predict(value))
            expectations.append(output_sample[j])

    # Compare the predictions to the expected outputs for accuracy
    print("Prediction Directions:")
    display_directions(predictions)
    print("Expectation Directions:")
    display_directions(expectations)
    print("RMSE: ", mean_squared_error(expectations, predictions) ** 0.5)


if __name__ == '__main__':
    test_main()
