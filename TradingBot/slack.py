

def construct_message(message=None, stale=False):
    from decimal import Decimal
    from datetime import datetime
    
    if (stale == False):
        side = message['side']
        size = message['size']
        product_id = message['product_id']
        price = message['price']
    else:
        side = "Fail"
        size = 0.01
        product_id = "BTC/USD"
        price = "9999"
    
    time_now = str(datetime.now())
    
    message = side.title() + " " + "{0:.2f}".format(Decimal(size)) + " " + product_id + " @ " + "{0:.2f}".format(Decimal(price))
    tweet = "Got a fill!\n" + message + "\nSent at: " + time_now
    print("\n" + tweet)
    
    send_message_to_slack(tweet)

def send_message_to_slack(text):     
    from urllib import request
    import json
    import config
    
    post = {"text": "{0}".format(text)}
   
    try:
        json_data = json.dumps(post)
        req = request.Request(config.slack,
                              data=json_data.encode('ascii'),
                              headers={'Content-Type': 'application/json'}) 
        resp = request.urlopen(req)
    except Exception as em:
        print("EXCEPTION: " + str(em))         



















# 
# 
# 
# # This should send me a slack message
# import json
# 
# from datetime import datetime
# from decimal import Decimal
# from urllib import request
# 
# class SlackNotification(object):
#     """
#     Send Notification via Slack Direct Message
# 
#     Details:
# 
#     Attributes:
#         
#     """
# 
#     def __init__(self, message=None, stale=False):
#         if (stale == False):
#             self.side = message['side']
#             self.size = message['size']
#             self.product_id = message['product_id']
#             self.price = message['price']
#         else:
#             self.side = "Fail"
#             self.size = 0.01
#             self.product_id = "BTC/USD"
#             self.price = "9999"
#         self.time_now = str(datetime.now())
#         
#         #self.construct_messagez()
# #         self.send_message_to_slack(text="Peter")
# #         self.send_message_to_slack(self.tweet)
#     @property
#     def construct_messagez(self):
#         #self.message = self.side.title() + " " + "{0:.2f}".format(Decimal(self.size)) + " " + self.product_id + " @ " + "{0:.2f}".format(Decimal(self.price))
#         #self.tweet = "Got a fill!\n" + self.message + "\nSent at: " + self.time_now
#         #print("\n" + self.tweet)
#         print("Peter")
# #         
# #     def send_message_to_slack(self, text):     
# #         post = {"text": "{0}".format(text)}
# #       
# #         try:
# #             json_data = json.dumps(post)
# #             req = request.Request("https://hooks.slack.com/services/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",
# #                                   data=json_data.encode('ascii'),
# #                                   headers={'Content-Type': 'application/json'}) 
# #             resp = request.urlopen(req)
# #         except Exception as em:
# #             print("EXCEPTION: " + str(em))                                                                                                                      