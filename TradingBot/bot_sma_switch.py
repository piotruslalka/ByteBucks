import time
import config
import logging
import numpy as np
import slack
import os.path

from moving_average import MovingAverageCalculation
from OrderBook import OrderBookConsole
from datetime import datetime

# Logging Settings
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create Console Handler and set level to INFO
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Create Error file handler and set level to ERROR
handler = logging.FileHandler(os.path.join("C:", "error_" + time.strftime("%Y%m%d_%H%M%S") + ".log"),"w")
handler.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Create Debug file handler and set level to DEBUG
handler = logging.FileHandler(os.path.join("C:", "debug_" + time.strftime("%Y%m%d_%H%M%S") + ".log"),"w")
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


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

# Moving Average Initialization. Using 3 hour MA.
my_MA = MovingAverageCalculation(period=4*60*60)
status_message_count = 0
stale_message_count = -1
loop_count = 0
timer_count = 0
use_long_sma = True
reset_not_triggered = True
while order_book.message_count < 1000000000000:
    loop_count += 1
    my_MA.count += 1
    long_sma = my_MA.add_value(order_book.trade_price)

    if order_book.num_order_rejects > 0:
        logger.critical("Setting Rejects back to 0")
        order_book.num_order_rejects = 0

    if long_sma != None:
        if my_MA.count > 30:
            short_sma =  my_MA.get_sma(30*60)
            if (order_book.auth_client.net_position > 19 and short_sma - long_sma < -5) or (order_book.auth_client.net_position < -19 and short_sma - long_sma > 5):
                use_long_sma = False
            elif abs(long_sma-short_sma) < 5:
                use_long_sma = True

            if use_long_sma:
                order_book.sma = long_sma
            else:
                order_book.sma = short_sma

            order_book.valid_sma = True
            order_book.short_std = my_MA.get_weighted_std(5*60) * 2
            order_book.long_std = my_MA.get_weighted_std(30*60) / 2
            #logger.info('RP:' + str(order_book.real_position) + ' pl:' + str(order_book.pnl) + ' NP:' + str(order_book.auth_client.net_position))
            logger.info('Price: {:.2f}\tPnL: {:.2f}\tNP: {:.1f}\tSMA: {:.2f}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}\t5_wStd: {:.2f}\t30_wStd: {:.2f}\tlSMA: {:.2f}\tsSMA: {:.2f}'.format(float(order_book.trade_price), order_book.get_pnl(), order_book.auth_client.net_position, order_book.sma, order_book.bid_theo, order_book.ask_theo, order_book.short_std, order_book.long_std, long_sma, short_sma))

        else:
            logger.info("Still Initializing. MA Count: " + str(my_MA.count) + "")
            logger.info('SMA: {:.2f}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}'.format(long_sma, order_book.bid_theo, order_book.ask_theo))

    time.sleep(1)

    if order_book.stop and reset_not_triggered:
            reset_not_triggered = False
            if config.connection_notifications:
                slack.send_message_to_slack("Connection has stopped. Restarting. Stop = True!")
                logger.error("Connection has stopped. Restarting. Stop = True!")

            # Copy Critical Info from dead order book
            buy_levels = order_book.auth_client.buy_levels
            sell_levels = order_book.auth_client.sell_levels
            real_position = order_book.auth_client.real_position
            net_position = order_book.auth_client.net_position
            current_pnl = order_book.auth_client.pnl
            current_bids = order_book.auth_client.my_buy_orders
            current_asks = order_book.auth_client.my_sell_orders
            order_book.close()

            # Populate New Order book with previously saved critical info.
            order_book = OrderBookConsole(product_id='BTC-USD', keys=myKeys)
            order_book.auth_client.buy_levels = buy_levels
            order_book.auth_client.sell_levels = sell_levels
            order_book.auth_client.real_position = real_position
            order_book.auth_client.net_position = net_position
            order_book.auth_client.pnl = current_pnl
            order_book.auth_client.my_buy_orders = current_bids
            order_book.auth_client.my_sell_orders = current_asks
            order_book.auth = True
            order_book.api_key = myKeys['key']
            order_book.api_secret = myKeys['secret']
            order_book.api_passphrase = myKeys['passphrase']
            order_book.auth_client.verify_orders()
            order_book.start()

    if ((loop_count - timer_count) > 15):
        reset_not_triggered = True
        if(order_book.message_count == 0):
            logger.critical("GDAX connection problem. Pausing 60 seconds.")
            time.sleep(60)
        timer_count = loop_count
        logger.info("Checking order book connection. Message Count: "+str(order_book.message_count)+". Stale Count: " + str(stale_message_count))
        if order_book.message_count==stale_message_count:
            if config.connection_notifications:
                slack.send_message_to_slack("Connection has stopped. Restarting.")
                logger.error("Connection has stopped. Restarting")

            # Copy Critical Info from dead order book
            buy_levels = order_book.auth_client.buy_levels
            sell_levels = order_book.auth_client.sell_levels
            real_position = order_book.auth_client.real_position
            net_position = order_book.auth_client.net_position
            current_pnl = order_book.auth_client.pnl
            current_bids = order_book.auth_client.my_buy_orders
            current_asks = order_book.auth_client.my_sell_orders
            order_book.close()

            # Populate New Order book with previously saved critical info.
            order_book = OrderBookConsole(product_id='BTC-USD', keys=myKeys)
            order_book.auth_client.buy_levels = buy_levels
            order_book.auth_client.sell_levels = sell_levels
            order_book.auth_client.real_position = real_position
            order_book.auth_client.net_position = net_position
            order_book.auth_client.pnl = current_pnl
            order_book.auth_client.my_buy_orders = current_bids
            order_book.auth_client.my_sell_orders = current_asks
            order_book.auth = True
            order_book.api_key = myKeys['key']
            order_book.api_secret = myKeys['secret']
            order_book.api_passphrase = myKeys['passphrase']
            order_book.auth_client.verify_orders()
            order_book.start()
            stale_message_count=-1
        stale_message_count=order_book.message_count

    # Print Status Message:
    if (my_MA.count - status_message_count) > 30:
        #TODO: Verify that no working orders have been missed.

        status_message_count = my_MA.count
        logger.info("-----Printing Status Message: -----")
        logger.info("Net Position: " + str(order_book.auth_client.net_position))
        logger.info("Num Buy Levels: " + str(order_book.auth_client.buy_levels))
        logger.info("Num Sell Levels: " + str(order_book.auth_client.sell_levels))

order_book.close()