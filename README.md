# Mean_Reversion

Mean Reversion is probably the most basic trading algorithm. It relies solely on the idea that stock prices will fluctuate about a "mean value," and as they rise above that mean value they are likely to come back down, and if they are below that value they are likely to pull back up. While the underlying basis for this premise is certainly true, the details of when to initiate a short or long position are critical to successful exection of this strategy.

For the example script that I have attached here, I look at the average high and average low of a stock for the previous five days (though you can easily change this "index" value early in the script). When the stock price trends above the average high, the script goes short, and if it dips below the average low, it goes long. As we expect the price to revert to the mean, we should have a positive return.

Values to play with include the number of days to average over to define highs and lows, the stop-loss and stop-profit values, as well as other modifications to the initiation of the trade, either the value or external factors such as sentiment.
