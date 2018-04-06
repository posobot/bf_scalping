import fcntl
import termios
import sys
import os
import datetime
import pytz

jst = pytz.timezone('Asia/Tokyo')

def get_key():
    fno = sys.stdin.fileno()

    #stdinの端末属性を取得
    attr_old = termios.tcgetattr(fno)

    # stdinのエコー無効、カノニカルモード無効
    attr = termios.tcgetattr(fno)
    attr[3] = attr[3] & ~termios.ECHO & ~termios.ICANON # & ~termios.ISIG
    termios.tcsetattr(fno, termios.TCSADRAIN, attr)

    # stdinをNONBLOCKに設定
    fcntl_old = fcntl.fcntl(fno, fcntl.F_GETFL)
    fcntl.fcntl(fno, fcntl.F_SETFL, fcntl_old | os.O_NONBLOCK)

    chr = 0

    try:
        # キーを取得
        c = sys.stdin.read(1)
        if len(c):
            while len(c):
                chr = (chr << 8) + ord(c)
                c = sys.stdin.read(1)
    finally:
        # stdinを元に戻す
        fcntl.fcntl(fno, fcntl.F_SETFL, fcntl_old)
        termios.tcsetattr(fno, termios.TCSANOW, attr_old)

    return chr
    
# dictionary型に入ったkey, valueを見やすく出力
def print_format_bulk(dict):
    now = datetime.datetime.now(jst)
    print_str = '{0:%m/%d %H時%M分%S秒}'.format(now) + " "
    
    for k, v in dict.items():
        print_str += k + ":" + str(v) + " "
        
    print(print_str)
    
def print_format(str):
    now = datetime.datetime.now(jst)
    print_str = '{0:%m/%d %H時%M分%S秒}'.format(now) + " " + str
    print(print_str)