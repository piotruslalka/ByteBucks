

my_buy_orders = []

order1 = {'user_id': '59a', 'type': 'open', 'order_id': '323ac'}
order2 = {'user_id': '59a', 'type': 'open', 'order_id': '323fg'}
order3 = {'user_id': '59a', 'type': 'open', 'order_id': '323yz'}

orderdic1 = {order1['order_id']: order1}
orderdic2 = {order2['order_id']: order2}
orderdic3 = {order3['order_id']: order3}

my_buy_orders.append(orderdic1)
my_buy_orders.append(orderdic2)
my_buy_orders.append(orderdic3)

print(my_buy_orders)

fill2 = {'user_id': '59a', 'order_id': '323fg'}

for order in my_buy_orders:
    if fill2['order_id'] in order.keys():
        my_buy_orders.remove(order)

print(my_buy_orders)