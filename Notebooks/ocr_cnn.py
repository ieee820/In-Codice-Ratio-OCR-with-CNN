import os.path
from IPython.display import Image
import numpy as np

# Keras
from keras.callbacks import ModelCheckpoint
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten
from keras.layers import Convolution2D, MaxPooling2D
from keras.utils import np_utils
from keras.preprocessing.image import ImageDataGenerator
from keras import backend as K
from keras.datasets import mnist

from util import Util
from preprocessing import preprocess_data

import dataset_generator as dataset

class OCR_NeuralNetwork:
    
    # Plot utils
    _u = Util()
    
    # Model
    _activation = "relu"
        
    # input image dimensions
    _img_rows, _img_cols = 34, 56
    _input_shape = (_img_rows, _img_cols, 1)

    # Image Data Generator
    _datagen = ImageDataGenerator(
                    rotation_range=30,
                    width_shift_range=0.05,
                    height_shift_range=0.05,
                    zoom_range=0.1,
                    horizontal_flip=False)
    
    # number of convolutional filters to use
    _nb_filters1 = 20
    _nb_filters2 = 40

    # size of pooling area for max pooling
    _pool_size1 = (2, 2)
    _pool_size2 = (3, 3)

    # convolution kernel size
    _kernel_size1 = (4, 4)
    _kernel_size2 = (5, 5)

    # dense layer size
    _dense_layer_size1 = 150

    # dropout rate
    _dropout = 0.15

    
    def __init__(self, nb_classes, nb_epochs=50, batch_size=128, 
                 model_dir="checkpoints", model_name="no_name"):
        self._model_name = model_name
        self._batch_size = batch_size
        self._nb_classes = nb_classes
        self._nb_epochs = nb_epochs
        self._model_path = os.path.join(model_dir, model_name + '.hdf5') 
        self._init_model()
        self.try_load_model_from_fs(verbose=0)
         
    # Initialization of a new model, it can be used to reset the neural net
    def _init_model(self):
        self._model = Sequential()

        self._model.add(Convolution2D(self._nb_filters1, self._kernel_size1[0], self._kernel_size1[1],
                                border_mode='valid',
                                input_shape=self._input_shape, name='covolution_1_' + str(self._nb_filters1) + '_filters'))
        self._model.add(Activation(self._activation, name='activation_1_' + self._activation))
        self._model.add(MaxPooling2D(pool_size=self._pool_size1, name='max_pooling_1_' + str(self._pool_size1) + '_pool_size'))
        self._model.add(Convolution2D(self._nb_filters2, self._kernel_size2[0], self._kernel_size2[1]))
        self._model.add(Activation(self._activation, name='activation_2_' + self._activation))
        self._model.add(MaxPooling2D(pool_size=self._pool_size2, name='max_pooling_1_' + str(self._pool_size2) + '_pool_size'))
        self._model.add(Dropout(self._dropout))

        self._model.add(Flatten())
        self._model.add(Dense(self._dense_layer_size1, name='fully_connected_1_' + str(self._dense_layer_size1) + '_neurons'))
        self._model.add(Activation(self._activation, name='activation_3_' + self._activation))
        self._model.add(Dropout(self._dropout))
        self._model.add(Dense(self._nb_classes, name='output_' + str(self._nb_classes) + '_neurons'))
        self._model.add(Activation('softmax', name='softmax'))

        self._model.compile(loss='categorical_crossentropy',
                      optimizer='adadelta',
                      metrics=['accuracy', 'precision', 'recall', 'mean_absolute_error'])

        self._history = None;
        self._history_cont = None;

    # Train the nerual net
    # params:  
    #   X_train, y_train X_test, y_test : self explanatory
    #   X_test, y_test : Needed to choose the best weights for the net
    #   forceRetrain : if true, reset the neural net
    #   verbose = 0 : self explanatory
    #   initial_epoch : not implemented yet
    #   window_size : Choose the number of epoch with image processing
    #   seed : self explanatory
    def fit(self, X_train, y_train, X_test, y_test, forceRetrain = True, 
        verbose = 0, initial_epoch = 0, window_size=(-1), seed=1337):

        if(forceRetrain):
            ## delete only if file exists ##
            if os.path.exists(self._model_path):
                os.remove(self._model_path)
            else:
                print("Older Neural Net could not be found, creating a new net...")

            self._init_model()
        # If it is not loaded yet, try load it from fs and create a new model
        else:
            self.try_load_model_from_fs()

        if window_size == (-1):
             window_size = 10 + np.random.randint(40)

        if window_size >= self._nb_epochs:
             window_size = self._nb_epochs - 1

        print("Not pre-processing " + str(window_size) + " epoch(s)")

        # Preprocess input
        X_train,y_train,self._input_shape = preprocess_data(X_train, y_train, self._nb_classes, 
            img_rows=self._img_rows, img_cols=self._img_cols, verbose=verbose)
        X_test, y_test, _ = preprocess_data(X_test, y_test, self._nb_classes, 
            img_rows=self._img_rows, img_cols=self._img_cols, verbose=verbose)
        
        # checkpoint
        checkpoint = ModelCheckpoint(self._model_path, monitor='val_acc', verbose=verbose, save_best_only=True, mode='max')
        callbacks_list = [checkpoint]

        # compute quantities required for featurewise normalization
        # (std, mean, and principal components if ZCA whitening is applied)
        self._datagen.fit(X_train)

        flow = self._datagen.flow(X_train, y_train, batch_size=self._batch_size, seed=seed)

        self._history = self._model.fit_generator(flow, samples_per_epoch=len(X_train),
                 nb_epoch=(self._nb_epochs-window_size), verbose=verbose, validation_data=(X_test, y_test), 
                 callbacks=callbacks_list)

        # ensuring best val_precision reached during training
        self.try_load_model_from_fs()

        # fits the model on clear training set, for nb_epoch-700 epochs
        self._history_cont = self._model.fit(X_train, y_train, batch_size=self._batch_size, nb_epoch=window_size,
                                        verbose=verbose, validation_data=(X_test, y_test), 
                                        callbacks=callbacks_list)

        # ensuring best val_precision reached during training
        self.try_load_model_from_fs()

        return self._history, self._history_cont

    def try_load_model_from_fs(self, verbose=1):
        # loading weights from checkpoints 
        if os.path.exists(self._model_path):
            self._model.load_weights(self._model_path)
        elif verbose == 1:
            print("Previous Model Not Found")
        
    def evaluate(self, X_test, y_test, verbose = 0):
        X, y, _ = self._preprocess_data(X_test, y_test, self._nb_classes,
            img_rows=self._img_rows, img_cols=self._img_cols, verbose=verbose)

        score = self._model.evaluate(X, y, verbose = verbose)

        print('Test score:', score[0])
        print('Test accuracy:', score[1])
        print('Test error:', (1-score[2])*100, '%')
        return score
        
    def predict(self, X_test):
        X_test, _, _ = self._preprocess_data(X_test, [], self._nb_classes,
            img_rows=self._img_rows, img_cols=self._img_cols, verbose=verbose)

        return self._model.predict_classes(X_test)

    # Need to fix the range of the axis
    def plot_history(self):
        if not self._history and not self._history_cont:
            print("You need to train the model first!")
            return

        print("History: ")
        self._u.plot_history(self._history)
        self._u.plot_history(self._history, 'precision')
        print("Continuation of training with no pre-processing:")
        self._u.plot_history(self._history_cont)
        self._u.plot_history(self._history_cont, 'precision')


def main():
    ## Fast Usage
    
    # Prepare the dataset
    (X_train, y_train), (X_test, y_test) = mnist.load_data()

    # Initialization
    nn = OCR_NeuralNetwork(10, nb_epochs=2, model_dir="checkpoints", model_name="test", batch_size=128)

    # Training
    history = nn.fit(X_train, y_train, X_test, y_test, forceRetrain=False, window_size=1)

    # Prediciton
    predicted = nn.predict(X_test)

    # Evaluation
    score = nn.evaluate(X_test, y_test, verbose=1)

    nn.plot_history()


# Execute the module if it is main
if __name__ == "__main__":
    main()
