'''
1.读取一个投资组合配置，包括标的和配置比例
2.按配置比例分配资金
3.根据策略交易
'''

#from __future__ import (absolute_import, division, print_function,unicode_literals)
#import os.path  # To manage paths
#import sys  # To find out the script name (in argv[0])
# from backtrader.analyzers import leverage
# from backtrader.dataseries import TimeFrame
# from backtrader.observers import benchmark
#from os import write  # For datetime objects
#import pyfolio as pf

import datetime
import backtrader as bt
import pandas as pd
import yfinance as yf
import notebooks.kingStrategies as ks
import numpy as np

# #读取投资组合配置
# df_allocation=pd.read_csv("data/skydog_port_conf.csv")
# df_allocation.columns=['ticker','allocation']
# allocation=df_allocation.set_index('ticker').T.to_dict('record')
# allocation=allocation[0]

#定义投资组合配置
allocation={'QQQ':0.5,
            'TLT':0.2}





#全局参数
start_date=datetime.date(2021,1,1)
end_date=datetime.date(2022,8,1)
writer=pd.ExcelWriter('./output/test.xlsx')


if __name__ == '__main__':    
    # 创建主控制器    
    cerebro = bt.Cerebro()    
    
    # 加入策略    
    cerebro.addstrategy(ks.PortSmaCross) 

    #准备回测数据
    for ticker,allocation in allocation.items():
        data=bt.feeds.PandasData(dataname=yf.download(ticker, start_date, end_date, auto_adjust=True),plot=False)
        data.allocation=allocation
        cerebro.adddata(data,name=ticker) 
    #benchmark_data=bt.feeds.PandasData(dataname=yf.download('QQQ', start_date, end_date, auto_adjust=True),plot=False)
    #cerebro.adddata(benchmark_data)
  
    
    # broker设置资金、手续费 \
    # myborker=bt.brokers.BackBroker(cash=1000000,commission=0.001,checksubmit=False)  
    # cerebro.broker=myborker 
    cerebro.broker.setcash(1000000.0)    
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_checksubmit(checksubmit=False)
 

    print('Starting Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(),cerebro.broker.getcash()))  


    # Analyzer
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='mysharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown,_name='mydrawdown')
    #cerebro.addanalyzer(bt.analyzers.Returns,_name='myreturn')
    cerebro.addanalyzer(bt.analyzers.Transactions,_name='mytrans')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')

    #Observer
    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.FundValue)
    #cerebro.addobserver(bt.observers.TimeReturn,timeframe=bt.TimeFrame.NoTimeFrame)
    #cerebro.addobserver(bt.observers.Benchmark,data=benchmark_data, timeframe=bt.TimeFrame.NoTimeFrame)
    cerebro.addobserver(bt.observers.DrawDown)
    

            

    # 启动回测    
    thestrats=cerebro.run(stdstats=False) #参数stdstats控制是否显添加默认的observer
    thestrat = thestrats[0] 

    #保持测试结果到CSV
    pyfoliozer = thestrat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
    returns.to_csv('./output/test_returns.csv')
    transactions.to_csv('./output/test_transactions.csv')


    #绩效评测
    print('End Portfolio Value: %.2f' % cerebro.broker.getvalue())  
    print('最大回撤:', thestrat.analyzers.mydrawdown.get_analysis()['max'])
    cerebro.plot()     



   











