import time
import config
import logging
import numpy as np
import slack

from moving_average import MovingAverageCalculation
from OrderBook import OrderBookConsole
from decimal import Decimal
from datetime import datetime

# Logging Settings

logging.basicConfig(filename='mynewlog.log', level=logging.DEBUG)
logging.info('Start Logging')


# #logging.basicConfig(filename='example.log', level=logging.DEBUG)
# logging = logging.getlogging('simple_example')
# logging.setLevel(logging.DEBUG)
# 
# # Create file handler which logs even debug messages
# fh = logging.FileHandler("fullLog_" + time.strftime("%Y%m%d_%H%M%S") + ".log")
# fh.setLevel(logging.DEBUG)
# 
# # Create console handler with a higher Log Level
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# 
# # Create formatter and add it to the handlers
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# ch.setFormatter(formatter)
# formatter2 = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# fh.setFormatter(formatter2)
# 
# # add the handlers to logging
# logging.addHandler(ch)
# logging.addHandler(fh)


# Log my Keys
my_user_id = config.my_user_id
myKeys = config.live
logging.info("My keys are: ")
for key, value in myKeys.items():
    logging.info(key + ": " + value)
logging.info("My user_id is: " + my_user_id)

# Start Up OrderBook
order_book = OrderBookConsole(product_id='BTC-USD', keys=myKeys)
order_book.auth = True
order_book.api_key = myKeys['key']
order_book.api_secret = myKeys['secret']
order_book.api_passphrase = myKeys['passphrase']
order_book.start()

# Moving Average Initialization. Using 4 hour MA.
my_MA = MovingAverageCalculation(window=25200, std_window=25200)
status_message_count = 0
stale_message_count = -1
loop_count = 0
timer_count = 0
while order_book.message_count < 1000000000000:
    loop_count += 1
    my_MA.count += 1
    sma = my_MA.add_value(order_book.trade_price)
    if sma != None:
        if my_MA.count > 30:
            order_book.sma = sma
            order_book.valid_sma = True
            order_book.short_std = my_MA.get_weighted_std(5*60) * 2 
            order_book.long_std = my_MA.get_weighted_std(30*60)
            logging.info('Price: ' + order_book.trade_price + '\tPnL: {:.2f}\tNP: {:.1f}\tSMA: {:.2f}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}\t5_wStd: {:.2f}\t30_wStd: {:.2f}'.format(order_book.get_pnl(), order_book.net_position, order_book.sma, order_book.bid_theo, order_book.ask_theo, order_book.short_std, order_book.long_std))
        
        else:
            logging.info("Still Initializing. MA Count: " + str(my_MA.count) + "")
            logging.info('SMA: {:.2f}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}'.format(sma, order_book.bid_theo, order_book.ask_theo))
    
    time.sleep(1)
    
    if ((loop_count - timer_count)>15):
        timer_count = loop_count
        logging.warning("Checking order book connection. Message Count: "+str(order_book.message_count)+". Stale Count: " + str(stale_message_count))
        if order_book.message_count==stale_message_count:
            if config.connection_notifications:
                slack.send_message_to_slack("Connection has stopped. Restarting.")
            
            buy_levels = order_book.buy_levels
            sell_levels = order_book.sell_levels
            current_pnl = order_book.pnl
            order_book = OrderBookConsole(product_id='BTC-USD', keys=myKeys)
            order_book.buy_levels = buy_levels
            order_book.sell_levels = sell_levels
            order_book.net_position = buy_levels-sell_levels
            order_book.pnl = current_pnl
            order_book.auth = True
            order_book.api_key = myKeys['key']
            order_book.api_secret = myKeys['secret']
            order_book.api_passphrase = myKeys['passphrase']
            order_book.start()
            stale_message_count=-1
        stale_message_count=order_book.message_count
    
    # Print Status Message:
    if (my_MA.count - status_message_count) > 30:
        status_message_count = my_MA.count
        logging.warning("-----Printing Status Message: -----")
        logging.warning("Net Position: " + str(order_book.net_position))
        logging.warning("Num Buy Levels: " + str(order_book.buy_levels))
        logging.warning("Num Sell Levels: " + str(order_book.sell_levels))

order_book.close()
