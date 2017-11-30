import gdax
import time
import config
import sys

# Settings
logging = True



class MyWebsocketClient(gdax.WebsocketClient):
    def on_open(self):
        self.url = "wss://ws-feed.gdax.com/"
        #self.products = ["BTC-USD"]
        self.message_count = 0
        print("Let's count the messages!")

    def on_message(self, msg):
        
        # Show my orders
        if 'user_id' in msg:
            if msg['user_id'] == my_user_id:
                for key, value in msg.items():
                    print(key + ": " + str(value))
                print("\n")
        
        # Show trades
        if msg['type'] == 'match':
            for key, value in msg.items():
                print(key + ": " + str(value))
            print("\n")
        
        # Show all updates
        #if 'price' in msg and 'type' in msg:
            #print("Message type:", msg["type"], "\t@ %.3f" % float(msg["price"]))
        self.message_count += 1

    def on_close(self):
        print("-- Goodbye! --")


# # Write output to log file
if logging:
    print("Begin Writing Log File:")
    orig_stdout = sys.stdout
    f = open('GDAXoutput.txt', 'w')
    sys.stdout = f


my_user_id = config.my_user_id
myKeys = config.live
print("My keys are: ")
for key, value in myKeys.items():
    print(key + ": " + value)
print("My user_id is: " + my_user_id)
    
# Start Client
wsClient = MyWebsocketClient(products='BTC-USD', 
                             auth = True,
                             api_key=myKeys['key'],
                             api_secret=myKeys['secret'],
                             api_passphrase=myKeys['passphrase'],
                             )
wsClient.start()
print(wsClient.url, wsClient.products, wsClient.api_key, wsClient.api_passphrase, str(wsClient.auth))

# Do some logic with the data
while wsClient.message_count < 1000:
    print("\nMessageCount =", "%i \n" % wsClient.message_count)
    time.sleep(1)

wsClient.close()

if logging:
    sys.stdout = orig_stdout
    f.close()