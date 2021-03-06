#!/usr/bin/env python3

import json
import numpy
import pandas
from argparse import ArgumentParser
from functools import partial
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error


class StockModel:
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

    def save(self, path):
        self.model.save(path)

    @classmethod
    def load(cls, path):
        from tensorflow import keras
        obj = cls()
        obj.model = keras.models.load_model(path)
        return obj

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

    def predict_verbose(self, input_sequence):
        # Convert the inputs to differences
        differences = []
        for i in range(1, len(input_sequence)):
            differences.append(input_sequence[i] - input_sequence[i - 1])

        # Scale the inputs down
        self.scaler.fit(differences)
        scaled_values = self.scaler.shrink(differences)

        # Make predictions
        expectations = scaled_values[1:]
        predictions = []
        for input_value in scaled_values[:-1]:
            scaled_output = self.model.predict(shape_3d(input_value), batch_size=1)
            predictions.append(shape_0d(scaled_output))

        # Scale the inputs and outputs up
        expectations = self.scaler.regrow(expectations)
        predictions = self.scaler.regrow(predictions)

        # Return the expected values and predictions made
        return predictions, expectations

    def predict(self, input_sequence):
        # Convert the inputs to differences
        differences = []
        for i in range(1, len(input_sequence)):
            differences.append(input_sequence[i] - input_sequence[i - 1])

        # Scale the inputs down
        self.scaler.fit(differences)
        scaled_values = self.scaler.shrink(differences)

        # Make predictions
        for input_value in scaled_values:
            scaled_output = self.model.predict(shape_3d(input_value), batch_size=1)

        # Return the rescaled output
        return input_sequence[-1] + shape_0d(self.scaler.regrow(scaled_output))


class PreservedScaler:
    def __init__(self, arr=None, *, feature_range=(0,1)):
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
            symbol = '????'
        elif value > 0:
            symbol = '????'
        else:
            symbol = '='
        print(symbol, end='')
    print()


def perform_test(args):
    # Load data from file
    with open("data/snapshots.json") as f:
        snapshots = json.load(f)

    # Take the difference at each timestep
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

    model = StockModel(neurons=args.neurons)

    print("---------------")
    print("Training model.")
    print("---------------")

    model.train(training_input, training_output, epochs=args.epochs)
    
    print("-------------------")
    print("Making predictions.")
    print("-------------------")

    # Gather predictions and expectations for each sample
    predictions = []
    expectations = []
    for input_sample in testing_input:
        sub_predictions, sub_expectations = model.predict_verbose(input_sample)
        predictions.extend(sub_predictions)
        expectations.extend(sub_expectations)

    print("RMSE: ", mean_squared_error(expectations, predictions) ** 0.5)


def create_model(args):
    # Load data from file
    with open("data/snapshots.json") as f:
        snapshots = json.load(f)

    # Take the difference at each timestep
    data = []
    for values in snapshots.values():
        datum = []
        prev = None
        for value in values:
            if prev is not None:
                datum.append(value - prev)
            prev = value
        data.append(datum)

    # Split training values into input and output
    training_input = pandas.DataFrame(datum[:-1] for datum in data).values
    training_output = pandas.DataFrame(datum[1:] for datum in data).values

    print("----------------")
    print("Compiling model.")
    print("----------------")

    model = StockModel(neurons=args.neurons)

    print("---------------")
    print("Training model.")
    print("---------------")

    model.train(training_input, training_output, epochs=args.epochs)

    # Save model to disk for later
    model.save(args.save_path)


def main():
    parser = ArgumentParser()
    parser.add_argument("-n", "--neurons", type=int, default=1)
    parser.add_argument("-e", "--epochs", type=int, default=50)
    parser.add_argument("-m", "--mode", choices=['test', 'create_model'], default='test')
    parser.add_argument("-p", "--save-path", default='./appdata/model/stock_lstm')
    args = parser.parse_args()

    if args.mode == 'test':
        perform_test(args)
    elif args.mode == 'create_model':
        create_model(args)


if __name__ == '__main__':
    main()
