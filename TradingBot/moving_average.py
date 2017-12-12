import numpy as np
import random
import time
import logging
from math import sqrt

# Logging Settings
logger = logging.getLogger('botLog')


class MovingAverageCalculation(object):
    """ A moving average class """
    
    def __init__(self, period=1*60):
        
        logger.info("Entered into the MovingAverageCalculation Class!")
                
        self.data = []
        self.period = period
        self.count = 0
        
    def add_value(self, trade_price):
        if trade_price == None:
            logger.info("We don't have a valid price yet.")
            #self.count = 0
            
        else:
            trade_price = float(trade_price)
            if len(self.data) < self.period:
                # Start up with window
                while len(self.data) < self.period:
                    self.data.append(trade_price)
                
                weights = np.repeat(1.0, self.period)/self.period
                smas = np.convolve(self.data, weights, 'valid')
                return (smas[-1])
            
            else:
                self.data.append(trade_price)
                weights = np.repeat(1.0, self.period)/self.period
                smas = np.convolve(self.data, weights, 'valid')
    
                #Remove old data
                if len(self.data) > self.period:
                    del self.data[0]
                    #logger.debug("Removing old data from MA.")
                            
                return (smas[-1])
            
    def get_sma(self, window=None):
        if window == None:
            window = self.period
        sma = np.mean(self.data[(len(self.data)-window):len(self.data)])
        return (sma)
    
    def get_std(self, window):
        std = np.std(self.data[len(self.data)-min(window, self.count):len(self.data)])
        return (std)
    
    def get_weighted_std(self, window):
        data_points = min(window, self.count)
        weights = np.arange(data_points)
        mean = np.average(self.data[(len(self.data)-data_points):len(self.data)], weights = weights)
        variance = np.average((self.data[(len(self.data)-data_points):len(self.data)]-mean)**2, weights=weights)
        std = sqrt(variance)
        return (std)

# if __name__ == '__main__':
#     while my_MA.count < 1000:
#         # Logging Settings
#         #logging.basicConfig(filename='example.log', level=logging.DEBUG)
#         logger = logging.getLogger('ma_test')
#         logger.setLevel(logging.DEBUG)
#         if (my_MA.count < 10):
#             trade_price = 1000
#         else:
#             trade_price = 5000
#     
#         print("Last Trade Price was " + str(trade_price))
#         my_MA.count += 1
#         
#         sma = my_MA.add_value(trade_price)
#         
#         print("MA IS : " + str(sma))
#         print("MA Count: " + str(my_MA.count) + "\n")
#         
#         time.sleep(.5)
    
