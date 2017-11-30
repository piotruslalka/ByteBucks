import time
import datetime as dt
import config
import logging
import numpy as np
import twitter
import slack

from MyFillOrderBook import MyFillOrderBook
from gdax import OrderBook
from decimal import Decimal

# Logging Settings
#logging.basicConfig(filename='example.log', level=logging.DEBUG)
logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)

# Create file handler which logs even debug messages
fh = logging.FileHandler('fullLog.log')
fh.setLevel(logging.DEBUG)

# Create console handler with a higher Log Level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add the handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)



class MovingAverageCalculation(object):
    """ A moving average class """
    
    def __init__(self, window=10):
        self.data = []
        self.window = window
        self.count = 0
        
    def add_value(self, trade_price):
        if trade_price == None:
            logger.info("We don't have a valid price yet.")
            self.count = 0
            
        else:
            trade_price = float(trade_price)
            if len(self.data) < self.window:
                # Start up with window
                while len(self.data) < self.window:
                    self.data.append(trade_price)
                
                weights = np.repeat(1.0, self.window)/self.window
                smas = np.convolve(self.data, weights, 'valid')
                return (smas[-1])
            
            else:
                self.data.append(trade_price)
                weights = np.repeat(1.0, self.window)/self.window
                smas = np.convolve(self.data, weights, 'valid')
    
                #Remove old data
                if len(self.data) > self.window:
                    del self.data[0]
                    logger.debug("Removing old data from MA.")
                            
                return (smas[-1])
            
        
