import numpy as np
import random
import time
import logging

# Logging Settings
#logging.basicConfig(filename='example.log', level=logging.DEBUG)
logger = logging.getLogger('ma_test')
logger.setLevel(logging.DEBUG)



class MovingAverageCalculation(object):
    """ A moving average class """
    
    def __init__(self, window=60, initial_window = 10):
        self.data = []
        self.window = window
        self.count = 0
        self.initial_window = initial_window
        
    def add_value(self, trade_price):
        if trade_price == None:
            logger.info("We don't have a valid price yet.")
            self.count = 0
        else:
            trade_price = float(trade_price)
            self.data.append(trade_price)
            
            if len(self.data) > self.initial_window:
                if len(self.data) <= self.window:
                    weights = np.repeat(1.0, self.count)/self.count
                    smas = np.convolve(self.data, weights, 'valid')
                    return (smas[-1])
                else:
                    weights = np.repeat(1.0, self.window)/self.window
                    smas = np.convolve(self.data, weights, 'valid')
        
                    #Remove old data
                    if len(self.data) > self.window:
                        del self.data[0]
                        logger.debug("Removing old data from MA.")
                                
                    return (smas[-1])
        
        
        
my_MA = MovingAverageCalculation(window = 100)

while my_MA.count < 1000:
    if (my_MA.count < 10):
        trade_price = 1000
    else:
        trade_price = 5000

    print("Last Trade Price was " + str(trade_price))
    my_MA.count += 1
    
    sma = my_MA.add_value(trade_price)
    
    print("MA IS : " + str(sma))
    print("MA Count: " + str(my_MA.count) + "\n")
    
    time.sleep(.5)

