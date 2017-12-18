#Nick Schmandt (n.schmandt@gmail.com), CloudQuant, 12/18/17

from cloudquant.interfaces import Strategy
import numpy as np

lime_midpoint_limit_buy = "4e69745f-5410-446c-9f46-95ec77050aa5"
lime_midpoint_limit_sell = "23d56e4a-ca4e-47d0-bf60-7d07da2038b7"

end_delay = 20 # in minutes, how long before the end of the day to stop trading.
start_delay = 10 # in minutes, how long after market open before we start trading.

index=5 # how many days of highs to average over
purchase_range_ratio=.33 # what fraction of the atr for a stock to be bought/shorted
sell_range_ratio=.66 # what fraction of the atr for a stock to be exited from

purchase_amount=25000 # dollar value that we want each purchase to be worth

class breakout_purchase(Strategy):
    
    @classmethod
    def register_event_streams(cls, md, service, account):
        return {'!sentiment/bloomberg/story/news': 'on_bloomberg_news', '!sentiment/stocktwits': 'on_stocktwits', '!sentiment/alexandria': 'on_alexandria_news'}
    
    @classmethod
    def is_symbol_qualified(cls, symbol, md, service, account):
        
        handle_list = service.symbol_list.get_handle('9a802d98-a2d7-4326-af64-cea18f8b5d61') #this is all stocks on S&P500
        return service.symbol_list.in_list(handle_list,symbol)
        
        #return symbol in ['AAPL', 'EBAY', 'AMZN', 'ORCL', 'WMT']
        #return symbol in ['AAPL']
    
    def __init__(self):  

        self.IsPositionOn = False  # do we have a position on?
        self.entry_price = 0  # estimated price of our position
        self.model_start = 0 # time to start, set in on_start
        self.IsShort=False # are we short?
        self.IsPurchasable=True # OK to purchase? (not repurchasing what we already sold)
        self.al_value=0
        self.bb_value=0
        self.st_value=0
    
    def on_finish(self, md, order, service, account):
        pass
    
    def on_alexandria_news(self, event, md, order, service, account):
        
        #this function is called on each alexandria news event
        
        if event.field['Relevance']>.3 and event.field['Sentiment']!=0: #this is a relevance threshold to prevent irrelevant information from being processed.
            #print('Change in %s stock sentiment of %d with confidence %d' % (self.symbol, event.field['Sentiment'], event.field['Confidence']))
            self.al_value+=(event.field['Sentiment'] * (event.field['Confidence']))
            #print('Current alexandria sentiment for %s is %.2f' % (self.symbol, self.al_value))
    
    def on_stocktwits(self, event, md, order, service, account):
        
        #this function is called on each stock twit event, note that for it to work you must have stock twit 
        #included in the register event stream function above.
        
        #each stock twit event includes a number between -1 and +1 that represents the change to the sentiment value
        
        if event.field['sentiment_score']!=0 and type(event.field['sentiment_score'])==float:
            #print('Change in %s stock twit sentiment of %.2f' % (self.symbol, event.field['sentiment_score']))
            self.st_value+=event.field['sentiment_score']
            #print('Current sentiment for %s is %.2f' % (self.symbol, self.st_value))
        
    def on_bloomberg_news(self, event, md, order, service, account):
        
        #this function is called on each bloomberg news event
        
        #bloomberg news events include a Score, +1 or -1, and a Confidence Value that represents the percent 
        #certainty of their prediction (between 1 and 100)
        
        if event.field['Score']!=0:
            #print('Bloomberg event: ' + event.field['Headline'])
            #print('Change in %s stock sentiment of %d with confidence %d' % (self.symbol, event.field['Score'], event.field['Confidence']))
            self.bb_value+=(event.field['Score'] * (event.field['Confidence']))
            #print('Current bloomberg sentiment for %s is %.2f' % (self.symbol, self.bb_value/100))
    
    def on_minute_bar(self, event, md, order, service, account, bar):
        
        #make sure it's not too late in the day
        
        if service.system_time < md.market_close_time - service.time_interval(minutes=end_delay, seconds=1):
            
            #gather some statistics
            md_daily=md.bar.daily(start=-index)
            md_high=md_daily.high
            md_low=md_daily.low
            md_close=md_daily.close
            average_high=np.mean(md_high)
            md_low=md_daily.low
            average_low=np.mean(md_low)
            average_range=np.mean(md_high-md_low)
            
            bar_1 = bar.minute()
            bar_close = bar_1.close
            bar_askvol = bar_1.askvol
            bar_bidvol = bar_1.bidvol
            
            if len(bar_close)>0 and bar_close[0]!=0:
            
                #remove stocks that have already moved outside the trading range
                if (average_high)>bar_close[0] and (average_low)<bar_close[0]:
                    self.IsPurchasable=True

                if self.IsPositionOn == True:
                    # there is a position on, therefore we want to check to see if
                    # we should realize a profit or stop a loss

                    #the stock has dropped too low, exit out of this position
                    if (average_low-sell_range_ratio*average_range)>bar_close[0]:

                        self.IsPositionOn = False
                        # send order; use a variable to accept the order_id that order.algo_buy returns
                        sell_order_id = order.algo_sell(self.symbol, algorithm=lime_midpoint_limit_sell, price=md[self.symbol].L1.bid*.95, intent="exit")
                        print('selling out of {0} at {1} due to stock dropping below average high at {1}'.format(self.symbol, service.time_to_string(service.system_time), bar_close[0]))
                        self.IsPurchasable=False
                        print('stock dropped below acceptable values on long, alexandria sentiment ' + str(self.al_value)\
                             +', bloomberg sentiment ' + str(self.bb_value) + ', stock twit sentiment ' + str(self.st_value))
                        
                    #we've made our target profit, let's back out of the trade now
                    elif (average_low+sell_range_ratio*average_range)<bar_close[0]:

                        self.IsPositionOn = False
                        # send order; use a variable to accept the order_id that order.algo_buy returns
                        sell_order_id = order.algo_sell(self.symbol, algorithm=lime_midpoint_limit_sell, price=md[self.symbol].L1.bid*.95, intent="exit")
                        print('selling out of {0} at {1} due to stock reaching target profit at {2}'.format(self.symbol, service.time_to_string(service.system_time), bar_close[0]))
                        self.IsPurchasable=False
                        print('stock reached profit target on long, alexandria sentiment ' + str(self.al_value)\
                             +', bloomberg sentiment ' + str(self.bb_value) + ', stock twit sentiment ' + str(self.st_value))
                            
                if self.IsShort == True:
                    # there is a position on, therefore we want to check to see if
                    # we should realize a profit or stop a loss
                    
                    #if the price has climbed a lot, exit out of the position
                    if average_high+sell_range_ratio*average_range<bar_close[0]:

                        #print(account[self.symbol].position.shares)
                        self.IsShort = False
                        # send order; use a variable to accept the order_id that order.algo_buy returns
                        order_id = order.algo_buy(self.symbol, algorithm=lime_midpoint_limit_buy, price=md[self.symbol].L1.ask*1.05, intent="exit")
                        print('exiting short of {0} at {1} due to rising above average low at {2}'.format(self.symbol, service.time_to_string(service.system_time), bar_close[0]))
                        self.IsPurchasable=False
                        
                        #print(account[self.symbol].position.shares)
                        print('stock exceeded acceptable values on short, alexandria sentiment ' + str(self.al_value)\
                             +', bloomberg sentiment ' + str(self.bb_value) + ', stock twit sentiment ' + str(self.st_value))

                    #we have made our profit target, exit out of the short
                    if average_high-sell_range_ratio*average_range>bar_close[0]:

                        self.IsShort = False
                        # send order; use a variable to accept the order_id that order.algo_buy returns
                        #print(account[self.symbol].position.shares)
                        order_id = order.algo_buy(self.symbol, algorithm=lime_midpoint_limit_buy, price=md[self.symbol].L1.ask*1.05, intent="exit")
                        print('exiting short by buying shares of {0} at {1} due to stock dropping below sell point at {2}'.format(self.symbol, service.time_to_string(service.system_time), bar_close[0]))
                        self.IsPurchasable=False
                        
                        #print(account[self.symbol].position.shares)
                        print('stock dropped below target on short, alexandria sentiment ' + str(self.al_value)\
                             +', bloomberg sentiment ' + str(self.bb_value) + ', stock twit sentiment ' + str(self.st_value))

                # we want to have at least a certain amount of time left before entering positions
                if service.system_time > self.model_start:
                    #make sure we're not already in a position and the stock hasn't already been bought and resold recently.
                    if self.IsPositionOn == False and self.IsShort == False and self.IsPurchasable==True:

                        # go long if stock drops below the average low
                        if average_low>bar_close[0]:
                            num_shares=np.round(purchase_amount/md[self.symbol].L1.last)
                            print('Purchasing {0} after breakout at {1}, purchased {2} shares at {3}'\
                                  .format(self.symbol, service.time_to_string(service.system_time), num_shares, bar_close[0]))
                            order_id = order.algo_buy(self.symbol, algorithm=lime_midpoint_limit_buy, price=md[self.symbol].L1.ask*1.05, intent="init", order_quantity=num_shares)
                            self.IsPositionOn=True
                            self.entry_price = bar_close[0]

                        # short if the stock is well above its normal values
                        elif average_high<bar_close[0]:
                            num_shares=np.round(purchase_amount/md[self.symbol].L1.last)
                            print('Initiating short of {0} after low breakout at {1}, sold {2} shares at {3}'\
                                  .format(self.symbol, service.time_to_string(service.system_time), num_shares, bar_close[0]))
                            sell_order_id = order.algo_sell(self.symbol, algorithm=lime_midpoint_limit_sell, price=md[self.symbol].L1.bid*.95, intent="init", order_quantity=num_shares)
                            self.IsShort=True
                            self.entry_price = bar_close[0]
                            
        else:
            
            bar_1 = bar.minute()
            bar_close = bar_1.close
            
            #close out on all open positions at the end of the day.
            
            if account[self.symbol].position.shares>0:
                order_id = order.algo_sell(self.symbol, "market", intent="exit")
                print('sold ' + self.symbol + ' at end of day.')
                if len(bar_close)>0:
                    print('Approximate price: ' + str(bar_close[0]))
            elif account[self.symbol].position.shares<0:
                order_id = order.algo_buy(self.symbol, "market", intent="exit")
                print('bought ' + self.symbol + ' at end of day.')
                if len(bar_close)>0:
                    print('Approximate price: ' + str(bar_close[0]))

    def on_start(self, md, order, service, account):
        
        self.model_start = service.system_time + service.time_interval(minutes=start_delay, seconds=1)
        
