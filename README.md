# Mean_Reversion
Scripts that trade on stocks likely to revert to their mean price range

This is a base algorithm that buys stocks that have fallen below their average low or shorts stocks that have risen above their average
high. The idea is that as they go beyond their average values from the preceeding days, they will be likely to revert to their means.

Values to play with include the number of days averaged over to determine highs and lows, exactly when the script enters a position (or
a short), and including sentiment values to improve the trading.
