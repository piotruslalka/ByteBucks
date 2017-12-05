import logging
import config

from MyFillOrderBook import MyFillOrderBook
from gdax import OrderBook

from decimal import Decimal
from datetime import datetime

logger = logging.getLogger('botLog')


class OrderBookConsole(OrderBook):
    ''' Logs real-time changes to the bid-ask spread to the console '''

    def __init__(self, product_id=None, keys=None):
        super(OrderBookConsole, self).__init__(product_id=product_id)

        logger.info("Entered into the OrderBook Class!")

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
        self.short_std = 0
        self.long_std = 0
        self.order_size = config.order_size
        self.buy_initial_offset = config.buy_initial_offset
        self.sell_initial_offset = config.sell_initial_offset
        self.buy_additional_offset = config.buy_additional_offset
        self.sell_additional_offset = config.sell_additional_offset
        self.bid_theo = 0
        self.ask_theo = 0
        self.net_position = 0
        self.buy_levels = 0
        self.sell_levels = 0
        self.outstanding_buy_orders = 0
        self.outstanding_sell_orders = 0
        self.pnl = 0
        self.num_rejections = 0
        self.min_tick = round(Decimal(0.01), 2)
        self.myKeys = keys
        self.auth_client = MyFillOrderBook(self.myKeys['key'], self.myKeys['secret'], self.myKeys['passphrase'])
        
        logger.info("Settings Used:")
        logger.info("Order Size: {}\tBuy Initial Offset: {}\tSell Initial Offset: {}\tBuy Additional Offset: {}\tSell Additional Offset: {}".format(self.order_size, self.buy_initial_offset, self.sell_initial_offset, self.buy_additional_offset, self.sell_additional_offset))

    def on_message(self, message):
        super(OrderBookConsole, self).on_message(message)
            
        self.message_count += 1    

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
            logger.debug('Bid/Ask Updated - Bid: {:.3f} @ {:.2f}\tAsk: {:.3f} @ {:.2f}\tSpread: {:.2f}'.format(bid_depth, bid, ask_depth, ask, self._spread))
            
            # See if we need to place a trade
            self.on_bidask_update()
    
        # See if there is a trade in websocket data
        if message['type'] == 'match':
            self.trade_price = message['price']
            self.trade_size = message['size']
            self.trade_side = message['side']
            logger.info('Trade: {}: {:.3f} @ {:.2f}'.format(self.trade_side.title(), Decimal(self.trade_size), Decimal(self.trade_price)))
    
        # See if something private came in the message (authenticated data)
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
                logger.warning("Sending Slack Notification:")
                logger.warning(message)
                if config.fill_notifications:
                    slack.send_message_to_slack("Filled - {} {:.3f} @ {:.2f} {}".format(message['side'].title(), Decimal(message['size']), Decimal(message['price']), str(datetime.now())))
                
            
    def on_bidask_update(self):
        # Since the bid/ask changed. Let's see if we need to place a trade.
        
        if self.valid_sma:
            self.update_theos()            
            self.check_if_action_needed()
            
    def update_theos(self):
        # Update Theos
        
        self.net_position = self.buy_levels - self.sell_levels
        std_offset = max(self.short_std, self.long_std)
        
        if self.net_position == 0:
            # We are flat
            self.bid_theo = self.sma - self.buy_initial_offset - std_offset
            self.ask_theo = self.sma + self.sell_initial_offset + std_offset
            
        elif self.net_position > 0:
            # We are long
            if self.net_position > 2:
                self.bid_theo = self.sma - (self.buy_initial_offset * abs(self.net_position + 1)) - (self.buy_additional_offset * ((self.net_position + 1) * (self.net_position + 1))) - std_offset
                self.ask_theo = self.sma - (self.buy_initial_offset * abs(self.net_position + 1) * 0.75) - (self.buy_additional_offset * ((self.net_position + 1 - 2) * (self.net_position + 1 - 2)))
            
            else:
                self.bid_theo = self.sma - self.buy_initial_offset * abs(self.net_position + 1) - (self.buy_additional_offset * ((self.net_position + 1) * (self.net_position + 1))) - std_offset
                self.ask_theo = self.sma
            
        else:
            # We are short
            if self.net_position < -2:
                self.ask_theo = self.sma + (self.sell_initial_offset * abs(self.net_position - 1)) + (self.sell_additional_offset * ((self.net_position - 1) * (self.net_position - 1))) + std_offset
                self.bid_theo = self.sma + (self.sell_initial_offset * abs(self.net_position - 1) * 0.75) + (self.sell_additional_offset * ((self.net_position - 1 + 2) * (self.net_position - 1 + 2)))
                
            else:                
                self.ask_theo = self.sma + self.sell_initial_offset * abs(self.net_position - 1) + (self.sell_additional_offset * ((self.net_position - 1) * (self.net_position - 1))) + std_offset
                self.bid_theo = self.sma    
            
    def check_if_action_needed(self):
        # Check to see if we want to place any orders
        
        # Check to see if we already placed an order
        if (outstanding_buy_orders != 0):
            
        
        
        
        
            if self._ask < self.bid_theo:
                # We want to place a Buy Order
                logger.info("Ask is lower than Bid Theo, we are placing a Buy Order at:" + str(bid) + "\t" 
                         + "Ask: " + str(ask) + "\tBid Theo: " + str(self.bid_theo) + "\tSpread: " + str(self._spread))
            
                if round(Decimal(self._spread), 2) == self.min_tick:
                    logger.info("Spread: " + str(self._spread))
                    clean_bid = '{:.2f}'.format(bid, 2)
                    logger.info("Order Price: " + clean_bid)
                    order_successful = self.auth_client.place_my_limit_order(side='buy', price=clean_bid, size='{:.3f}'.format(self.order_size))
                    if order_successful:
                        self.buy_levels += 1
                        logger.warning("Buy Levels: " + str(self.buy_levels))
                        if config.place_notifications:
                            slack.send_message_to_slack("Placing - Buy {:.3f} @ {}\tSpread: {:.2f}\t{}".format(self.order_size, clean_bid, self._spread, str(datetime.now())))
                        
                        self.pnl -= Decimal(bid)*Decimal(self.order_size)
        
                    else:
                        # Order did not go through... Try again.
                        logger.critical("Order Rejected... Trying again")
                        logger.critical("Market Bid/Ask: " + str(bid) + " / " + str(ask))
        
                else:
                    logger.info("Spread > 0.01: " + str(self._spread))
                    #clean_bid = '{:.2f}'.format(bid + self.min_tick, 2)
                    clean_bid = '{:.2f}'.format(bid, 2)
                    logger.info("Order Price: " + clean_bid)
                    order_successful = self.auth_client.place_my_limit_order(side='buy', price=clean_bid, size='{:.3f}'.format(self.order_size))
                    if order_successful:
                        self.buy_levels += 1
                        logger.warning("Buy Levels: " + str(self.buy_levels))
                        if config.place_notifications:
                            slack.send_message_to_slack("Placing - Buy {:.3f} @ {}\tSpread: {:.2f}\t{}".format(self.order_size, clean_bid, self._spread, str(datetime.now())))
                        
                        self.pnl -= Decimal(bid)*Decimal(self.order_size)
        
                    else:
                        # Order did not go through... Try again.
                        logger.critical("Order Rejected... Trying again")
                        logger.critical("Market Bid/Ask: " + str(bid) + " / " + str(ask))
    
    
    
    
        if (self.outstanding_sell_orders != 0):
            if self._bid > self.ask_theo:
                # We want to place a Sell Order
                logger.info("Bid is Higher than Ask Theo, we are placing a Sell order at:" + str(ask) + "\t"
                              + "Bid: " + str(bid) + "\tAsk Theo: " + str(self.ask_theo) + "\tSpread: " + str(self._spread))
                      
                if round(Decimal(self._spread), 2) == self.min_tick:
                    logger.info("Spread: " + str(self._spread))
                    clean_ask = '{:.2f}'.format(ask, 2)
                    logger.info("Order Price: " + clean_ask)
                    order_successful = self.auth_client.place_my_limit_order(side='sell', price=clean_ask, size='{:.3f}'.format(self.order_size))
                    if order_successful:
                        self.sell_levels += 1
                        logger.warning("Sell Levels: " + str(self.sell_levels))
                        if config.place_notifications:
                            slack.send_message_to_slack("Placing - Sell {:.3f} @ {}\tSpread: {:.2f}\t{}".format(self.order_size, clean_ask, self._spread, str(datetime.now())))
                        
                        self.pnl += Decimal(ask)*Decimal(self.order_size)
                        
                    else:
                        # Order did not go through... Try again.
                        logger.critical("Order Rejected... Trying again")
                        logger.critical("Market Bid/Ask: " + str(bid) + " / " + str(ask))
        
                else:
                    logger.info("Spread > 0.01: " + str(self._spread))
                    #clean_ask = '{:.2f}'.format(ask - self.min_tick, 2)
                    clean_ask = '{:.2f}'.format(ask, 2)
                    logger.info("Order Price: " + clean_ask)
                    order_successful = self.auth_client.place_my_limit_order(side='sell', price=(clean_ask), size='{:.3f}'.format(self.order_size))
                    if order_successful:
                        self.sell_levels += 1
                        logger.warning("Sell Levels: " + str(self.sell_levels))
                        if config.place_notifications:
                            slack.send_message_to_slack("Placing - Sell {:.3f} @ {}\tSpread: {:.2f}\t{}".format(self.order_size, clean_ask, self._spread, str(datetime.now())))
                        
                        self.pnl += Decimal(ask)*Decimal(self.order_size)
                        
                    else:
                        # Order did not go through... Try again
                        logger.critical("Order Rejected... Trying again")
                        logger.critical("Market Bid/Ask: " + str(bid) + " / " + str(ask))
            
            
    def get_pnl(self):
        return self.pnl + self.net_position * Decimal(self.trade_price) * Decimal(self.order_size)
