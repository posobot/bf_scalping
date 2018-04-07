#!/usr/bin/python3
import time
import sys
import exchangeFunc
import func
from datetime import datetime
from exchangeFunc import TIME_FRAME
import yaml
with open('config.yml', 'r') as yml:
    config = yaml.load(yml)


# ---- 1分足スキャbot用設定 ----
SMA_COUNT                           = config['SMA_COUNT']                       # 1分足何本分の平均価格を使うか
NO_ENTRY_DIFF_FROM_SMA              = config['NO_ENTRY_DIFF_FROM_SMA']          # 平均価格と現在価格がこれだけ離れていたらNO ENTRY
NO_ENTRY_DIFF_FROM_LATEST_MEDIAN    = config['NO_ENTRY_DIFF_FROM_LATEST_MEDIAN']# 前回の足の中央値と現在価格がこれだけ離れていたらNO ENTRY
ENTRY_DIFF                          = config['ENTRY_DIFF']                      # エントリー価格(現在価格に±して使う)
PROFIT_DIFF                         = config['PROFIT_DIFF']                     # 利確幅
STOP_LOSS_DIFF                      = config['STOP_LOSS_DIFF']                  # 損切り幅
WAIT_AFTER_NOT_ENTRY                = config['WAIT_AFTER_NOT_ENTRY']            # エントリー否定と損切り後に指定した秒数休憩
WAIT_AFTER_ORDER_DONE               = config['WAIT_AFTER_ORDER_DONE']           # 利確・損切りした後再度エントリー判定を始めるまでの秒数
WAIT_AFTER_CANCEL                   = config['WAIT_AFTER_CANCEL']               # 注文をキャンセルしてから再度判定を始めるまでの秒数
LOT                                 = config['LOT']                             # 取引LOT[BTC]
LOOP_WAIT_SEC                       = config['LOOP_WAIT_SEC']                   # 何秒ごとにループを回すか（間隔が短すぎると怒られるので3秒ぐらいかな）
ORDER_CANCEL_SEC                    = config['ORDER_CANCEL_SEC']                # オーダーを出してから何秒間約定しなければキャンセルするか

# debug出力
dict = {
    "SMA_COUNT" : SMA_COUNT,
    "NO_ENTRY_DIFF_FROM_SMA" : NO_ENTRY_DIFF_FROM_SMA,
    "NO_ENTRY_DIFF_FROM_LATEST_MEDIAN" : NO_ENTRY_DIFF_FROM_LATEST_MEDIAN,
    "ENTRY_DIFF" : ENTRY_DIFF,
    "PROFIT_DIFF" : PROFIT_DIFF,
    "STOP_LOSS_DIFF" : STOP_LOSS_DIFF,
    "WAIT_AFTER_NOT_ENTRY" : WAIT_AFTER_NOT_ENTRY,
    "WAIT_AFTER_ORDER_DONE" : WAIT_AFTER_ORDER_DONE,
    "WAIT_AFTER_CANCEL" : WAIT_AFTER_CANCEL,
    "LOT" : LOT,
    "LOOP_WAIT_SEC" : LOOP_WAIT_SEC,
    "ORDER_CANCEL_SEC" : ORDER_CANCEL_SEC
}
func.print_format_bulk(dict)

# ---- グローバル変数 ----
order_id = ''  # オーダーID
wait_order_count = 0  # 注文を出してから、ループ何回分役定していないか
is_order_success = False
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

# パラメータの初期化
def init_param():
    global order_id
    order_id = ''

    global wait_order_count
    wait_order_count = 0
    
    global is_order_success
    is_order_success = False
    
# 全オーダーをキャンセル
def cancel_all_orders():
    exchangeFunc.cancel_all_orders()
    init_param()
    

# botが売買注文を出すs
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

    if is_order_success == False and order_size > 0:
        # 注文が通った
        func.print_format("--- 注文確定 ---")
        is_order_success = True
    
    # 売買注文を出す

    if order_id == '':
        if open_order_count == 0 and order_size == 0:
            order_id = bot_buy_and_sell(last_price)
    else:
        if is_order_success == True:
            # 注文が通った場合の処理
            if order_size == 0:
                func.print_format("--- 利確・損切り(TODO: 今回いくら勝ったとか、合計収支とか出す)---")
                
                # 利確or損切りまで済んでいたら再度注文が発生する状態に初期化
                init_param()
                time.sleep(WAIT_AFTER_ORDER_DONE)
                continue
        
        else:        
            # 注文が通っていない時の処理
            
            wait_order_count += 1
            if wait_order_count * LOOP_WAIT_SEC >= ORDER_CANCEL_SEC:
                # 一定時間オーダーが通らなかったらキャンセル
                func.print_format("--- cancel order ---")
                cancel_all_orders()
                time.sleep(WAIT_AFTER_CANCEL)
                continue

    # ループ間隔
    time.sleep(LOOP_WAIT_SEC)
