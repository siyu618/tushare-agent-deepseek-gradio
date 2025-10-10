from collections import defaultdict
from typing import List

import tushare as ts
import pandas as pd
import time

from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 初始化 tushare API
token = '15a8b539980b03878d71c3e1d8a57d6e5a718e68e720e6c0b0e0dbce'
pd.options.display.max_columns = None
pro = ts.pro_api(token=token)

# 获取历史数据的函数
def get_stock_data(ts_code: str, start_date: str, end_date: str, freq='D', ma: list = [5, 10, 20, 30, 60, 120]):
    """ 获取指定股票的历史数据，包括均线 """
    return ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, freq=freq, ma=ma)

# 定义 StatInfo 类来封装每一天的统计数据
class StatInfo:
    def __init__(self, ts_code=None, trade_date=None, open_price=None, close_price=None,  pre_close=None, volume=None, moving_averages=None):
        self.ts_code = ts_code
        self.trade_date = trade_date
        self.open_price = open_price
        self.close_price = close_price
        self.pre_close = pre_close
        self.volume = volume
        self.moving_averages = moving_averages
        self.is_up = self._is_up()  # 判断当天是否上涨
        self.moving_averages_in_range = self._moving_averages_in_range()

    def _is_up(self):
        """ 判断当天是否上涨 """
        if self.close_price > self.pre_close:
            return True
        if self.open_price is not None and self.close_price is not None:
            return self.close_price > self.open_price
        return None

    def _moving_averages_in_range(self):
        """
        判断均线价格是否在开盘价和收盘价之间
        :return: 字典 {均线名称: 是否在范围内}
        """
        if self.open_price is None or self.close_price is None:
            return {f"MA_{days}": None for days in [5, 10, 20, 30, 60, 120]}

        return {
            f"MA_{days}": (min(self.open_price, self.close_price, self.pre_close) <= ma <= max(self.open_price, self.close_price))
            if ma is not None else False
            for days, ma in zip([5, 10, 20, 30, 60, 120], self.moving_averages)
        }

    def __repr__(self):
        return (f"StatInfo(ts_code={self.ts_code}, trade_date={self.trade_date}, is_up={self.is_up}, volume={self.volume}, "
                f"moving_averages_in_range={self.moving_averages_in_range})")

# 策略匹配
def match_policy(pre_day: StatInfo, cur_day: StatInfo, next_day: StatInfo) -> bool:
    if not pre_day.is_up or not cur_day.is_up or not next_day.is_up:
        return False
    if not (cur_day.volume / pre_day.volume > 3 and cur_day.volume / next_day.volume > 3):
        return False
    return sum(value is True for value in cur_day.moving_averages_in_range.values()) >= 4
    # return all(cur_day.moving_averages_in_range.values())
    #return True
    # return all(pre_day.moving_averages_in_range.values()) or all(cur_day.moving_averages_in_range.values())  # 检查均线是否都在范围内

# 获取符合策略的日期（封装所有步骤）
def get_stock_match_days(ts_code: str, start_date: str, end_date: str, freq = 'D', ma: list = [5, 10, 20, 30, 60, 120]) -> list:
    """
    获取符合策略的股票匹配日期
    结合了获取股票数据、生成统计信息列表以及策略匹配的步骤
    """
    # 获取数据
    df = get_stock_data(ts_code, start_date, end_date, freq, ma)
    # print(df.info)

    # 创建 StatInfo 实例列表
    stat_info_list = []
    for _, row in df.iterrows():
        stat_info = StatInfo(
            ts_code=row['ts_code'],
            trade_date=row['trade_date'],
            open_price=row['open'],
            close_price=row['close'],
            pre_close=row['pre_close'],
            volume=row['vol'],
            moving_averages=[row['ma5'], row['ma10'], row['ma20'], row['ma30'], row['ma60'], row['ma120']]
            #moving_averages=[row['ma_v_5'], row['ma_v_10'], row['ma_v_20'], row['ma_v_30'], row['ma_v_60'], row['ma_v_120']]
        )
        # print(stat_info)
        stat_info_list.append(stat_info)

    # 反转列表，使最新的数据在前
    stat_info_list.reverse()
    print(len(stat_info_list))
    # 获取符合策略的日期
    stock_match_days = []
    for i in range(1, len(stat_info_list) - 1):
        pre_day = stat_info_list[i - 1]
        cur_day = stat_info_list[i]
        next_day = stat_info_list[i + 1]
        # print(cur_day.trade_date)
        if match_policy(pre_day, cur_day, next_day):
            stock_match_days.append(cur_day.trade_date)

    return stock_match_days

# 使用示例
# stock_match_days = get_stock_match_days(ts_code='601933.SH', start_date='20221110', end_date='20241110', freq='D')
# #stock_match_days = get_stock_match_days(ts_code='601933.SH', start_date='20231110', end_date='20241110', freq='W', ma=[1, 2, 4, 6, 12, 24])
#
# print("601933.SH stock match days: ", stock_match_days)

# exit(0)

class Stock:
    def __init__(self, ts_code, name):
        self.ts_code = ts_code  # 股票代码
        self.name = name        # 股票名称

    def __repr__(self):
        return f"Stock(ts_code={self.ts_code}, name={self.name})"

def get_all_live_stocks() -> List[Stock]:
    df = pro.stock_basic(list_status='L')
    # 创建 Stock 对象列表 stock_list
    stock_list = [Stock(ts_code=row['ts_code'], name=row['name']) for _, row in df.iterrows()]
    return stock_list


lock = Lock()
res = []
# 定义处理单个股票的函数
def process_stock(stock):
    t_start_in = time.time()
    print(f"Processing {stock.name}, {stock.ts_code}")

    # 调用 get_stock_match_days 以获取匹配日期
    stock_match_days = get_stock_match_days(ts_code=stock.ts_code, start_date=start_day, end_date=end_day, freq='M')

    t_end_in = time.time()
    print(f"{stock.ts_code} processed in {t_end_in - t_start_in:.2f} seconds")

    # 如果有匹配日期，用锁保护对 res 的访问
    if stock_match_days:
        with lock:
            res.append((stock, stock_match_days))
    return stock

global end_day, start_day

def count_avg_stocks():
    global end_day, start_day, res
    current_date = datetime.now()
    ten_days_ago = current_date - timedelta(days=365 * 2)
    end_day = current_date.strftime('%Y%m%d')
    start_day = ten_days_ago.strftime('%Y%m%d')
    res = []
    print("all stocks: ", len(get_all_live_stocks()))
    # exit(0)
    # 记录总的开始时间
    t_start = time.time()
    # 使用线程池执行任务
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_stock, stock) for stock in get_all_live_stocks()]

        # 确保每个线程正常执行并记录其结果
        for future in as_completed(futures):
            future.result()  # 确保捕获任务的返回值，但不使用
    # 记录总的结束时间
    t_end = time.time()
    print(f"Total processing time: {t_end - t_start:.2f} seconds")
    print("Result:", res)


if __name__ == "__main__":
    count_avg_stocks()

# res = []
# lock = Lock()
# t_start = time.time()
# for i, stock in enumerate(get_all_live_stocks()):
#     t_start_in = time.time()
#     print(i, " processing ", stock.name, stock.ts_code)
#     stock_match_days = get_stock_match_days(ts_code=stock.ts_code, start_date=start_day, end_date=end_day)
#     print(i, " one cost ", time.time() - t_start_in)
#     if len(stock_match_days) > 0:
#         print(stock.ts_code, stock.name, stock_match_days)
#         res.append([stock, stock_match_days])
# print("total cost ", time.time() - t_start)
# print(res)
#
#
