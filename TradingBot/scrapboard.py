#===============================================================================
# from decimal import Decimal
# 
# 
# ask = Decimal(0.0100000001)
# spread = 0.03
# spread = Decimal(spread)
# price = (spread-ask)
# my_price_string = '{:.2f}'.format(price)
# 
# my_price_string = str(my_price_string)
# my_price_string = str(my_price_string)
# 
# type(ask)
# type(spread)
# type(my_price_string)
# type(price)
# 
# spread = Decimal(spread)
# type(spread)
# 
# 
# print('Ask: {:.2f}\tSpread: {:.2f}'.format(ask, spread)) 
# 
# my_price_string = '{:.2f}'.format(ask + spread)
# 
# 
# if ask == spread:
#     print("yes")
# else:
#     print("no")
# 
# fail = ask + Decimal(spread)
# 
# spread = Decimal(spread)
# type(spread)
# 
# 
# print(fail)
#===============================================================================

# import slack
# 
# message = {'side':'buy',
#            'size':'0.05',
#            'price':'32533',
#            'product_id':'btc/usd'}
# 
# slack.construct_message(message = message)


#import slack

#from datetime import datetime
#from decimal import Decimal

#message = {'side':'buy',
#           'size':'0.050000',
#           'price':'32533',
#           'product_id':'btc/usd'}

#currTime = str(datetime.now().time())

#print(currTime)
#net_position = 4.00000000002
#slack.send_message_to_slack("Filled - {} {:.2f} @ {}\t{} NP: {:.0f}".format(message['side'].title(), Decimal(message['size']), message['price'], currTime, net_position))
                            
                            
                            
import time
import datetime as dt
import config
import sys
import logging
import numpy as np
import types

import gdax

from gdax import OrderBook
from decimal import Decimal


# Print out my Keys
my_user_id = config.my_user_id
myKeys = config.live

auth_client = gdax.AuthenticatedClient(myKeys['key'], myKeys['secret'], myKeys['passphrase'] )
my_accounts = auth_client.get_accounts()
print(my_accounts)

my_position = auth_client.get_position()
print(my_position)

my_order = auth_client.get_order('8191d8c9-99cc-4a4b-892e-c8191d1976e7')
print(len(my_order))
print(my_order)

my_order = auth_client.get_order(' 8191d8c9-99cc-4a4b-892e-c8191d1976e7')
print(len(my_order))
print(my_order)

my_orders = auth_client.get_orders(product_id='BTC-USD', status = "open")
if isinstance(my_orders, types.GeneratorType):
    for order in my_orders:
        print(order)
print(my_orders)

