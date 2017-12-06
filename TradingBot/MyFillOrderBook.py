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
        self.my_PnL = None
        
    def place_my_limit_order(self, side, price, size='0.01'):
        """ I place the limit order here """
        if(config.debug):
            return (True)
        
        str_price = str(price)
        
        logger.warning("We are placing a Buy Order at:" + str_price)

        my_order = self.place_limit_order(product_id='BTC-USD', side=side, price=str_price, size=str(size), time_in_force='GTC', post_only=True)
        logger.warning(my_order)
        
        # Check if limit order Rejected
        if 'status' in my_order:
            if my_order['status'] == 'rejected':
                logging.critical("ORDER REJECTED!")
                return (False)
            else:
                logging.info("Saving Order...")
                if (side == "buy"):
                    self.my_buy_orders.append(my_order)
                else:
                    self.my_sell_orders.append(my_order)    
                return (True)
            
        else:
            logger.error("status is not in my_order")
            logger.error(my_order)
            return (False)
        
        
        
    def add_my_order(self, order):
        """ Add Order to book """
        logging.warning("Adding Order to book")
        logging.warning(order)
        if order['side'] == 'buy':
            myOrder = {order['order_id']: order}
            self.my_buy_orders.append(myOrder)
        if order['side'] == 'sell':
            myOrder = {order['order_id']: order}
            self.my_sell_orders.append(myOrder)
            
        logging.info("Number of Open Buy Orders: " + str(len(self.my_buy_orders)))
        logging.info("Number of Open Sell Orders: " + str(len(self.my_sell_orders)))
        print("Number of Open Buy Orders: " + str(len(self.my_buy_orders)))
        print("Number of Open Sell Orders: " + str(len(self.my_sell_orders)))
                
    def remove_my_order(self, order):
        """ Remove Order from book """
        
    def add_my_fill(self, fill):
        """ Add Fill to book """
        logging.warning("Adding Fill to book")
        logging.warning(fill)
        
        if fill['side'] == 'buy':
            # Add to Fills list
            self.my_buy_fills.append(fill)
            # Remove from Orders list
            for order in self.my_buy_orders:
                if fill['maker_order_id'] in order.keys():
                    self.my_buy_orders.remove(order)
                    logging.warning("Removing " + str(fill['maker_order_id']) + " from Buy Order Book.")
                    logging.warning(self.my_buy_orders)

        if fill['side'] == 'sell':
            # Add to Fills list
            self.my_sell_fills.append(fill)
            # Remove from Orders list
            for order in self.my_sell_orders:
                if fill['maker_order_id'] in order.keys():
                    self.my_sell_orders.remove(order)
                    logging.warning("Removing " + str(fill['maker_order_id']) + " from Sell Order Book.")
                    logging.warning(self.my_sell_orders)

            
        logging.info("Number of Open Buy Fills: " + str(len(self.my_buy_fills)))
        logging.info("Number of Open Sell Fills: " + str(len(self.my_sell_fills)))
        print("Number of Open Buy Fills: " + str(len(self.my_buy_fills)))
        print("Number of Open Sell Fills: " + str(len(self.my_sell_fills)))
        
        # Now that we have a fill. Lets place a profit order
