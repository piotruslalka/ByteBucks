# Here we test how to place orders

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

count = 0
while count < 1000000000000:
	print(count)
	auth_client = gdax.AuthenticatedClient(myKeys['key'], myKeys['secret'], myKeys['passphrase'] )
	my_accounts = auth_client.get_accounts()
	print(my_accounts)
	
	my_position = auth_client.get_position()
	print(my_position)
	
	my_orders = auth_client.get_orders(product_id='BTC-USD', status = "open")
	if isinstance(my_orders, types.GeneratorType):
		for order in my_orders:
			print(order)
	print(my_orders)
	time.sleep(3*60)
	count += 1
