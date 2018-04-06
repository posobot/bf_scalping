import time
import ccxt
import requests
import sys

REAL_TRADE = 1 # 本番に繋ぐ時はこちら側だけ有効にする
# REAL_TRADE = 0 # testnetに繋ぐ時はこちら側だけ有効にする

# 接続先
EXCHANGE_BITMEX = 1
EXCHANGE_BITFLYER = 2
# TRADE_EXCHANGE = EXCHANGE_BITMEX  # BITMEXに接続
TRADE_EXCHANGE = EXCHANGE_BITFLYER  # BITFLYERに接続

API_RETRY_MAX = 5   # API呼び出しretry上限回数
RETRY_WAIT = 0.5    # APIの呼び出しで例外が発生した時のwait

def is_bitmex():
    return TRADE_EXCHANGE == EXCHANGE_BITMEX
    
    
def is_bitflyer():
    return TRADE_EXCHANGE == EXCHANGE_BITFLYER

class TIME_FRAME:
    MIN_1 = 1,
    MIN_3 = 2,
    MIN_5 = 3,
    MIN_15 = 4,
    MIN_30 = 5,
    HOUR_1 = 6,
    HOUR_2 = 7,
    HOUR_4 = 8,
    HOUR_6 = 9,
    HOUR_12 = 10,
    DAY_1 = 11,
    DAY_3 = 12,
    WEEK_1 = 13,
    WEEK_2 = 14,
    MONTH_1 = 15,


class OHLCV_INDEX:
    TIME = 0,
    OPEN = 1,
    HIGH = 2,
    LOW = 3,
    CLOSE = 4


class PIVOT:
    R3 = 0,
    R2 = 1,
    R1 = 2,
    P = 3,
    S1 = 4,
    S2 = 5,
    S3 = 6,

if TRADE_EXCHANGE == EXCHANGE_BITMEX:
    TRADE_PAIR = 'BTC/USD'
elif TRADE_EXCHANGE == EXCHANGE_BITFLYER:
    TRADE_PAIR = 'FX_BTC_JPY'

# bitmexを利用するために初期化(他人に共有しちゃだめ)
if REAL_TRADE == 0:
    # testnet
    exchange = ccxt.bitmex({
        'apiKey': '',
        'secret': '',
    })
    # testnetを使うときのみ必要
    # これを書くと、'https://www.bitmex.com' → 'https://testnet.bitmex.com'に接続先が変わる
    exchange.urls['api'] = exchange.urls['test']
else:
    # 本番
    if TRADE_EXCHANGE == EXCHANGE_BITMEX:
        exchange = ccxt.bitmex({
            'apiKey': '',
            'secret': '',
        })
    elif TRADE_EXCHANGE == EXCHANGE_BITFLYER:
        exchange = ccxt.bitflyer({
            "apiKey": "",
            "secret": ""
        })


# 指値買い
def limit_buy(price, size, retry_count=0):
    try:
        order = exchange.create_order(TRADE_PAIR, type='limit', side='buy', price=price, amount=size)
    except Exception:
        if retry_count < API_RETRY_MAX:
            time.sleep(RETRY_WAIT)
            limit_buy(price, size, retry_count + 1)
        else:
            raise

    print('Entry limit buy: ')
    print(order)
    return order


# 指値売り
def limit_sell(price, size, retry_count=0):
    try:
        order = exchange.create_order(TRADE_PAIR, type='limit', side='sell', price=price, amount=size)
    except Exception:
        if retry_count < API_RETRY_MAX:
            time.sleep(RETRY_WAIT)
            limit_sell(price, size, retry_count + 1)
        else:
            raise

    print('Entry limit sell:')
    print(order)
    return order


# 成り行き買い
def market_buy(size, retry_count=0):
    try:
        order = exchange.create_order(TRADE_PAIR, type='market', side='buy', amount=size)
    except Exception:
        if retry_count < API_RETRY_MAX:
            time.sleep(RETRY_WAIT)
            market_buy(retry_count + 1)
        else:
            raise
            
    return order


# 成り行き売り
def market_sell(size, retry_count=0):
    try:
        order = exchange.create_order(TRADE_PAIR, type='market', side='sell', amount=size)
    except Exception:
        if retry_count < API_RETRY_MAX:
            time.sleep(RETRY_WAIT)
            market_sell(retry_count + 1)
        else:
            raise
            
    return order


