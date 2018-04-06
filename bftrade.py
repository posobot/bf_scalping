#!/usr/bin/python3
import time
import sys
import exchangeFunc
import func
from datetime import datetime
from exchangeFunc import TIME_FRAME


# ---- 1分足スキャbot用 ----
SMA_COUNT = 7                           # 1分足何本分の平均価格を使うか
NO_ENTRY_DIFF_FROM_SMA = 1500           # 平均価格と現在価格がこれだけ離れていたらNO ENTRY
NO_ENTRY_DIFF_FROM_LATEST_MEDIAN = 1000  # 前回の足の中央値と現在価格がこれだけ離れていたらNO ENTRY
ENTRY_DIFF = 100                        # エントリー価格(現在価格に±して使う)
PROFIT_DIFF = 189                       # 利確幅
STOP_LOSS_DIFF = 150                    # 損切り幅
WAIT_AFTER_NOT_ENTRY = 15               # エントリー否定と損切り後に指定した秒数休憩
WAIT_AFTER_STOP_LOSS = 180              # 損切りした後エントリー判定を始めるまでの秒数
WAIT_AFTER_CACEL     = 10               # 注文をキャンセルしてから再度判定を始めるまでの秒数
LOT = 0.001                             # 取引LOT[BTC]


# ---- 定数 ----
LOOP_WAIT_SEC = 5  # 何秒ごとにループを回すか（間隔が短すぎると怒られるので3秒ぐらいかな）
ORDER_CANCEL_SEC = 30
STOP_LOSS_WAIT_SEC = 30  # 損切り後にwaitを入れる

# ---- グローバル変数 ----
order_id = ''  # オーダーID
wait_order_count = 0  # 注文を出してから、ループ何回分役定していないか

# ---- 関数 ----


# S キーを押して強制停止した時にポジションがあれば成り行きで手放す
def exit_program():
    size = exchangeFunc.get_current_order_size()
    print("exit market trade:" + str(size))
    if size > 0:
        print(' exit Sell! #############')
        # 成り行きで売る
        exchangeFunc.market_sell(abs(size))

    elif size < 0:
        print(' exit Buy! #############')
        # 成り行きで買う
        exchangeFunc.market_buy(abs(size))

    cancel_all_orders()


# 全オーダーをキャンセル
def cancel_all_orders():
    exchangeFunc.cancel_all_orders()

    global order_id
    order_id = ''

    global wait_order_count
    wait_order_count = 0

# botが売買注文を出す
def bot_buy_and_sell(last_price):
    is_buy = False
    is_sell = False

    global wait_order_count
    wait_order_count = 0

    ohlcv = exchangeFunc.fetch_ohlcv(TIME_FRAME.MIN_1)
    # 1分足SMA_COUNT分の平均価格
    sma = exchangeFunc.sma(ohlcv, SMA_COUNT)
    # 前回中央値
    latest_median = exchangeFunc.get_latest_ohlcv_median(ohlcv)
    # 平均価格と現在価格の差
    diff_sma = abs(last_price - sma)
    # 前回中央値と現在価格の差
    diff_median = abs(last_price - latest_median)
    
    # debug出力
    dict = {
        "last_price" : last_price,
        "sma" : sma,
        "latest_median" : latest_median,
        "diff_sma" : diff_sma,
        "diff_median" : diff_median
    }
    func.print_format_bulk(dict)

    if diff_sma > NO_ENTRY_DIFF_FROM_SMA:
        # 平均価格と現在価格が離れすぎていたらエントリーしない
        time.sleep(WAIT_AFTER_NOT_ENTRY)
        return

    if diff_median > NO_ENTRY_DIFF_FROM_LATEST_MEDIAN:
        # 前回中央値と現在価格が離れすぎていたらエントリーしない
        time.sleep(WAIT_AFTER_NOT_ENTRY)
        return

    global order_id
    profit_order_price = 0
    stop_loss_order_price = 0
    
    is_buy = True
    if last_price <= sma:
        # -- ショート --
        func.print_format("---SELL SIGN---")
        
        is_buy = False
        price = last_price + ENTRY_DIFF
        # 利確金額を決める
        profit_order_price = price - PROFIT_DIFF
        # 損切金額を決める
        stop_loss_order_price = price + STOP_LOSS_DIFF
    elif last_price > sma:
        # -- ロング --
        func.print_format("---BUY SIGN---")
        
        price = last_price - ENTRY_DIFF
        # 利確金額を決める
        profit_order_price = price + PROFIT_DIFF
        # 損切金額を決める
        stop_loss_order_price = price - STOP_LOSS_DIFF
        
        dict = {
            "price" : str(price),
            "profit_order_price" : str(profit_order_price),
            "stop_loss_order_price" : str(stop_loss_order_price)
        }
        func.print_format_bulk(dict)
    
    # BFではIFDOCOで注文を出す
    order_id = exchangeFunc.create_ifdoco_order(is_buy, LOT, price, profit_order_price, stop_loss_order_price)
    return price


# ---- メインループ ----
while True:
    key = func.get_key()
    # enterで終了、キー入力があれば表示
    if key == 115:  # 's' の入力
        exit_program()
        sys.exit()

    # 最終取引価格を取得
    last_price = exchangeFunc.get_last_price()
    open_order_count = exchangeFunc.fetch_open_orders()
    order_size = exchangeFunc.get_current_order_size(order_id)
    
    # 売買注文を出す
    if open_order_count == 0 and order_size == 0:
        if order_id == '':
            order_id = bot_buy_and_sell(last_price)
        else:
            # 注文中の時の処理
            wait_order_count += 1
            if wait_order_count * LOOP_WAIT_SEC >= ORDER_CANCEL_SEC:
                # 一定時間オーダーが通らなかったらキャンセル
                print("--- cancel order ---")
                cancel_all_orders()
                time.sleep(WAIT_AFTER_CACEL)
                continue
            else:
                time.sleep(LOOP_WAIT_SEC)
                continue

    # ループ間隔
    time.sleep(LOOP_WAIT_SEC)
