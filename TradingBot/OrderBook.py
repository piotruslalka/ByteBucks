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
        self.buy_profit_target_multiplier = 2
        self.sell_profit_target_multiplier = 2
        self.bid_theo = 0
        self.ask_theo = 0
        self.num_order_rejects = 0
        self.num_rejections = 0
        self.min_tick = round(0.01, 2)
        self.min_order_size = round(0.01, 2)
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
            logger.debug('Trade: {}: {:.3f} @ {:.2f}'.format(self.trade_side.title(), float(self.trade_size), float(self.trade_price)))

        # See if something private came in the message (authenticated data)
        if 'user_id' in message:
            # We received a private message. Please log it.
            logger.warning("***Private Message Received from Websocket***: user_id - " + message['user_id'] + " found in message.")
            logger.debug(message)
            logger.debug("Cleaning Message...")
            message = self.auth_client.clean_message(message)
            logger.debug(message)

            if message['type'] == 'received':
                # A valid order has been received and is now active. This message is emitted for every single valid order as soon as the matching engine receives it whether it fills immediately or not.
                # The received message does not indicate a resting order on the order book. It simply indicates a new incoming order which as been accepted by the matching engine for processing.
                # Received orders may cause match message to follow if they are able to begin being filled (taker behavior).
                # Self-trade prevention may also trigger change messages to follow if the order size needs to be adjusted.
                # Orders which are not fully filled or canceled due to self-trade prevention result in an open message and become resting orders on the order book.
                # Market orders (indicated by the order_type field) may have an optional funds field which indicates how much quote currency will be used to buy or sell.
                # For example, a funds field of 100.00 for the BTC-USD product would indicate a purchase of up to 100.00 USD worth of bitcoin.

                # {
                #     "type": "received",
                #     "time": "2014-11-07T08:19:27.028459Z",
                #     "product_id": "BTC-USD",
                #     "sequence": 10,
                #     "order_id": "d50ec984-77a8-460a-b958-66f114b0de9b",
                #     "size": "1.34",
                #     "price": "502.1",
                #     "side": "buy",
                #     "order_type": "limit"
                # }

                if message['order_type'] == 'limit':
                    logger.warning("***Limit Order Place was Acknowledged***")
                    # Send the order to the orderbook
                    self.auth_client.add_my_order_ack(message)
                else:
                    logger.critical("We had a message type 'received' with an order_type other than limit: " + message['order_type'])
                    logger.critical(message)

            elif message['type'] == 'open':
                # The order is now open on the order book. This message will only be sent for orders which are not fully filled immediately.
                # remaining_size will indicate how much of the order is unfilled and going on the book.

                # {
                #     "type": "open",
                #     "time": "2014-11-07T08:19:27.028459Z",
                #     "product_id": "BTC-USD",
                #     "sequence": 10,
                #     "order_id": "d50ec984-77a8-460a-b958-66f114b0de9b",
                #     "price": "200.2",
                #     "remaining_size": "1.00",
                #     "side": "sell"
                # }

                logger.warning("***Limit Order " + message['order_id'] + " is now open on the order book. ")
                logger.warning("Remaining Size: " + message['remaining_size'])

            elif message['type'] == 'done':
                # The order is no longer on the order book.
                # Sent for all orders for which there was a received message.
                # This message can result from an order being canceled or filled.
                # There will be no more messages for this order_id after a done message.
                # remaining_size indicates how much of the order went unfilled; this will be 0 for filled orders.
                # market orders will not have a remaining_size or price field as they are never on the open order book at a given price.

                # {
                #     "type": "done",
                #     "time": "2014-11-07T08:19:27.028459Z",
                #     "product_id": "BTC-USD",
                #     "sequence": 10,
                #     "price": "200.2",
                #     "order_id": "d50ec984-77a8-460a-b958-66f114b0de9b",
                #     "reason": "filled", // or "canceled"
                #     "side": "sell",
                #     "remaining_size": "0"
                # }

                if message['reason'] == 'canceled':
                    # Order canceled  received
                    logger.critical("Cancel Message Received.")
                    self.auth_client.process_cancel_message(message)

                elif message['reason'] == 'filled':
                    # Fill Message done
                    # Match message comes in first so we will ignore this until we do detailed order and fill reconciliation.
                    logger.debug("Message Type == 'done' with a reason of 'filled'")
                    logger.debug(message)
                else:
                    logger.critical("Message Type == 'done' with a new message reason.")

            elif message['type'] == 'match':
                # We recieved a fill message
                logger.warning("***Received a Fill Message***")
                logger.warning(message)

                self.auth_client.process_fill_message(message)

                if config.fill_notifications:
                    logger.warning("Sending Slack Notification:")
                    slack.send_message_to_slack("Filled - {} {:.3f} @ {:.2f} {}".format(message['side'].title(), float(message['size']), float(message['price']), str(datetime.now())))

            elif message['type'] == 'change':
                # we received a change messages
                logger.critical("Received a Change Message... We currently aren't doing anything with these, but logging them.")
                logger.critical(message)
            else:
                logger.critical("Received a Message Type that we have not yet coded for. Mesage Type: " + message['type'])
                logger.critical(message)

    def on_bidask_update(self):
        # Since the bid/ask changed. Let's see if we need to place a trade.

        if self.valid_sma:
            self.update_theos()
            # logger.debug("My Buy Orders:")
            # logger.debug(self.auth_client.my_buy_orders)
            # logger.debug("My Sell Orders:")
            # logger.debug(self.auth_client.my_sell_orders)
            if (self.num_order_rejects < 2):
                self.check_if_action_needed()
            else:
                logger.debug("We have more than 2 rejects. Waiting a second...")

    def update_theos(self):
        # Update Theos
        std_offset = max(self.short_std, self.long_std)

        if self.auth_client.net_position == 0:
            # We are flat
            self.bid_theo = self.sma - self.buy_initial_offset - std_offset
            self.ask_theo = self.sma + self.sell_initial_offset + std_offset

        elif self.auth_client.net_position > 0:
            # We are long
            if self.auth_client.net_position > 2:
                self.bid_theo = self.sma - (self.buy_initial_offset * abs(self.auth_client.net_position + 1)) - (self.buy_additional_offset * ((self.auth_client.net_position + 1) * (self.auth_client.net_position + 1))) - std_offset
                self.ask_theo = self.sma - (self.buy_initial_offset * abs(self.auth_client.net_position)) - (self.buy_additional_offset * ((self.auth_client.net_position) * (self.auth_client.net_position))) - self.buy_initial_offset * self.buy_profit_target_multiplier / sqrt(self.auth_client.net_position)
            else:
                self.bid_theo = self.sma - self.buy_initial_offset * abs(self.auth_client.net_position + 1) - (self.buy_additional_offset * ((self.auth_client.net_position + 1) * (self.auth_client.net_position + 1))) - std_offset
                self.ask_theo = self.sma

        else:
            # We are short
            if self.auth_client.net_position < -2:
                self.ask_theo = self.sma + (self.sell_initial_offset * abs(self.auth_client.net_position - 1)) + (self.sell_additional_offset * ((self.auth_client.net_position - 1) * (self.auth_client.net_position - 1))) + std_offset
                self.bid_theo = self.sma + (self.sell_initial_offset * abs(self.auth_client.net_position)) + (self.sell_additional_offset * ((self.auth_client.net_position) * (self.auth_client.net_position))) + (self.sell_initial_offset * self.sell_profit_target_multiplier / sqrt(-self.auth_client.net_position))
            else:
                self.ask_theo = self.sma + self.sell_initial_offset * abs(self.auth_client.net_position - 1) + (self.sell_additional_offset * ((self.auth_client.net_position - 1) * (self.auth_client.net_position - 1))) + std_offset
                self.bid_theo = self.sma

    def check_if_action_needed(self):
        # Check to see if we want to place any orders

        # Check to see if we already placed an order
        if (len(self.auth_client.my_buy_orders) > 0):
            # We have an order already on the exchange

            if (len(self.auth_client.my_buy_orders) == 1):
                my_order_price = self.auth_client.my_buy_orders[0]['price']

                if (self._bid < (self.bid_theo + (self.min_tick*10))):
                    # Keep Order
                    logger.debug("Bid: " + str(self._bid) + " should be less than " + str(self.bid_theo + (self.min_tick*10)))
                    if (self._bid > (my_order_price + (self.min_tick*10))):
                        # Bid has moved more than 10 ticks from my order price. Please place a new order at the current bid + 1 minTick
                        logger.debug("Bid: " + str(self._bid) + " should be greater than " + str(my_order_price + (self.min_tick*10)))
                        # Cancel Current Order
                        if (not self.auth_client.sent_buy_cancel):
                            logger.warning("Cancelling Order")
                            logger.warning(self.auth_client.my_buy_orders)
                            self.auth_client.cancel_order(self.auth_client.my_buy_orders[0]['id'])
                            self.auth_client.sent_buy_cancel = True
                            logger.critical("Setting Sent Buy Cancel to True")
                        else:
                            logger.debug("Already sent buy cancel.")
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

                place_size = self.order_size
                if self.auth_client.real_position < 2 * self.order_size and self.auth_client.real_position > self.min_order_size:
                    place_size = self.auth_client.real_position

                order_successful = self.auth_client.place_my_limit_order(side = 'buy', price = order_price, size = place_size)
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

                if (self._ask > (self.ask_theo - (self.min_tick * 10))):
                    # Keep Order
                    logger.debug("Ask: " + str(self._ask) + " should be greater than " + str(self.ask_theo - (self.min_tick*10)))
                    if (self._ask < (my_order_price - (self.min_tick * 10))):
                        # Ask has moved more than 10 ticks from my order price. Please place a new order at the current ask - 1 minTick
                        logger.debug("Ask: " + str(self._ask) + " should be less than " + str(my_order_price - (self.min_tick*10)))
                        # Cancel Current Order
                        if (not self.auth_client.sent_sell_cancel):
                            logger.warning("Cancelling Order")
                            logger.warning(self.auth_client.my_sell_orders)
                            self.auth_client.cancel_order(self.auth_client.my_sell_orders[0]['id'])
                            self.auth_client.sent_sell_cancel = True
                            logger.critical("Setting Sent Sell Cancel to True")
                        else:
                            logger.debug("Already sent sell cancel.")
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

                place_size = self.order_size
                if self.auth_client.real_position < 2 * self.order_size and self.auth_client.real_position > self.min_order_size:
                    place_size = self.auth_client.real_position

                order_successful = self.auth_client.place_my_limit_order(side = 'sell', price = order_price, size = place_size)
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
        return self.auth_client.pnl + self.auth_client.real_position * float(self.trade_price)
