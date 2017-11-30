import gdax
import time

class MyWebsocketClientSandbox(gdax.WebsocketClient):
    """
    This class is inherited from WebsockClient.
    It uses the Sandbox. NOT LIVE DATA
    """
    def on_open(self):
        self.url = "wss://ws-feed-public.sandbox.gdax.com/"
        self.products = ["BTC-USD"]
        self.message_count = 0
        print("Let's count the messages! (Sandbox)")

    def on_message(self, msg):
        if 'price' in msg and 'type' in msg:
            print("Message type:", msg["type"], "\t@ %.3f" % float(msg["price"]))
        self.message_count += 1

    #If I comment this out then we should see Socket Closed on disconnect
    def on_close(self):
        print("-- Goodbye! --")

class MyWebsocketClient(gdax.WebsocketClient):
    """
    This class is inherited from WebsockClient.
    USES LIVE DATA
    """
    def on_open(self):
        self.url = "wss://ws-feed.gdax.com/"
        self.products = ["LTC-USD"]
        self.message_count = 0
        print("Let's count the messages!(LIVE DATA)")

    def on_message(self, msg):
        if 'price' in msg and 'type' in msg:
            print("Message type:", msg["type"], "\t@ %.3f" % float(msg["price"]))
        self.message_count += 1

    def on_close(self):
        print("-- Goodbye! --")

wsClient = MyWebsocketClient()
wsClient.start()
print(wsClient.url, wsClient.products)

# Do some logic with the data
while wsClient.message_count < 20:
    print("\nMessageCount =", "%i \n" % wsClient.message_count)
    time.sleep(1)
wsClient.close()

