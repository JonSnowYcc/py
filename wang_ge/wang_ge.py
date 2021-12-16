'''backtest
start: 2019-07-01 00:00:00
end: 2020-01-03 00:00:00
period: 1m
exchanges: [{"eid":"OKEX","currency":"BTC_USDT"}]
'''

import json
import time
import tushare as ts

# 参数
beginPrice = 5000  # 网格区间开始价格
endPrice = 8000  # 网格区间结束价格
distance = 20  # 每个网格节点的价格距离
pointProfit = 50  # 每个网格节点的利润差价
amount = 0.01  # 每个网格节点的挂单量
minBalance = 300  # 账户最小资金余额（买入时）

# 全局变量
arrNet = []
arrMsg = []
acc = None


def findOrder(orderId, NumOfTimes, ordersList=[]):
    for j in range(NumOfTimes):
        orders = None
        if len(ordersList) == 0:
            orders = _C(exchange.GetOrders)
        else:
            orders = ordersList
        for i in range(len(orders)):
            if orderId == orders[i]["Id"]:
                return True
        time.leep(1000)
    return False


def cancelOrder(price, orderType):
    orders = _C(exchange.GetOrders)
    for i in range(len(orders)):
        if price == orders[i]["Price"] and orderType == orders[i]["Type"]:
            exchange.CancelOrder(orders[i]["Id"])
            time.sleep(500)


def checkOpenOrders(orders, ticker):
    global arrNet, arrMsg
    for i in range(len(arrNet)):
        if not findOrder(arrNet[i]["id"], 1, orders) and arrNet[i]["state"] == "pending":
            orderId = exchange.Sell(arrNet[i]["coverPrice"], arrNet[i]["amount"], arrNet[i], ticker)
            if orderId:
                arrNet[i]["state"] = "cover"
                arrNet[i]["id"] = orderId
            else:
                # 撤销
                cancelOrder(arrNet[i]["coverPrice"], ORDER_TYPE_SELL)
                arrMsg.append("挂单失败!" + json.dumps(arrNet[i]) + ", time:" + _D())


def checkCoverOrders(orders, ticker):
    global arrNet, arrMsg
    for i in range(len(arrNet)):
        if not findOrder(arrNet[i]["id"], 1, orders) and arrNet[i]["state"] == "cover":
            arrNet[i]["id"] = -1
            arrNet[i]["state"] = "idle"
            Log(arrNet[i], "节点平仓，重置为空闲状态。", "#FF0000")


def onTick():
    global arrNet, arrMsg, acc

    print(ts.get_realtime_quotes('600519'));
    ticker = _C(exchange.GetTicker)  # 每次获取当前最新的行情
    for i in range(len(arrNet)):  # 遍历所有网格节点，根据当前行情，找出需要挂单的位置，挂买单。
        if i != len(arrNet) - 1 and arrNet[i]["state"] == "idle" and ticker.Sell > arrNet[i]["price"] and ticker.Sell < \
                arrNet[i + 1]["price"]:
            acc = _C(exchange.GetAccount)
            if acc.Balance < minBalance:  # 如果钱不够了，只能跳出，什么都不做了。
                arrMsg.append("资金不足" + json.dumps(acc) + "！" + ", time:" + _D())
                break

            orderId = exchange.Buy(arrNet[i]["price"], arrNet[i]["amount"], arrNet[i], ticker)  # 挂买单
            if orderId:
                arrNet[i]["state"] = "pending"  # 如果买单挂单成功，更新网格节点状态等信息
                arrNet[i]["id"] = orderId
            else:
                # 撤单
                cancelOrder(arrNet[i]["price"], ORDER_TYPE_BUY)  # 使用撤单函数撤单
                arrMsg.append("挂单失败!" + json.dumps(arrNet[i]) + ", time:" + _D())
    time.sleep(1000)
    orders = _C(exchange.GetOrders)
    checkOpenOrders(orders, ticker)  # 检测所有买单的状态，根据变化做出处理。
    time.sleep(1000)
    orders = _C(exchange.GetOrders)
    checkCoverOrders(orders, ticker)  # 检测所有卖单的状态，根据变化做出处理。

    # 以下为构造状态栏信息，可以查看FMZ API 文档。
    tbl = {
        "type": "table",
        "title": "网格状态",
        "cols": ["节点索引", "详细信息"],
        "rows": [],
    }

    for i in range(len(arrNet)):
        tbl["rows"].append([i, json.dumps(arrNet[i])])

    errTbl = {
        "type": "table",
        "title": "记录",
        "cols": ["节点索引", "详细信息"],
        "rows": [],
    }

    orderTbl = {
        "type": "table",
        "title": "orders",
        "cols": ["节点索引", "详细信息"],
        "rows": [],
    }

    while len(arrMsg) > 20:
        arrMsg.pop(0)

    for i in range(len(arrMsg)):
        errTbl["rows"].append([i, json.dumps(arrMsg[i])])

    for i in range(len(orders)):
        orderTbl["rows"].append([i, json.dumps(orders[i])])

    LogStatus(_D(), "\n", acc, "\n", "arrMsg length:", len(arrMsg), "\n",
              "`" + json.dumps([tbl, errTbl, orderTbl]) + "`")


def main():  # 策略执行从这里开始
    global arrNet
    for i in range(int((endPrice - beginPrice) / distance)):  # for 这个循环根据参数构造了网格的数据结构，是一个列表，储存每个网格节点，每个网格节点的信息如下：
        arrNet.append({
            "price": beginPrice + i * distance,  # 该节点的价格
            "amount": amount,  # 订单数量
            "state": "idle",  # pending / cover / idle           # 节点状态
            "coverPrice": beginPrice + i * distance + pointProfit,  # 节点平仓价格
            "id": -1,  # 节点当前相关的订单的ID
        })

    while True:  # 构造好网格数据结构后，进入策略主要循环
        onTick()  # 主循环上的处理函数，主要处理逻辑
        time.sleep(500)  # 控制轮询频率