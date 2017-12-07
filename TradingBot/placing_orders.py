
from decimal import Decimal
from gdax.authenticated_client import AuthenticatedClient
from MyFillOrderBook import MyFillOrderBook

import config

# Log my Keys
my_user_id = config.my_user_id
myKeys = config.live


auth_client = MyFillOrderBook(myKeys['key'], myKeys['secret'], myKeys['passphrase'])

#offset = 1
#close_price = '13423'

#my_ask = Decimal(close_price) + offset
#my_bid = Decimal(close_price) - offset




    
my_bid = 16040.11

my_order = auth_client.place_my_limit_order('buy', my_bid, '0.01')

order_details = auth_client.my_sell_orders[0]

print(order_details)