def fetch_order(orderId, retry_count=0):
    try:
        return exchange.fetch_order(orderId, TRADE_PAIR)
    except Exception:
        if retry_count < API_RETRY_MAX:
            time.sleep(RETRY_WAIT)
            fetch_order(orderId, retry_count + 1)
        else:
            raise


def fetch_orders(retry_count=0):
    try:
        orders = exchange.fetch_orders(TRADE_PAIR)
    except Exception:
        if retry_count < API_RETRY_MAX:
            time.sleep(RETRY_WAIT)
            fetch_orders(retry_count + 1)
        else:
            raise
            
    return orders


def fetch_open_order(retry_count=0):
    try:
        orders = exchange.fetch_open_orders(TRADE_PAIR)
    except Exception:
        if retry_count < API_RETRY_MAX:
            time.sleep(RETRY_WAIT)
            fetch_open_order(retry_count + 1)
        else:
            raise
            
    return orders


def fetch_open_order_count(retry_count=0):
    return len(fetch_open_order())


# オーダーキャンセル
def cancel_order(orderId, retry_count=0):
    try:
        orders = exchange.cancel_order(orderId, TRADE_PAIR)
    except ccxt.base.errors.OrderNotFound:
        print("order cancel済")
    except Exception:
        if retry_count < API_RETRY_MAX:
            time.sleep(RETRY_WAIT)
            cancel_order(orderId, retry_count + 1)
        else:
            raise


def cancel_all_orders(retry_count=0):
    if TRADE_EXCHANGE == EXCHANGE_BITMEX:
        orders = fetch_open_order()
        for order in orders:
            if order['remaining'] > 0:
                cancel_order(order['id'])
    elif TRADE_EXCHANGE == EXCHANGE_BITFLYER:
        exchange.private_post_cancelallchildorders(params = { "product_code" : TRADE_PAIR})

def fetch_open_orders():
    if TRADE_EXCHANGE == EXCHANGE_BITFLYER:
        orders = exchange.private_get_getparentorders(params = { "product_code" : TRADE_PAIR, "parent_order_state" : "ACTIVE" })
        return len(orders)

def get_current_order_size(orderId=None, retry_count=0):
    if TRADE_EXCHANGE == EXCHANGE_BITMEX:
        pos_list = exchange.private_get_positions()
        for pos in pos_list:
            if pos['symbol'] == 'XBTUSD':
                return pos['currentQty']
            
    elif TRADE_EXCHANGE == EXCHANGE_BITFLYER:
        pos_list = exchange.private_get_getpositions(params = { "product_code" : TRADE_PAIR })
        
        size = 0
        
        for pos in pos_list:
            size += pos['size']
        
        return size
        
    
    return 0

def get_ticker(retry_count=0):
    # こういう数値が取れる
    # 'symbol': 'BTC/USD',
    # 'timestamp': 1521123625553,
    # 'datetime': '2018-03-15T14:20:26.553Z',
    # 'high': 8350.0,
    # 'low': 7600.0,
    # 'bid': 8328.0,
    # 'ask': 8329.0,
    # 'vwap': 7996.8013,
    # 'open': 8199.5,
    # 'close': 8329.0,
    # 'last': 8329.0,
    # 'previousClose': None,
    # 'change': 129.5,
    # 'percentage': 1.5793645954021587,
    # 'average': 8264.25,
    # 'baseVolume': 19631.621860730003,
    # 'quoteVolume': 156973738.0,
    # 'info': {'timestamp': '2018-03-16T00:00:00.000Z', 'symbol': 'XBTUSD', 'open': 8199.5, 'high': 8350, 'low': 7600, 'close': 8329, 'trades': 28708, 'volume': 156973738, 'vwap': 7996.8013, 'lastSize': 800, 'turnover': 1963162186073, 'homeNotional': 19631.621860730003, 'foreignNotional': 156973738}
    return exchange.fetch_ticker(TRADE_PAIR)


def get_last_price():
    return get_ticker()['last']


