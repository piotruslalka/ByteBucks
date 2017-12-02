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


import slack

from datetime import datetime
from decimal import Decimal

message = {'side':'buy',
           'size':'0.050000',
           'price':'32533',
           'product_id':'btc/usd'}

currTime = str(datetime.now())

slack.send_message_to_slack("Filled - {} {:.2f} @ {}\t{}".format(message['side'].title(), Decimal(message['size']), message['price'], currTime))
                            
                            #:.3f
