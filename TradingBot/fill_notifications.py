# This script will run and check if there are any fills.
# If there is a fill then I will send the fill message via a Twitter direct message

# Log in and check if any fills occur

import gdax
import config
import time
import twitter
import datetime

from decimal import Decimal

LIVE = True


###############################

if LIVE == True:
    myKeys = config.live
else:
    myKeys = config.sandbox
    
print("My keys are: ")
for key, value in myKeys.items():
    print(key + ": " + value)
    
if LIVE == True:
    auth_client = gdax.AuthenticatedClient(myKeys['key'], myKeys['secret'], myKeys['passphrase'])
else:
    auth_client = gdax.AuthenticatedClient(myKeys['key'], myKeys['secret'], myKeys['passphrase'],
                                               api_url="https://api-public.sandbox.gdax.com")

my_accounts = auth_client.get_accounts()

if len(my_accounts) < 3:
    print(my_accounts['message'])
else:
    for account in my_accounts:
        print("\n" + account['currency'] + " Account:")
        for key, value in account.items():
            print(key + ": " + value)

# Every Minute check to see if we had a fill
my_fills = auth_client.get_fills(product_id='BTC-USD')
my_fills = my_fills[0]

# Add these fills to a new list
rec_fills = my_fills[:]

print("\nCurrent number of reconciled Fills: "+ str(len(my_fills)))
    
#max_repetitions = 4
count = 0
# Now we pull again to see if we have any fills after this fill.
while True:
    print("\n" + str(datetime.datetime.now()) + " - Checking for new fills...")
    newFill = False
    
    # Pull to get 10 most recent fills
    my_fills = auth_client.get_fills(product_id='BTC-USD', limit='10')
    my_fills = my_fills[0]

    # Check to see if any of those are not in the Rec'd list
    for fill in my_fills:
        if fill not in rec_fills:
            # Add Fill to Rec'd fills list and print fill info
            print("\nAcknowledging the following fill:")
            for key, value in fill.items():
                print(key + ": " + str(value))
            rec_fills.append(fill)
            newFill = True
            message = fill['side'].title() + " " + "{0:.2f}".format(Decimal(fill['size'])) + " " + fill['product_id'] + " @ " + "{0:.2f}".format(Decimal(fill['price']))
            
            # Send Twitter Notification
            twitterNotification = twitter.TwitterNotification(message)
            twitterNotification.send_notification()
    
    if newFill == True:
        print("\nFinished adding new fills. Current Number of Reconciled fills: " + str(len(rec_fills)))
    else:
        print("No new fills...")

    count = count + 1
    time.sleep(30)








#import twitter

# Send Twitter Notification
#twitterNotification = twitter.TwitterNotification("Buy 0.01 BTC @ 3753.24")
#twitterNotification.send_notification()
