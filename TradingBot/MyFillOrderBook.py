import logging
import config

from gdax.authenticated_client import AuthenticatedClient
from decimal import Decimal

# Logging Settings
logger = logging.getLogger('botLog')


class MyFillOrderBook(AuthenticatedClient):
    """ This is where I store all my order and fill information """

    def __init__(self, key, b64secret, passphrase):
        super(MyFillOrderBook, self).__init__(key=key, b64secret=b64secret, passphrase=passphrase)

        logger.info("Entered into the MyFillOrderBook Class!")

        self.my_buy_fills = []
        self.my_sell_fills = []
        self.my_buy_orders = []
        self.my_sell_orders = []
        self.my_buy_order_acks = []
        self.my_sell_order_acks = []
        self.my_PnL = None

    def place_my_limit_order(self, side, price, size='0.01'):
        """ I place the limit order here """
        if(config.debug):
            return (True)

        str_price = str(round(float(price), 2))
        str_size = str(round(float(size), 8))

        logger.warning("We are placing an Order at:" + str_price)

        my_order = self.place_limit_order(product_id='BTC-USD', side=side, price=str_price, size=str_size, time_in_force='GTC', post_only=True)
        logger.warning(my_order)

        # Check if limit order Rejected
        if 'status' in my_order:
            if my_order['status'] == 'rejected':
                logging.critical("ORDER REJECTED!")
                return (False)
            else:
                logging.info("Saving Order...")
                if (side == "buy"):
                    self.my_buy_orders.append(self.clean_message(my_order))
                    logging.critical(self.my_buy_orders)
                else:
                    self.my_sell_orders.append(self.clean_message(my_order))
                    logging.critical(self.my_sell_orders)
                return (True)

        else:
            logger.error("status is not in my_order")
            logger.error(my_order)
            return (False)

    def clean_message(self, message):
        if 'price' in message:
            message['price'] = float(message['price'])
        if 'size' in message:
            message['size'] = float(message['size'])
        return message

    # def add_my_order(self, order):
    #     """ Add Order to book """
    #     logging.warning("Adding Order to book")
    #     logging.warning(order)
    #     if order['side'] == 'buy':
    #         myOrder = {order['order_id']: order}
    #         self.my_buy_orders.append(myOrder)
    #     if order['side'] == 'sell':
    #         myOrder = {order['order_id']: order}
    #         self.my_sell_orders.append(myOrder)
    #
    #     logging.info("Number of Open Buy Orders: " + str(len(self.my_buy_orders)))
    #     logging.info("Number of Open Sell Orders: " + str(len(self.my_sell_orders)))
    #     print("Number of Open Buy Orders: " + str(len(self.my_buy_orders)))
    #     print("Number of Open Sell Orders: " + str(len(self.my_sell_orders)))

    def add_my_order_ack(self, message):
        """ Add Order Ack to Order Ack Book """

        if message['side'] == 'buy':
            self.auth_client.my_buy_order_acks.append(clean_message(message))
        elif message['side'] == 'sell':
            self.auth_client.my_sell_order_acks.append(clean_message(message))
        else:
            logger.critical("Message has a side other than buy or sell in add_my_order_ack.")

    def process_cancel_message(self, message):
        """ Process the cancel message and remove orders from book if necessary. """

        if message['side'] == 'buy' and len(self.auth_client.my_buy_orders) > 0:
            if message['order_id'] == self.auth_client.my_buy_orders[0]['id']:
                self.auth_client.my_buy_orders.clear()
                self.sent_buy_cancel = False
                logger.critical("Setting Sent Buy Cancel to False")
                logger.warning(self.auth_client.my_buy_orders)
            else:
                logger.critical("Message order_id: " + message['order_id'] + " does not match the id we have in my_buy_orders: " + self.auth_client.my_buy_orders[0]['id'])
        elif message['side'] == 'sell' and len(self.auth_client.my_sell_orders) > 0:
            if message['order_id'] == self.auth_client.my_sell_orders[0]['id']:
                self.auth_client.my_sell_orders.clear()
                self.sent_sell_cancel = False
                logger.critical("Setting Sent Sell Cancel to False")
                logger.warning(self.auth_client.my_sell_orders)
            else:
                logger.critical("Message order_id: " + message['order_id'] + " does not match the id we have in my_sell_orders: " + self.auth_client.my_sell_orders[0]['id'])
        else:
            logger.critical("We have a message with side other than Buy or Sell.")

    def process_fill_message(self, message):
        """ Process the fill message and update positions and theos as necessary. """

        if message['side'] == 'buy' and len(self.auth_client.my_buy_orders) > 0:
            if message['maker_order_id'] == self.auth_client.my_buy_orders[0]['id']:
                fill_size = message['size']
                logger.critical("Clearing Out Dictionary (BEFORE)...")
                logger.critical(self.auth_client.my_buy_orders)
                remaining_size = self.auth_client.my_buy_orders[0]['size'] - fill_size
                if remaining_size > 0.001:
                    self.pnl -= fill_size * message['price']
                    self.buy_levels += fill_size
                    self.real_position += fill_size
                    self.net_position = round(self.real_position / self.order_size)
                    self.auth_client.my_buy_orders[0]['size'] = remaining_size
                else:
                    self.pnl -= self.auth_client.my_buy_orders[0]['size'] * message['price']
                    self.buy_levels += self.auth_client.my_buy_orders[0]['size']
                    self.real_position += self.auth_client.my_buy_orders[0]['size']
                    self.net_position = round(self.real_position / self.order_size)
                    self.auth_client.my_buy_orders.clear()
                    logger.critical("Clearing Out Dictionary (AFTER)...")
                    logger.critical(self.auth_client.my_buy_orders)
        elif message['side'] == 'sell' and len(self.auth_client.my_sell_orders) > 0:
            if message['maker_order_id'] == self.auth_client.my_sell_orders[0]['id']:
                fill_size = message['size']
                logger.critical("Clearing Out Dictionary (BEFORE)...")
                logger.critical(self.auth_client.my_sell_orders)
                remaining_size = self.auth_client.my_sell_orders[0]['size'] - fill_size
                if remaining_size > 0.001:
                    self.pnl += fill_size * message['price']
                    self.sell_levels += fill_size
                    self.real_position -= fill_size
                    self.net_position = round(self.real_position / self.order_size)
                    self.auth_client.my_sell_orders[0]['size'] = remaining_size
                else:
                    self.pnl += self.auth_client.my_sell_orders[0]['size'] * message['price']
                    self.sell_levels += self.auth_client.my_sell_orders[0]['size']
                    self.real_position -= self.auth_client.my_sell_orders[0]['size']
                    self.net_position = round(self.real_position / self.order_size)
                    self.auth_client.my_sell_orders.clear()
                    logger.critical("Clearing Out Dictionary (AFTER)...")
                    logger.critical(self.auth_client.my_sell_orders)
        else:
            logger.critical("Message Side is not either buy or sell.")


    # def add_my_fill(self, fill):
    #     """ Add Fill to book """
    #     logging.warning("Adding Fill to book")
    #     logging.warning(fill)
    #
    #     if fill['side'] == 'buy':
    #         # Add to Fills list
    #         self.my_buy_fills.append(fill)
    #         # Remove from Orders list
    #         for order in self.my_buy_orders:
    #             if fill['maker_order_id'] in order.keys():
    #                 self.my_buy_orders.remove(order)
    #                 logging.warning("Removing " + str(fill['maker_order_id']) + " from Buy Order Book.")
    #                 logging.warning(self.my_buy_orders)
    #
    #     if fill['side'] == 'sell':
    #         # Add to Fills list
    #         self.my_sell_fills.append(fill)
    #         # Remove from Orders list
    #         for order in self.my_sell_orders:
    #             if fill['maker_order_id'] in order.keys():
    #                 self.my_sell_orders.remove(order)
    #                 logging.warning("Removing " + str(fill['maker_order_id']) + " from Sell Order Book.")
    #                 logging.warning(self.my_sell_orders)
    #
    #
    #     logging.info("Number of Open Buy Fills: " + str(len(self.my_buy_fills)))
    #     logging.info("Number of Open Sell Fills: " + str(len(self.my_sell_fills)))
    #     print("Number of Open Buy Fills: " + str(len(self.my_buy_fills)))
    #     print("Number of Open Sell Fills: " + str(len(self.my_sell_fills)))
    #
    #     # Now that we have a fill. Lets place a profit order