# timeframeに合わせて価格情報を取得
def fetch_ohlcv(timeFrame, orderId=""):
    sec = 0
    if timeFrame == TIME_FRAME.MIN_1:
        sec = 60
    elif timeFrame == TIME_FRAME.MIN_3:
        sec = 60 * 3
    elif timeFrame == TIME_FRAME.MIN_5:
        sec = 60 * 5
    elif timeFrame == TIME_FRAME.MIN_15:
        sec = 60 * 15
    elif timeFrame == TIME_FRAME.MIN_30:
        sec = 60 * 30
    elif timeFrame == TIME_FRAME.HOUR_1:
        sec = 60 * 60
    elif timeFrame == TIME_FRAME.HOUR_2:
        sec = 60 * 60 * 2
    elif timeFrame == TIME_FRAME.HOUR_4:
        sec = 60 * 60 * 4
    elif timeFrame == TIME_FRAME.HOUR_6:
        sec = 60 * 60 * 6
    elif timeFrame == TIME_FRAME.HOUR_12:
        sec = 60 * 60 * 12
    elif timeFrame == TIME_FRAME.DAY_1:
        sec = 60 * 60 * 24
    elif timeFrame == TIME_FRAME.DAY_3:
        sec = 60 * 60 * 24 * 3
    elif timeFrame == TIME_FRAME.WEEK_1:
        sec = 60 * 60 * 24 * 7
    elif timeFrame == TIME_FRAME.WEEK_2:
        sec = 60 * 60 * 24 * 14
    elif timeFrame == TIME_FRAME.MONTH_1:
        sec = 60 * 60 * 24 * 30
        
    sec = str(sec)
    
    if TRADE_EXCHANGE == EXCHANGE_BITMEX:
        r = requests.get('https://api.cryptowat.ch/markets/bitmex/btcusd-perpetual-futures/ohlc?periods=' + sec)
        return r.json()['result'][sec]
    elif TRADE_EXCHANGE == EXCHANGE_BITFLYER:
        r = requests.get('https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc', params = { "periods" : sec, "after" : orderId }, timeout = 5)
        return r.json()['result'][sec]


def pivot(time_frame_type):
    row = fetch_ohlcv(time_frame_type)

    Last1D = row[len(row) - 2]

    HIGH = Last1D[2]
    LOW = Last1D[3]
    CLOSE = Last1D[4]
    PIVOT = round((HIGH + LOW + CLOSE) / 3, 1)
    r3 = round(HIGH + 2 * (PIVOT - LOW))
    r2 = round(PIVOT + (HIGH - LOW))
    r1 = round((2 * PIVOT) - LOW)
    s1 = round((2 * PIVOT) - HIGH)
    s2 = round(PIVOT - (HIGH - LOW))
    s3 = round(LOW - 2 * (HIGH - PIVOT))
    return r3, r2, r1, PIVOT, s1, s2, s3

def sma(ohlcv, n):
    result = 0
    for i in range(n):
        result += ohlcv[-i - 2][OHLCV_INDEX.CLOSE]
    result = result / n
    return round(result)


def get_latest_ohlcv_median(ohlcv):
    latest = ohlcv[len(ohlcv) - 2]

    h = ohlcv[len(ohlcv) - 2][2]
    l = ohlcv[len(ohlcv) - 2][3]

    return round((h + l) / 2)
    
    
def create_ifdoco_order(is_buy, order_size, ifd_price, profit_price, stop_loss_price, retry_count = 0):
    if is_bitflyer() == False:
        # BFのみ対応
        print("IFDOCO order not support")
        sys.exit()
        
    if is_buy:
        side = "BUY"
        other_side = "SELL"
    else:
        side = "SELL"
        other_side = "BUY"
        
    try:
        
        parent_id = exchange.private_post_sendparentorder(params = {
                "order_method" : "IFDOCO", 
                "minute_to_expire" : 10000, 
                "time_in_force" :  "GTC",
                "parameters" : [
                    {
                        #IFD：指値で買い注文、約定したらOCO注文
                        "product_code": TRADE_PAIR,
                        "condition_type": "LIMIT",
                        "side": side,
                        "price": ifd_price,
                        "size": order_size,
                    },{
                        #OCO①：指値で利確注文
                        "product_code": TRADE_PAIR, 
                        "condition_type": "LIMIT", 
                        "side": other_side,
                        "price": profit_price,
                        "size": order_size,
                    },{
                        #OCO②ストップ注文、トリガー価格を下回ったら成行で損切
                        "product_code": TRADE_PAIR, 
                        "condition_type": "STOP", 
                        "side": other_side,
                        "trigger_price": stop_loss_price,
                        "size": order_size,
                    }
                ]
            }
        )
        # order_id = exchange.private_get_getparentorder(params = {"parent_order_acceptance_id" : parent_id})
    except Exception:        
        if retry_count < 0:
            time.sleep(RETRY_WAIT)
            create_ifdoco_order(is_buy, order_size, ifd_price, profit_price, stop_loss_price, retry_count + 1)
        else:
            raise
    
    return parent_id['parent_order_acceptance_id']