class MovingAverageCalculation(object):
    """ A moving average class """
    
    def __init__(self, window=60):
        self.data = []
        self.window = window
        
    def add_value(self, trade_price):
        if trade_price == None:
            print("We don't have a valid price yet.")
        else:
            trade_price = float(trade_price)
            #print(str(trade_price))
            self.data.append(trade_price)
            #print("My MA contains " + str(len(self.data)) + " values.")
            #print(self.data)
            
            if len(self.data) <= self.window:
                print("We don't have enough data points yet...")
            else:
                weights = np.repeat(1.0, self.window)/self.window
                smas = np.convolve(self.data, weights, 'valid')
    
                #Remove old data
                if len(self.data) > self.window:
                    #print("Removing element: " + str(self.data[0]))
                    del self.data[0]
                return (smas[-1])
        