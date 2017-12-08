import logging
import config
import slack

from MyFillOrderBook import MyFillOrderBook
from gdax import OrderBook

#from decimal import Decimal
from datetime import datetime
from math import sqrt

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
        self.buy_profit_target_multiplier = 1
        self.sell_profit_target_multiplier = 1
        self.bid_theo = 0
        self.ask_theo = 0
        self.net_position = 0
        self.real_position = 0
        self.buy_levels = 0
        self.sell_levels = 0
        self.num_order_rejects = 0
        self.pnl = 0
        self.num_rejections = 0
        self.min_tick = round(0.01, 2)
        self.myKeys = keys
        self.auth_client = MyFillOrderBook(self.myKeys['key'], self.myKeys['secret'], self.myKeys['passphrase'])

        logger.info("Settings Used:")
        logger.info("Order Size: {}\tBuy Initial Offset: {}\tSell Initial Offset: {}\tBuy Additional Offset: {}\tSell Additional Offset: {}\tBuy Profit Target Mult: {}\tSell Profit Target Mult: {}".format(self.order_size, self.buy_initial_offset, self.sell_initial_offset, self.buy_additional_offset, self.sell_additional_offset, self.buy_profit_target_multiplier, self.sell_profit_target_multiplier))

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
            self._bid = float(bid)
            self._ask = float(ask)
            self._bid_depth = bid_depth
            self._ask_depth = ask_depth
            self._spread =  float(ask - bid)
            #logger.debug('Bid/Ask Updated - Bid: {:.3f} @ {:.2f}\tAsk: {:.3f} @ {:.2f}\tSpread: {:.2f}'.format(bid_depth, bid, ask_depth, ask, self._spread))

            # See if we need to place a trade
            self.on_bidask_update()

        # See if there is a trade in websocket data
        if message['type'] == 'match':
            self.trade_price = message['price']
            self.trade_size = message['size']
            self.trade_side = message['side']
            #logger.debug('Trade: {}: {:.3f} @ {:.2f}'.format(self.trade_side.title(), self.trade_size, self.trade_price))

        # See if something private came in the message (authenticated data)
        if 'user_id' in message:
            # We received a private message. Please log it.
            logger.warning("***Private Message Received from Websocket***: user_id - " + message['user_id'] + " found in message.")
            logger.debug(message)
            if 'price' in message and 'size' in message:
                message = self.auth_client.clean_message(message)

            if message['type'] == 'received':
                # Order Place was Acknowledged.
                if message['order_type'] == 'limit':
                    logger.warning("***Limit Order Place was Acknowledged***")
                    # Send the order to the orderbook
                    if message['side'] == 'buy':
                        self.auth_client.my_buy_order_acks.append(message)
                    else:
                        self.auth_client.my_sell_order_acks.append(message)
                else:
                    logger.critical("We had a message type 'received' with an order_type other than limit: " + message['order_type'])

            elif message['type'] == 'done':
                if message['reason'] == 'canceled':
                    # Order canceled ack
                    # Remove the Order from the Order Dictionary
                    if message['side'] == 'buy' and len(self.auth_client.my_buy_orders) > 0:
                        if message['order_id'] == self.auth_client.my_buy_orders[0]['id']:
                            self.auth_client.my_buy_orders.clear()
                            logger.warning(self.auth_client.my_buy_orders)
                    elif message['side'] == 'sell' and len(self.auth_client.my_sell_orders) > 0:
                        if message['order_id'] == self.auth_client.my_sell_orders[0]['id']:
                            self.auth_client.my_sell_orders.clear()
                            logger.warning(self.auth_client.my_sell_orders)
                    else:
                        logger.critical("We have a message with side other than Buy or Sell.")

            elif message['type'] == 'match':
                # We recieved a fill message
                logger.warning("***Received a Fill Message***")
                logger.warning(message)

                # Update Net Position
                if message['side'] == 'buy':
                    if message['maker_order_id'] == self.auth_client.my_buy_orders[0]['id']:
                        fill_size = message['size']
                        logger.critical("Clearing Out Dictionary (BEFORE)...")
                        logger.critical(self.auth_client.my_buy_orders)
                        remaining_size = self.auth_client.my_buy_orders[0]['size'] - fill_size
                        if remaining_size > 0.001:
                            self.pnl += fill_size * message['price']
                            self.real_position += fill_size
                            self.net_position = self.real_position / self.order_size
                            self.auth_client.my_buy_orders[0]['size'] = remaining_size
                        else:
                            self.pnl += self.auth_client.my_buy_orders[0]['size'] * message['price']
                            self.real_position += self.auth_client.my_buy_orders[0]['size']
                            self.net_position = self.real_position / self.order_size
                            self.auth_client.my_buy_orders.clear()
                            logger.critical("Clearing Out Dictionary (AFTER)...")
                            logger.critical(self.auth_client.my_buy_orders)
                elif message['side'] == 'sell':
                    if message['maker_order_id'] == self.auth_client.my_sell_orders[0]['id']:
                        fill_size = message['size']
                        logger.critical("Clearing Out Dictionary (BEFORE)...")
                        logger.critical(self.auth_client.my_sell_orders)
                        remaining_size = self.auth_client.my_sell_orders[0]['size'] - fill_size
                        if remaining_size > 0.001:
                            self.pnl -= fill_size * message['price']
                            self.real_position -= fill_size
                            self.net_position = self.real_position / self.order_size
                            self.auth_client.my_sell_orders[0]['size'] = remaining_size
                        else:
                            self.pnl -= self.auth_client.my_sell_orders[0]['size'] * message['price']
                            self.real_position -= self.auth_client.my_sell_orders[0]['size']
                            self.net_position = self.real_position / self.order_size
                            self.net_position = self.net_position - self.auth_client.my_sell_orders[0]['size']
                            self.auth_client.my_sell_orders.clear()
                            logger.critical("Clearing Out Dictionary (AFTER)...")
                            logger.critical(self.auth_client.my_sell_orders)

                else:
                    logger.critical("MASSIVE FAIL - Message Side is not either buy or sell.")

                if config.fill_notifications:
                    logger.warning("Sending Slack Notification:")
                    slack.send_message_to_slack("Filled - {} {:.3f} @ {:.2f} {}".format(message['side'].title(), float(message['size']), float(message['price']), str(datetime.now())))


    def on_bidask_update(self):
        # Since the bid/ask changed. Let's see if we need to place a trade.

        if self.valid_sma:
            self.update_theos()
            if (self.num_order_rejects < 3):
                self.check_if_action_needed()
            else:
                logger.critical("We have more than 2 rejects. Waiting a second...")

    def update_theos(self):
        # Update Theos

        #self.net_position = self.buy_levels - self.sell_levels
        std_offset = max(self.short_std, self.long_std)

        if self.net_position == 0:
            # We are flat
            self.bid_theo = self.sma - self.buy_initial_offset - std_offset
            self.ask_theo = self.sma + self.sell_initial_offset + std_offset

        elif self.net_position > 0:
            # We are long
            if self.net_position > 2:
                self.bid_theo = self.sma - (self.buy_initial_offset * abs(self.net_position + 1)) - (self.buy_additional_offset * ((self.net_position + 1) * (self.net_position + 1))) - std_offset
                self.ask_theo = self.sma - (self.buy_initial_offset * abs(self.net_position)) - (self.buy_additional_offset * ((self.net_position) * (self.net_position))) + self.buy_initial_offset * self.buy_profit_target_multiplier / sqrt(self.net_position)
                #self.ask_theo = self.sma - (self.buy_initial_offset * abs(self.net_position + 1) * 0.75) - (self.buy_additional_offset * ((self.net_position + 1 - 2) * (self.net_position + 1 - 2)))

            else:
                self.bid_theo = self.sma - self.buy_initial_offset * abs(self.net_position + 1) - (self.buy_additional_offset * ((self.net_position + 1) * (self.net_position + 1))) - std_offset
                self.ask_theo = self.sma

        else:
            # We are short
            if self.net_position < -2:
                self.ask_theo = self.sma + (self.sell_initial_offset * abs(self.net_position - 1)) + (self.sell_additional_offset * ((self.net_position - 1) * (self.net_position - 1))) + std_offset
                self.bid_theo = self.sma + (self.sell_initial_offset * abs(self.net_position)) + (self.sell_additional_offset * ((self.net_position) * (self.net_position))) - (self.sell_initial_offset * self.sell_profit_target_multiplier / sqrt(-self.net_position))
                #self.bid_theo = self.sma + (self.sell_initial_offset * abs(self.net_position - 1) * 0.75) + (self.sell_additional_offset * ((self.net_position - 1 + 2) * (self.net_position - 1 + 2)))

            else:
                self.ask_theo = self.sma + self.sell_initial_offset * abs(self.net_position - 1) + (self.sell_additional_offset * ((self.net_position - 1) * (self.net_position - 1))) + std_offset
                self.bid_theo = self.sma

    def check_if_action_needed(self):
        # Check to see if we want to place any orders

        # Check to see if we already placed an order
        if (len(self.auth_client.my_buy_orders) > 0):
            # We have an order already on the exchange

            if (len(self.auth_client.my_buy_orders) == 1):
                my_order_price = self.auth_client.my_buy_orders[0]['price']

                if (self._bid < (self.bid_theo + (self.min_tick*100))):
                    # Keep Order
                    if (self._bid > (my_order_price + (self.min_tick*1000))):
                        # Bid has moved more than 10 ticks from my order price. Please place a new order at the current bid + 1 minTick
                        # Cancel Current Order
                        logger.warning("Cancelling Order")
                        logger.warning(self.auth_client.my_buy_orders)
                        self.auth_client.cancel_order(self.auth_client.my_buy_orders[0]['id'])
                    else:
                        # Keep Order
                        logger.debug("Bid is either less than the previous order placed or within 10 ticks of it. Do not remove original order.")
                else:
                    # Remove Order? No need to.. lets just leave it out there...
                    logger.debug("No need to remove order because the bid is now more than 100 ticks from the Bid Theo.")
            else:
                logger.critical("We have more than just one order in the order book. Something is wrong...")

        else:
            # We do not currently have any active orders.
            if ((self._bid + self.min_tick) < self.bid_theo):
                # We want to place a Buy Order
                order_price = self._bid
                if self._spread > .01:
                    order_price += self.min_tick
                order_successful = self.auth_client.place_my_limit_order(side = 'buy', price = order_price, size = self.order_size)
                logger.info("Bid is lower than Bid Theo, we are placing a Buy Order at:" + str(self._bid + self.min_tick) + "\t"
                                + "Bid: " + str(self._bid) + "\tBid Theo: " + str(self.bid_theo) + "\tSpread: " + str(self._spread))

                if order_successful:
                    #if config.place_notifications:
                    #    slack.send_message_to_slack("Placing - Buy {:.3f} @ {}\tSpread: {:.2f}\t{}".format(self.order_size, self._bid, self._spread, str(datetime.now())))

                    #self.pnl -= Decimal(self._bid)*Decimal(self.order_size)
                    logger.warning("Order successfully placed.")
                    self.num_order_rejects = 0
                else:
                    # Order did not go through... Try again.
                    logger.critical("Order of Price: " + str(order_price) +" Rejected... Trying again")
                    logger.critical("Market Bid/Ask: " + str(self._bid) + " / " + str(self._ask))
                    self.num_order_rejects += 1


        if (len(self.auth_client.my_sell_orders) > 0):
            # We have a sell order already on the exchange

            if (len(self.auth_client.my_sell_orders) == 1):
                my_order_price = self.auth_client.my_sell_orders[0]['price']

                if (self._ask > (self.ask_theo - (self.min_tick * 100))):
                    # Keep Order
                    if (self._ask < (my_order_price - (self.min_tick * 1000))):
                        # Ask has moved more than 10 ticks from my order price. Please place a new order at the current ask - 1 minTick
                        # Cancel Current Order
                        logger.warning("Cancelling Order")
                        logger.warning(self.auth_client.my_sell_orders)
                        self.auth_client.cancel_order(self.auth_client.my_sell_orders[0]['id'])
                    else:
                        # Keep Order
                        logger.debug("Ask is either higher than the previous order placed or within 10 ticks of it. Do not remove original order.")
                else:
                    # Remove Order? No Need to... lets just leave it out there..
                    logger.debug("No need to remove order because the ask is now more than 100 ticks from the Ask Theo.")
            else:
                logger.critical("We have more than just one order in the order book. Somethin is wrong...")

        else:
            # We do not currently have any active orders.
            if ((self._ask - self.min_tick) > self.ask_theo):
                # We want to place a Sell Order
                order_price = self._ask
                if self._spread > .01:
                    order_price -= self.min_tick


                order_successful = self.auth_client.place_my_limit_order(side = 'sell', price = order_price, size = self.order_size)
                logger.info("Ask is Higher than Ask Theo, we are placing a Sell order at:" + str(self._ask - self.min_tick) + "\t"
                              + "Ask: " + str(self._ask) + "\tAsk Theo: " + str(self.ask_theo) + "\tSpread: " + str(self._spread))
                if order_successful:
                    # if config.place_notifications:
                    #     slack.send_message_to_slack("Placing - Sell {:.3f} @ {}\tSpread: {:.2f}\t{}".format(self.order_size, self._ask, self._spread, str(datetime.now())))
                    #
                    #     self.pnl += Decimal(self._ask)*Decimal(self.order_size)
                    logger.warning("Order successfully placed.")
                    self.num_order_rejects = 0
                else:
                    # Order did not go through... Try again.
                    logger.critical("Order Rejected... Trying again")
                    logger.critical("Market Bid/Ask: " + str(self._bid) + " / " + str(self._ask))
                    self.num_order_rejects = self.num_order_rejects + 1


    def get_pnl(self):
        return self.pnl + self.net_position * float(self.trade_price) * float(self.order_size)