class OrderBookConsole(OrderBook):
    ''' Logs real-time changes to the bid-ask spread to the console '''

    def __init__(self, product_id=None, keys=None):
        super(OrderBookConsole, self).__init__(product_id=product_id)

        # latest values of bid-ask spread
        self._bid = None
        self._ask = None
        self._bid_depth = None
        self._ask_depth = None
        self._spread = None
        self.trade_price = None
        self.trade_size = None
        self.trade_side = None
        self.message_count = 0
        self.sma = None
        self.valid_sma = False
        self.buy_initial_offset = 25
        self.sell_initial_offset = 25
        self.buy_additional_offset = 2
        self.sell_additional_offset = 2
        self.bid_theo = 0
        self.ask_theo = 0
        self.net_position = 0
        self.buy_levels = 0
        self.sell_levels = 0
        self.num_rejections = 0
        self.min_tick = round(Decimal(0.01), 2)
        self.myKeys = keys
        self.auth_client = MyFillOrderBook(self.myKeys['key'], self.myKeys['secret'], self.myKeys['passphrase'])
        

    def on_message(self, message):
        super(OrderBookConsole, self).on_message(message)
            
        self.message_count += 1    
        logger.debug("Message Count: " + str(self.message_count))

        # Calculate newest bid-ask spread
        bid = self.get_bid()
        bids = self.get_bids(bid)
        bid_depth = sum([b['size'] for b in bids])
        ask = self.get_ask()
        asks = self.get_asks(ask)
        ask_depth = sum([a['size'] for a in asks])
        
        # Update Best Bid and Ask if there is a change    
        if self._bid == bid and self._ask == ask and self._bid_depth == bid_depth and self._ask_depth == ask_depth:
            # If there are no changes to the bid-ask spread since the last update, no need to print
            pass
        else:
            # If there are differences, update the cache
            self._bid = bid
            self._ask = ask
            self._bid_depth = bid_depth
            self._ask_depth = ask_depth
            self._spread =  ask - bid
            logger.debug('bid: {:.3f} @ {:.2f}\task: {:.3f} @ {:.2f}\tspread: {:.2f}'.format(bid_depth, bid, ask_depth, ask, self._spread))
            
            # Since the bid/ask changed. Let's see if we need to place a trade.
            if self.valid_sma:
                # Update Theos
                self.net_position = self.buy_levels - self.sell_levels
    
                if self.net_position == 0:
                    # We are flat
                    self.bid_theo = self.sma - self.buy_initial_offset
                    self.ask_theo = self.sma + self.sell_initial_offset
                    
                elif self.net_position > 0:
                    # We are long
                    if self.net_position > 2:
                        self.bid_theo = self.sma - (self.buy_initial_offset * abs(self.net_position + 1)) - (self.buy_additional_offset * (self.net_position + 1 * self.net_position + 1))
                        self.ask_theo = self.sma - (self.buy_initial_offset * abs(self.net_position + 1) * 0.5) - (self.buy_additional_offset * ((self.net_position + 1 - 2) * (self.net_position + 1 - 2)))
                    
                    else:
                        self.bid_theo = self.sma - self.buy_initial_offset * abs(self.net_position + 1) - (self.buy_additional_offset * (self.net_position + 1 * self.net_position + 1))
                        self.ask_theo = self.sma
                    
                else:
                    # We are short
                    if self.net_position < -2:
                        self.ask_theo = self.sma + (self.sell_initial_offset * abs(self.net_position - 1)) + (self.sell_additional_offset * (self.net_position - 1 * self.net_position - 1))
                        self.bid_theo = self.sma + (self.sell_initial_offset * abs(self.net_position - 1) * 0.5) + (self.sell_additional_offset * ((self.net_position - 1 + 2) * (self.net_position - 1 + 2)))
                        
                    else:                
                        self.ask_theo = self.sma + self.sell_initial_offset * abs(self.net_position - 1) + (self.sell_additional_offset * (self.net_position - 1 * self.net_position - 1))
                        self.bid_theo = self.sma
                    
                logger.debug('Net Position: {}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}'.format(self.net_position, self.bid_theo, self.ask_theo)) 
                
                if ask < self.bid_theo:
                    # We want to place a Buy Order
                    logger.info("Ask is lower than Bid Theo, we are placing a Buy Order at:" + str(bid) + "\t" 
                             + "Ask: " + str(ask) + "\tBid Theo: " + str(self.bid_theo) + "\tSpread: " + str(self._spread))
                
                    if round(Decimal(self._spread), 2) == self.min_tick:
                        logger.info("Spread: " + str(self._spread))
                        clean_bid = '{:.2f}'.format(bid, 2)
                        logger.info("Order Price: " + clean_bid)
                        order_successful = self.auth_client.place_my_limit_order(side='buy', price=clean_bid)
                        if order_successful:
                            self.buy_levels += 1
                            logger.warning("Buy Levels: " + str(self.buy_levels))

                        else:
                            # Order did not go through... Try again.
                            logger.critical("Order Rejected... Trying again")
                            logger.critical("Market Bid/Ask: " + str(bid) + " / " + str(ask))

                    else:
                        logger.info("Spread > 0.01: " + str(self._spread))
                        #clean_bid = '{:.2f}'.format(bid + self.min_tick, 2)
                        clean_bid = '{:.2f}'.format(bid, 2)
                        logger.info("Order Price: " + clean_bid)
                        order_successful = self.auth_client.place_my_limit_order(side='buy', price=clean_bid)
                        if order_successful:
                            self.buy_levels += 1
                            logger.warning("Buy Levels: " + str(self.buy_levels))

                        else:
                            # Order did not go through... Try again.
                            logger.critical("Order Rejected... Trying again")
                            logger.critical("Market Bid/Ask: " + str(bid) + " / " + str(ask))

                if bid > self.ask_theo:
                    # We want to place a Sell Order
                    logger.info("Bid is Higher than Ask Theo, we are placing a Sell order at:" + str(ask) + "\t"
                                  + "Bid: " + str(bid) + "\tAsk Theo: " + str(self.ask_theo) + "\tSpread: " + str(self._spread))
                          
                    if round(Decimal(self._spread), 2) == self.min_tick:
                        logger.info("Spread: " + str(self._spread))
                        clean_ask = '{:.2f}'.format(ask, 2)
                        logger.info("Order Price: " + clean_ask)
                        order_successful = self.auth_client.place_my_limit_order(side='sell', price=clean_ask)
                        if order_successful:
                            self.sell_levels += 1
                            logger.warning("Sell Levels: " + str(self.sell_levels))
                            
                        else:
                            # Order did not go through... Try again.
                            logger.critical("Order Rejected... Trying again")
                            logger.critical("Market Bid/Ask: " + str(bid) + " / " + str(ask))

                    else:
                        logger.info("Spread > 0.01: " + str(self._spread))
                        #clean_ask = '{:.2f}'.format(ask - self.min_tick, 2)
                        clean_ask = '{:.2f}'.format(ask, 2)
                        logger.info("Order Price: " + clean_ask)
                        order_successful = self.auth_client.place_my_limit_order(side='sell', price=(clean_ask))
                        if order_successful:
                            self.sell_levels += 1
                            logger.warning("Sell Levels: " + str(self.sell_levels))
                            
                        else:
                            # Order did not go through... Try again
                            logger.critical("Order Rejected... Trying again")
                            logger.critical("Market Bid/Ask: " + str(bid) + " / " + str(ask))

            
        # See if there is a trade
        if message['type'] == 'match':
            self.trade_price = message['price']
            self.trade_size = message['size']
            self.trade_side = message['side']
            logger.info('Trade: {}: {:.3f} @ {:.2f}'.format(self.trade_side.title(), Decimal(self.trade_size), Decimal(self.trade_price)))

        # See if there is something from me
        if 'user_id' in message:
            logger.warning("user_id - " + message['user_id'] + " found in message.")
            for key, value in message.items():
                logger.debug(key + ": " + str(value) + "\n")
            
            if message['type'] == 'received':
                logger.warning("message_type - " + message['type'] + " found in message.")
                if message['order_type'] == 'limit':
                    # We entered a limit order
                    logger.warning("We've entered a limit order")
                    for key, value in message.items():
                        logger.warning(key + ": " + str(value) + "\n")

                    # Send the order to the orderbook
                    self.auth_client.add_my_order(message)
                else:
                    logger.critical("We had a message type 'received' with an order_type other than limit: " + message['order_type'])

            
            if message['type'] == 'match':
                self.auth_client.add_my_fill(message)
                logger.warning("Got a trade. trade_id: " + str(message['trade_id']))
                logger.warning("Sending Twitter Notification:")
                logger.warning(message)
                #my_notification = twitter.TwitterNotification(message = message)
                slack.construct_message(message = message)



    

