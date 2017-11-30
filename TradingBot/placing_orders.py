# Here we test how to place orders

import time
import datetime as dt
import config
import sys
import logging
import pandas as pd
import numpy as np

import gdax

from gdax import OrderBook
from decimal import Decimal




# Print out my Keys
my_user_id = config.my_user_id
myKeys = config.live
print("My keys are: ")
for key, value in myKeys.items():
    print(key + ": " + value)
print("My user_id is: " + my_user_id)


auth_client = gdax.AuthenticatedClient(myKeys['key'], myKeys['secret'], myKeys['passphrase'])
my_accounts = auth_client.get_accounts()
print(my_accounts)

# Place Buy Limit Order
#my_buy = auth_client.place_limit_order(product_id='BTC-USD', side='buy', price='4335.05', size='0.01', time_in_force='GTC', post_only=True)
#print(my_buy)

# Cancel Buy Order
my_cancel = auth_client.cancel_order(order_id='36f34997-9069-4f68-b91c-02a56e558a55')
