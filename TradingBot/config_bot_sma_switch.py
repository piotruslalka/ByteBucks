# Package Trade Settings as a dictionary so you can simply pass that into OrderBook
strategy_settings = {
    'strategy_name': "bot_sma_switch",
    'order_size': 0.002,
    'buy_initial_offset': 1,
    'sell_initial_offset': 1,
    'buy_additional_offset': 1,
    'sell_additional_offset': 1,
    'max_long_position': 100,
    'max_short_position': 100,
    'fill_notifications': True,
    'place_notifications': False,
    'connection_notifications': True,
}