# Log my Keys
my_user_id = config.my_user_id
myKeys = config.live
logger.info("My keys are: ")
for key, value in myKeys.items():
    logger.info(key + ": " + value)
logger.info("My user_id is: " + my_user_id)

# Start Up OrderBook
order_book = OrderBookConsole(product_id='BTC-USD', keys=myKeys)
order_book.auth = True
order_book.api_key = myKeys['key']
order_book.api_secret = myKeys['secret']
order_book.api_passphrase = myKeys['passphrase']
order_book.start()

# Moving Average Initialization. Using 4 hour MA.
my_MA = MovingAverageCalculation(window=25200)
status_message_count = 0
stale_message_count = 0

while order_book.message_count < 1000000000000:
    my_MA.count += 1
    sma = my_MA.add_value(order_book.trade_price)
    if sma != None:
        if my_MA.count > 30:
            order_book.valid_sma = True
            order_book.sma = sma
            logger.info('SMA: {:.2f}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}'.format(order_book.sma, order_book.bid_theo, order_book.ask_theo))
        else:
            logger.info("Still Initializing. MA Count: " + str(my_MA.count) + "")
            logger.info('SMA: {:.2f}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}'.format(sma, order_book.bid_theo, order_book.ask_theo))
    time.sleep(1)
    
    # Print Status Message
    if (my_MA.count - status_message_count) > 60:
        status_message_count = my_MA.count
        logger.warning("-----Printing Status Message: -----")
        logger.warning("Net Position: " + str(order_book.net_position))
        logger.warning("Num Buy Levels: " + str(order_book.buy_levels))
        logger.warning("Num Sell Levels: " + str(order_book.sell_levels))

        # See if we have stale data
        if (order_book.message_count > 0):
            if (stale_message_count == order_book.message_count):
                # We have stale data
                logger.critical("We have stale data. Quiting Program and sending a message")
                #my_notification = twitter.TwitterNotification(stale=True)
                slack.construct_message(stale=True)
                quit()
                
            else:
                logger.debug("Order Book Message Count: " + str(order_book.message_count))
                logger.debug("Stale Message Count: " + str(stale_message_count))
                stale_message_count = order_book.message_count

order_book.close()
