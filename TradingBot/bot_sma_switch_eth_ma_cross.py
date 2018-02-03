import time
import config
import logging
import numpy as np
import slack
import os.path

from moving_average import MovingAverageCalculation
from OrderBook import OrderBookConsole
from datetime import datetime

# Strategy Settings: Package Trade Settings as a dictionary so you can simply pass that into OrderBook
strategy_settings = {
    'product_id': 'ETH-USD',
    'min_tick': 0.01,
    'strategy_name': "bot_sma_cross_stable",
    'order_size': 0.01,
    'set_ma_value': True,
    'manual_ma_value': 885.69,
    'min_size_for_order_update': 0,
    'min_distance_for_order_update': 0,
    'buy_initial_offset': 5,
    'sell_initial_offset': 10,
    'sma_cross_diff': 0.5,
    'break_out_level_add': 50,
    'break_out_level_reduce': 50,
    'sell_max_initial_profit_target': 50000,
    'buy_max_initial_profit_target': 50000,
    'max_long_position': 10000,
    'max_short_position': 10000,
    'sma_swap_trigger_level': 10000,
    'sma_long_duration': 4*60,
    'sma_cross_short_duration': 5,
    'sma_cross_long_duration': 15,
    'std_long_duration': 30,
    'std_short_duration': 5,
    'std_long_multiplier': 0.5,
    'std_short_multiplier': 2,
    'fill_notifications': True,
    'place_notifications': False,
    'connection_notifications': True,
}


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
handler = logging.FileHandler(os.path.join("C:", "error_" + strategy_settings.get('strategy_name') + "_" + time.strftime("%Y%m%d_%H%M%S") + ".log"),"w")
handler.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Create Debug file handler and set level to DEBUG
# handler = logging.FileHandler(os.path.join("C:", "debug_" + strategy_settings.get('strategy_name') + "_" + time.strftime("%Y%m%d_%H%M%S") + ".log"),"w")
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
# handler.setFormatter(formatter)
# logger.addHandler(handler)


# Log my Keys
my_user_id = config.my_user_id
myKeys = config.live
logger.info("My keys are: ")
for key, value in myKeys.items():
    logger.info(key + ": " + value)
logger.info("My user_id is: " + my_user_id)

# Moving Average Initialization.
my_MA = MovingAverageCalculation(period=strategy_settings.get('sma_long_duration')*60)

# Start Up OrderBook
order_book = OrderBookConsole(product_id=strategy_settings.get('product_id'), keys=myKeys, strategy_settings = strategy_settings)
order_book.auth_client.buy_levels = 0.60249643
order_book.auth_client.net_position = -9
current_price = 975.90
current_pnl = 22.04
order_book.auth_client.real_position = strategy_settings.get('order_size') * order_book.auth_client.net_position
order_book.auth_client.pnl = current_pnl - (order_book.auth_client.real_position * current_price)
order_book.auth_client.sell_levels = order_book.auth_client.buy_levels - order_book.auth_client.real_position
order_book.auth = True
order_book.api_key = myKeys['key']
order_book.api_secret = myKeys['secret']
order_book.api_passphrase = myKeys['passphrase']
order_book.start()

status_message_count = 0
stale_message_count = -1
loop_count = 0
timer_count = 0
use_long_sma = True
reset_not_triggered = True
while order_book.message_count < 1000000000000:
    loop_count += 1
    my_MA.count += 1

    if strategy_settings.get('set_ma_value') == True:
        my_MA.add_value(order_book.trade_price)
        long_sma = strategy_settings.get('manual_ma_value')
    else:
        long_sma = my_MA.add_value(order_book.trade_price)


    if order_book.num_order_rejects > 0:
        logger.warning("Setting Rejects back to 0")
        order_book.num_order_rejects = 0

    if long_sma != None:
        if my_MA.count > 30 and order_book.trade_price != None:
            sma_cross_short = my_MA.get_sma(strategy_settings.get('sma_cross_short_duration')*60)
            sma_cross_long = my_MA.get_sma(strategy_settings.get('sma_cross_long_duration')*60)

            order_book.sma_cross_short = sma_cross_short
            order_book.sma_cross_long = sma_cross_long

            order_book.sma = long_sma
            order_book.valid_sma = True

            order_book.short_std = my_MA.get_weighted_std(strategy_settings.get('std_short_duration')*60) * strategy_settings.get('std_short_multiplier')
            order_book.long_std = my_MA.get_weighted_std(strategy_settings.get('std_long_duration')*60) * strategy_settings.get('std_long_multiplier')
            logger.debug('Price: {:.2f}'.format(float(order_book.trade_price)))
            logger.debug('PnL: {:.2f}'.format(order_book.get_pnl()))
            logger.debug('NP: {:.1f}'.format(order_book.auth_client.net_position))
            logger.debug('SMA: {:.2f}'.format(order_book.sma))
            logger.debug('Bid Theo: {:.2f}'.format(order_book.bid_theo))
            logger.debug('Ask Theo: {:.2f}'.format(order_book.ask_theo))
            logger.debug('5_wStd: {:.2f}'.format(order_book.short_std))
            logger.debug('30_wStd: {:.2f}'.format(order_book.long_std))
            logger.info('Price: {:.2f}\tPnL: {:.2f}\tNP: {:.1f}\tSMA: {:.2f}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}\t5_wStd: {:.2f}\t30_wStd: {:.2f}\tsSMA: {:.2f}\tlSMA: {:.2f}'.format(float(order_book.trade_price), order_book.get_pnl(), order_book.auth_client.net_position, order_book.sma, order_book.bid_theo, order_book.ask_theo, order_book.short_std, order_book.long_std, order_book.sma_cross_short, order_book.sma_cross_long))

        else:
            logger.info("Still Initializing. MA Count: " + str(my_MA.count) + "")
            logger.info('SMA: {:.2f}\tBid Theo: {:.2f}\tAsk Theo: {:.2f}'.format(long_sma, order_book.bid_theo, order_book.ask_theo))

    time.sleep(1)

    if order_book.stop and reset_not_triggered:
            reset_not_triggered = False
            if strategy_settings.get('connection_notifications'):
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
            order_book = OrderBookConsole(product_id=strategy_settings.get('product_id'), keys=myKeys, strategy_settings = strategy_settings)
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
            try:
                order_book.auth_client.verify_orders()
            except:
                logger.error("Unexpected error: " + str(sys.exc_info()[0]))
            order_book.start()
            timer_count = loop_count

    if ((loop_count - timer_count) > 30):
        reset_not_triggered = True
        if(order_book.message_count == 0):
            logger.critical("GDAX connection problem. Pausing 60 seconds.")
            time.sleep(60)
        timer_count = loop_count
        logger.info("Checking order book connection. Message Count: "+str(order_book.message_count)+". Stale Count: " + str(stale_message_count))
        if order_book.message_count==stale_message_count:
            if strategy_settings.get('connection_notifications'):
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
            order_book = OrderBookConsole(product_id=strategy_settings.get('product_id'), keys=myKeys, strategy_settings = strategy_settings)
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
            try:
                order_book.auth_client.verify_orders()
            except:
                logger.error("Unexpected error: " + str(sys.exc_info()[0]))
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
