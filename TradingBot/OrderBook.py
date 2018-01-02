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

    def __init__(self, strategy_settings, product_id=None, keys=None):
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
        self.strategy_name = strategy_settings.get('strategy_name')
        self.order_size = strategy_settings.get('order_size')
        self.min_size_for_order_update = strategy_settings.get('min_size_for_order_update')
        self.min_distance_for_order_update = strategy_settings.get('min_distance_for_order_update')
        self.buy_initial_offset = strategy_settings.get('buy_initial_offset')
        self.sell_initial_offset = strategy_settings.get('sell_initial_offset')
        self.buy_additional_offset_multiplier = strategy_settings.get('buy_additional_offset_multiplier')
        self.sell_additional_offset_multiplier = strategy_settings.get('sell_additional_offset_multiplier')
        self.max_long_position = strategy_settings.get('max_long_position')
        self.max_short_position = strategy_settings.get('max_short_position')
        self.fill_notifications = strategy_settings.get('fill_notifications')
        self.buy_max_initial_profit_target = strategy_settings.get('buy_max_initial_profit_target')
        self.sell_max_initial_profit_target = strategy_settings.get('sell_max_initial_profit_target')
        self.buy_profit_target_multiplier = 1
        self.sell_profit_target_multiplier = 1
        self.bid_theo = 0
        self.ask_theo = 0
        self.num_order_rejects = 0
        self.num_rejections = 0
        self.min_tick = round(0.01, 2)
        self.min_order_size = round(0.0001, 4)
        self.myKeys = keys
        self.auth_client = MyFillOrderBook(self.myKeys['key'], self.myKeys['secret'], self.myKeys['passphrase'], strategy_settings)

        logger.info("Settings Used:")
        logger.info(strategy_settings)
        logger.info("Order Size: {}\tBuy Initial Offset: {}\tSell Initial Offset: {}\tBuy Additional Offset: {}\tSell Additional Offset: {}\tBuy Profit Target Mult: {}\tSell Profit Target Mult: {}".format(self.order_size, self.buy_initial_offset, self.sell_initial_offset, self.buy_additional_offset_multiplier, self.sell_additional_offset_multiplier, self.buy_profit_target_multiplier, self.sell_profit_target_multiplier))

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
        if self._bid == bid and self._ask == ask and bid>self.bid_theo and ask<self.ask_theo:# and self._bid_depth == bid_depth and self._ask_depth == ask_depth:
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
            logger.debug("***Private Message Received from Websocket***: user_id - " + message['user_id'] + " found in message.")
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
                    logger.debug("***Limit Order Place was Acknowledged***")
                    # Send the order to the orderbook
                    self.auth_client.add_my_order_ack(message)
                else:
                    logger.critical("We had a message type 'received' with an order_type other than limit: " + message['order_type'])

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

                logger.debug("***Limit Order " + message['order_id'] + " is now open on the order book. ")
                logger.debug("Remaining Size: " + message['remaining_size'])

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
                    logger.debug("***Cancel Order Message Acknowledged.***")
                    self.auth_client.process_cancel_message(message)

                elif message['reason'] == 'filled':
                    # Fill Message done
                    # Match message comes in first.
                    logger.debug("Message Type == 'done' with a reason of 'filled'")

                else:
                    logger.critical("Message Type == 'done' with a new message reason.")

            elif message['type'] == 'match':
                # We received a fill message
                if message['side'] == 'buy':
                    if len(self.auth_client.my_buy_orders) > 0:
                        if message['maker_order_id'] == self.auth_client.my_buy_orders[0]['id']:
                            logger.warning("***Received a Buy Fill Message***")
                            self.auth_client.process_fill_message(message)
                            if self.fill_notifications:
                                logger.debug("Sending Slack Notification:")
                                slack.send_message_to_slack("{}: {} {:.4f} @ {:.2f} {}. NP: {:.0f} PnL: {:.2f}".format(self.strategy_name, message['side'].title(), float(message['size']), float(message['price']), str(datetime.now().time()), self.auth_client.net_position, self.get_pnl()))
                elif message['side'] == 'sell':
                    if len(self.auth_client.my_sell_orders) > 0:
                        if message['maker_order_id'] == self.auth_client.my_sell_orders[0]['id']:
                            logger.warning("****Received a Sell Fill Message***")
                            self.auth_client.process_fill_message(message)
                            if self.fill_notifications:
                                logger.debug("Sending Slack Notification:")
                                slack.send_message_to_slack("{}: {} {:.4f} @ {:.2f} {}. NP: {:.0f} PnL: {:.2f}".format(self.strategy_name, message['side'].title(), float(message['size']), float(message['price']), str(datetime.now().time()), self.auth_client.net_position, self.get_pnl()))
                else:
                    logger.critical("We received a message that had something other than a buy or sell for the side...")

            elif message['type'] == 'change':
                # we received a change messages
                logger.critical("Received a Change Message... We currently aren't doing anything with these, but logging them.")
            else:
                logger.critical("Received a Message Type that we have not yet coded for. Message Type: " + message['type'])

    def on_bidask_update(self):
        # Since the bid/ask changed. Let's see if we need to place a trade.

        if self.valid_sma:
            self.update_theos()

            if (self.num_order_rejects < 1):
                self.check_if_action_needed()
            else:
                logger.debug("We have more than 1 rejects. Waiting a second...")

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
                self.bid_theo = self.sma - (self.buy_initial_offset * abs(self.auth_client.net_position + 1)) - (self.buy_additional_offset_multiplier * ((self.auth_client.net_position + 1) * (self.auth_client.net_position + 1))) - std_offset
                self.ask_theo = self.sma - (self.buy_initial_offset * abs(self.auth_client.net_position)) - (self.buy_additional_offset_multiplier * ((self.auth_client.net_position) * (self.auth_client.net_position))) + self.buy_initial_offset  * self.buy_profit_target_multiplier
                if self.ask_theo > self.auth_client.last_buy_price + self.buy_max_initial_profit_target:
                    self.ask_theo = self.auth_client.last_buy_price + self.buy_max_initial_profit_target
            else:
                self.bid_theo = self.sma - self.buy_initial_offset * abs(self.auth_client.net_position + 1) - (self.buy_additional_offset_multiplier * ((self.auth_client.net_position + 1) * (self.auth_client.net_position + 1))) - std_offset
                self.ask_theo = self.sma

        else:
            # We are short
            if self.auth_client.net_position < -2:
                self.ask_theo = self.sma + (self.sell_initial_offset * abs(self.auth_client.net_position - 1)) + (self.sell_additional_offset_multiplier * ((self.auth_client.net_position - 1) * (self.auth_client.net_position - 1))) + std_offset
                self.bid_theo = self.sma + (self.sell_initial_offset * abs(self.auth_client.net_position)) + (self.sell_additional_offset_multiplier * ((self.auth_client.net_position) * (self.auth_client.net_position))) - (self.sell_initial_offset * self.sell_profit_target_multiplier)
                if self.bid_theo < self.auth_client.last_sell_price - self.sell_max_initial_profit_target:
                    self.bid_theo = self.auth_client.last_sell_price - self.sell_max_initial_profit_target
            else:
                self.ask_theo = self.sma + self.sell_initial_offset * abs(self.auth_client.net_position - 1) + (self.sell_additional_offset_multiplier * ((self.auth_client.net_position - 1) * (self.auth_client.net_position - 1))) + std_offset
                self.bid_theo = self.sma

    def check_if_action_needed(self):
        # Check to see if we want to place any orders

        # Check to see if we already placed an order
        if (len(self.auth_client.my_buy_orders) > 0):
            # We have an order already on the exchange
            if (len(self.auth_client.my_buy_orders) == 1):
                my_order_price = self.auth_client.my_buy_orders[0]['price']

                if (self._bid < self.bid_theo):
                    if (((self._bid > my_order_price) and (self._bid_depth > self.min_size_for_order_update)) or (self._bid > my_order_price + self.min_distance_for_order_update)):
                        self.cancel_buy_order()
                    else:
                        # Keep Order
                        logger.debug("Bid is either equal to the order placed or the size or distance from order triggers were not yet reached. Do not remove original order.")
                elif abs(my_order_price - self.bid_theo) > self.buy_initial_offset*0.5:
                    logger.debug("Canceling bid since it has sufficiently diverged from the bid theo.")
                    self.cancel_buy_order()
                else:
                    # Remove Order? No need to.. lets just leave it out there...
                    logger.debug("No need to remove order because the bid is now more than 100 ticks from the Bid Theo.")
            else:
                logger.critical("We have more than just one order in the order book. Something is wrong...")

        else:
            # We do not currently have any active orders. Place buy order if the bid is below our bid theo or if we are short.
            if ((self._bid + self.min_tick) < self.bid_theo and self.auth_client.net_position < self.max_long_position):
                order_price = self._bid
                if self._spread > .01:
                    order_price += self.min_tick

                order_size = self.order_size
                if (-self.min_order_size) > self.auth_client.real_position and self.auth_client.real_position > -1.99 * self.order_size:
                    order_size = round(-self.auth_client.real_position,8)

                self.place_buy_order(order_price, order_size)

        # Check to see if we already placed an order
        if (len(self.auth_client.my_sell_orders) > 0):
            # We have a sell order already on the exchange

            if (len(self.auth_client.my_sell_orders) == 1):
                my_order_price = self.auth_client.my_sell_orders[0]['price']

                if (self._ask > self.ask_theo):
                    if (((self._ask < my_order_price) and (self._ask_depth > self.min_size_for_order_update)) or (self._ask < my_order_price - self.min_distance_for_order_update)):
                        self.cancel_sell_order()
                    else:
                        # Keep Order
                        logger.debug("Ask is either equal to the order placed or the size or distnace from order triggers were not yet reached. Do not remove original order.")
                elif abs(my_order_price - self.ask_theo) > self.sell_initial_offset*0.5:
                    logger.debug("Canceling offer since it has sufficiently diverged from the ask theo.")
                    self.cancel_sell_order()
                else:
                    # Remove Order? No Need to... lets just leave it out there..
                    logger.debug("Ask is higher than Ask Theo - 500 ticks.")
            else:
                logger.critical("We have more than just one order in the order book. Somethin is wrong...")

        else:
            # We do not currently have any active orders. Place sell order if the ask is below our ask theo or if we are long.
            if ((self._ask - self.min_tick) > self.ask_theo and self.auth_client.net_position > -self.max_short_position):
                # We want to place a Sell Order
                order_price = self._ask
                if self._spread > .01:
                    order_price -= self.min_tick

                order_size = self.order_size
                if self.min_order_size < self.auth_client.real_position  and self.auth_client.real_position < 1.99 * self.order_size:
                    order_size = round(self.auth_client.real_position,8)

                self.place_sell_order(order_price, order_size)

    def place_buy_order(self, order_price, order_size):
        order_successful = self.auth_client.place_my_limit_order(side = 'buy', price = order_price, size = order_size)
        logger.info("Bid is lower than Bid Theo, we are placing a Buy Order of: " + str(order_size) + " at:" + str(order_price) + "\t"
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
            logger.debug("Market Bid/Ask: " + str(self._bid) + " / " + str(self._ask))
            self.num_order_rejects += 1


    def place_sell_order(self, order_price, order_size):
        order_successful = self.auth_client.place_my_limit_order(side = 'sell', price = order_price, size = order_size)
        logger.info("Ask is Higher than Ask Theo, we are placing a Sell order of: " + str(order_size) + " at:" + str(self._ask - self.min_tick) + "\t"
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
            logger.debug("Market Bid/Ask: " + str(self._bid) + " / " + str(self._ask))
            self.num_order_rejects = self.num_order_rejects + 1

    def cancel_buy_order(self):
        # Cancel Current Order
        if (not self.auth_client.sent_buy_cancel):
            logger.warning("Cancelling Order")
            logger.debug(self.auth_client.my_buy_orders)
            exchange_message = None
            exchange_message = self.auth_client.cancel_order(self.auth_client.my_buy_orders[0]['id'])
            logger.debug("Exchange Message:")
            logger.debug(exchange_message)
            if 'message' in exchange_message:
                if exchange_message['message'] == "order not found":
                    logger.debug("Order is Not Found. It probably hasn't made it to the orderbook yet. Don't do anything.")
                    self.auth_client.sent_buy_cancel = True
                    logger.debug("Setting Sent Buy Cancel to True")
                elif exchange_message['message'] == 'Order already done':
                    logger.critical("Order is already canceled or filled. Verifying orders now.")
                    self.auth_client.verify_orders()
                else:
                    logger.critical("Message is different than expected.")
            else:
                logger.debug("Exchange Message is our order_ID. Cancel successful.")
                self.auth_client.sent_buy_cancel = True
                logger.debug("Setting Sent Buy Cancel to True")
        else:
            logger.debug("Already sent buy cancel.")
            self.auth_client.num_buy_cancel_rejects += 1
            if self.auth_client.num_buy_cancel_rejects > 100:
                # The exchange must not have received the cancel request. Sending New Cancel request
                logger.critical("This really should not be happening.")
                logger.critical("Retrying to Cancel Order:")
                logger.critical(self.auth_client.my_buy_orders)
                exchange_message = self.auth_client.cancel_order(self.auth_client.my_buy_orders[0]['id'])
                logger.critical("Exchange Message Inner:")
                logger.critical(exchange_message)
                if 'message' in exchange_message:
                    self.auth_client.verify_orders()
                    if exchange_message['message'] == "order not found":
                        logger.critical("Order is Not Found. It probably hasn't made it to the orderbook yet. Don't do anything.")
                    elif exchange_message['message'] == 'Order already done':
                        logger.critical("Order is already canceled or filled.")
                    else:
                        logger.critical("Message is different than expected.")
                else:
                    logger.critical("Exchange Message is our order_ID. Cancel successful.")
                    self.auth_client.sent_buy_cancel = True
                    logger.critical("Setting Sent Buy Cancel to True")
                logger.critical("Sent Buy Cancel should already be set to True...")
                logger.critical("Resetting cancel rejects.")
                self.auth_client.num_buy_cancel_rejects = 0

    def cancel_sell_order(self):
        # Cancel Current Order
        if (not self.auth_client.sent_sell_cancel):
            logger.warning("Canceling Order")
            logger.debug(self.auth_client.my_sell_orders)
            exchange_message = None
            exchange_message = self.auth_client.cancel_order(self.auth_client.my_sell_orders[0]['id'])
            logger.debug("Exchange Message:")
            logger.debug(exchange_message)
            if 'message' in exchange_message:
                if exchange_message['message'] == "order not found":
                    logger.debug("Order is Not Found. It probably hasn't made it to the orderbook yet. Don't do anything.")
                    self.auth_client.sent_sell_cancel = True
                    logger.debug("Setting Sent Sell Cancel to True.")
                elif exchange_message['message'] == 'Order already done':
                    logger.critical("Order is already canceled or filled. Verifying orders now.")
                    self.auth_client.verify_orders()
                else:
                    logger.critical("Message is different than expected.")
            else:
                logger.debug("Exchange message is our order_id. Cancel sent successfully.")
                self.auth_client.sent_sell_cancel = True
                logger.debug("Setting Sent Sell Cancel to True.")
        else:
            logger.debug("Already sent sell cancel.")
            self.auth_client.num_sell_cancel_rejects += 1
            if self.auth_client.num_sell_cancel_rejects > 100:
                # The exchange must not have received the cancel request. Sending New Cancel request
                # HTTP/1.1 400 32 <-- Error code
                logger.critical("This really should not be happening.")
                logger.critical("Retrying to Cancel Order:")
                logger.critical(self.auth_client.my_sell_orders)
                exchange_message = self.auth_client.cancel_order(self.auth_client.my_sell_orders[0]['id'])
                logger.critical("Exchange Message Inner:")
                logger.critical(exchange_message)
                if 'message' in exchange_message:
                    self.auth_client.verify_orders()
                    if exchange_message['message'] == "order not found":
                        logger.critical("Order is Not Found. It probably hasn't made it to the orderbook yet. Don't do anything.")
                    elif exchange_message['message'] == 'Order already done':
                        logger.critical("Order is already canceled or filled.")
                    else:
                        logger.critical("Message is different than expected.")
                else:
                    logger.critical("Exchange Message is our order_ID. Cancel sent successfully.")
                    self.auth_client.sent_sell_cancel = True
                    logger.critical("Setting Sent Sell Cancel to True")
                logger.critical("Sent Sell Cancel should already be set to True...")
                logger.critical("Resetting cancel rejects.")
                self.auth_client.num_sell_cancel_rejects = 0

    def get_pnl(self):
        return self.auth_client.pnl + self.auth_client.real_position * float(self.trade_price)
