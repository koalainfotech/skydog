# 对整个投资组合回测某个交易策略

import datetime as dt

from backtrader.analyzers import leverage
from backtrader.dataseries import TimeFrame
import strategies.kingStrategies as st
import backtrader as bt
import yfinance as yf
import pandas as pd
import prettytable as pt
import empyrical
import pyfolio as pf



if __name__ == '__main__': 
    #参数
    # port={'QQQ':0.44,
    #       'MCHI':0.07,
    #       'FB':0.1,
    #       '0700.HK':0.05,
    #       'BABA':0.05,
    #       'IBUY':0.05,
    #       'BGNE':0.03,
    #       '1810.HK':0.03,
    #       'ARKQ':0.04,
    #       'ARKG':0.04,
    #       'BIDU':0.02,
    #       'TDOC':0.01,
    #       'UBER':0.01,
    #       'CNK':0.01,
    #       'VIPS':0.01,
    #       'TAL':0.01,
    #       'PDD':0.01,
    #       '0175.HK':0.01,}

    port={'QQQ':0.7,
          'FXI':0.3,
           }


       
        

         
    
    start_date=dt.date(2016,1,1)
    end_date=dt.date.today()
    daysinayear=250
    # mystrategy={'name':'SMA','strategy':st.PortSmaCross,
    #             'args':{'trailpercent':0.12,
    #                     'signalexit':False,
    #                     'fast_days':20,
    #                     'slow_days':60,
    #                     'start_date':start_date
    
    #                     }                           
    #     }

    mystrategy={'name':'Hold','strategy':st.PortBuyAndRebalance1,
                'args':{
                        'start_date':start_date
    
                        }                           
        }

    totalvalue=1000000

    #买入持有定期再平衡组合作为比较基准
    # 创建主控制器    
    cerebro0 = bt.Cerebro()
    
    #准备回测数据
    for ticker,allocation in port.items():
        data=bt.feeds.PandasData(dataname=yf.download(ticker, start_date-dt.timedelta(days=365), end_date, auto_adjust=True),plot=False)
        data.allocation=allocation
        cerebro0.adddata(data,name=ticker) 
    
    # Analyzer
    cerebro0.addanalyzer(bt.analyzers.PyFolio,_name='pyfolio')
    cerebro0.addanalyzer(bt.analyzers.Transactions,_name='mytrans')

    #Observer
    cerebro0.addobserver(bt.observers.TimeReturn,timeframe=bt.TimeFrame.NoTimeFrame)
 
        
    # 加入策略    
    strats = cerebro0.addstrategy(st.PortBuyAndRebalance1,start_date=start_date)
    
    # broker设置资金、手续费    
    cerebro0.broker.setcash(totalvalue)    
    cerebro0.broker.setcommission(commission=0.001,leverage=10)
    cerebro0.broker.set_checksubmit(False)
    
    
    # 启动回测   
    print('Start Portfolio Value: %.2f' % cerebro0.broker.getvalue()) 
    thestrats=cerebro0.run(stdstats=False) #参数stdstats控制是否显添加默认的observer
    thestrat = thestrats[0] 
    print('End Portfolio Value: %.2f' % cerebro0.broker.getvalue()) 

    #绩效评测
    trans=thestrat.analyzers.mytrans.get_analysis()
    pyfoliozer = thestrat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
    returns=returns[start_date:]
    table=pt.PrettyTable(['Strategy','Total Return','Annual Return','Sharpe Ratio','Max Drawdown','Volatility'])
    table.add_row(['Buy and Rebalance',
                    '{:.2%}'.format(empyrical.cum_returns_final(returns=returns)),
                    '{:.2%}'.format(empyrical.annual_return(returns=returns,annualization=daysinayear)),
                    '{:.2f}'.format(empyrical.sharpe_ratio(returns=returns,annualization=daysinayear)),
                    '{:.2%}'.format(empyrical.max_drawdown(returns=returns)),
                    '{:.2%}'.format(empyrical.annual_volatility(returns=returns,annualization=daysinayear))])
    
    returns.to_csv('output/benchmark_rets.csv')




 
    # 创建主控制器    
    cerebro = bt.Cerebro()
        
    #准备回测数据
    for ticker,allocation in port.items():
        price=yf.download(ticker, start_date-dt.timedelta(days=365), end_date, auto_adjust=True)
        data=bt.feeds.PandasData(dataname=price,plot=False)
        data.allocation=allocation
        cerebro.adddata(data,name=ticker)
    
    # Analyzer
    cerebro.addanalyzer(bt.analyzers.PyFolio,_name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.Transactions,_name='mytrans')

    #Observer
    # cerebro.addobserver(bt.observers.Broker)
    # cerebro.addobserver(bt.observers.FundValue)
    cerebro.addobserver(bt.observers.TimeReturn,timeframe=bt.TimeFrame.NoTimeFrame)    

        
    # 加入策略    
    strats = cerebro.addstrategy(mystrategy['strategy'],**mystrategy['args'])
    
    # broker设置资金、手续费    
    cerebro.broker.setcash(totalvalue)    
    cerebro.broker.setcommission(commission=0.001,leverage=10)

    # 启动回测   
    print('Start Portfolio Value: %.2f' % cerebro.broker.getvalue()) 
    thestrats=cerebro.run(stdstats=True) #参数stdstats控制是否显添加默认的observer
    thestrat = thestrats[0] 
    print('End Portfolio Value: %.2f' % cerebro.broker.getvalue()) 

    #保存回测生产的交易记录
    trans=thestrat.analyzers.mytrans.get_analysis()
    df_trans=pd.DataFrame()
    for trans_date,order in trans.items():
            df=pd.DataFrame(order)
            df['trans_date']=trans_date
            df.columns=['quantity','price','sid','ticker','amount','trans_date']
            df_trans=df_trans.append(df)
    df_trans=df_trans[['trans_date','ticker','quantity','price']]
    df_trans=df_trans.reset_index()
    df_trans.to_csv('./output/%stest.csv'%(mystrategy['strategy'].__name__),index=False)

    #绩效评测
    pyfoliozer = thestrat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
    returns=returns[start_date:]
    table.add_row([mystrategy['strategy'].__name__,
                    '{:.2%}'.format(empyrical.cum_returns_final(returns=returns)),
                    '{:.2%}'.format(empyrical.annual_return(returns=returns,annualization=daysinayear)),
                    '{:.2f}'.format(empyrical.sharpe_ratio(returns=returns,annualization=daysinayear)),
                    '{:.2%}'.format(empyrical.max_drawdown(returns=returns)),
                    '{:.2%}'.format(empyrical.annual_volatility(returns=returns,annualization=daysinayear))])


    returns.to_csv('output/strategy_rets.csv')
        
    print(table)

 
    