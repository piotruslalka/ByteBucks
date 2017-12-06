
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

my_ask = 13453+3.34

my_order = auth_client.place_my_limit_order('sell', my_ask, '0.01')
#my_order = auth_client.place_my_limit_order('buy', my_bid, '0.01')

print(my_order)