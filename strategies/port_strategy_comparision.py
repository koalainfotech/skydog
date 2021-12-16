import datetime as dt
from backtrader import strategy
from backtrader.analyzers import leverage
import strategies.kingStrategies as st
import backtrader as bt
import yfinance as yf
import pandas as pd
import prettytable as pt
import empyrical


def compare_strategy(strategy_list,port,start_date,end_date,daysinayear=250):
    print('Start:%s, End:%s'%(start_date,end_date))
    allreturns=[]
    totalvalue=1000000
   
    for strategy in strategy_list:
        print('Testing %s...'%(strategy['name']))   
        
        cerebro = bt.Cerebro()

        for ticker,allocation in port.items():
            if 'slow_days' in strategy['args']:
                data=bt.feeds.PandasData(dataname=yf.download(ticker, start_date-dt.timedelta(days=int(strategy['args']['slow_days']/5*7)), end_date, auto_adjust=True),plot=False)
            else:
                data=bt.feeds.PandasData(dataname=yf.download(ticker, start_date, end_date, auto_adjust=True),plot=False)
            data.allocation=allocation
            cerebro.adddata(data,name=ticker)
        
        # Analyzer
        cerebro.addanalyzer(bt.analyzers.PyFolio,_name='pyfolio')

        # 加入策略    
        strats = cerebro.addstrategy(strategy['strategy'],**strategy['args'],trade_start_date=start_date)
        
        # broker设置资金、手续费    
        cerebro.broker.setcash(totalvalue)    
        cerebro.broker.setcommission(commission=0.001,leverage=10)
        cerebro.broker.set_checksubmit(False)
        
        
        # 启动回测   
        print('Start Portfolio Value: %.2f' % cerebro.broker.getvalue()) 
        thestrats=cerebro.run(stdstats=False) #参数stdstats控制是否显添加默认的observer
        thestrat = thestrats[0] 
        print('End Portfolio Value: %.2f' % cerebro.broker.getvalue()) 

        #绩效评测
        pyfoliozer = thestrat.analyzers.getbyname('pyfolio')
        returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
        allreturns.append({'strategy':strategy['name'],'returns':returns})
        
    table=pt.PrettyTable(['Strategy','Start Date','Total Return','Annual Return','Sharpe Ratio','Max Drawdown','Volatility'])
    df=pd.DataFrame(columns=['Strategy','Start Date','Total Return','Annual Return','Sharpe Ratio','Max Drawdown','Volatility'])
    
    for item in allreturns:
        table.add_row([item['strategy'],
                       start_date,
                        '{:.2%}'.format(empyrical.cum_returns_final(returns=item['returns'])),
                        '{:.2%}'.format(empyrical.annual_return(returns=item['returns'],annualization=daysinayear)),
                        '{:.2f}'.format(empyrical.sharpe_ratio(returns=item['returns'],annualization=daysinayear)),
                        '{:.2%}'.format(empyrical.max_drawdown(returns=item['returns'])),
                        '{:.2%}'.format(empyrical.annual_volatility(returns=item['returns'],annualization=daysinayear))])
        
        df=df.append({'Strategy': item['strategy'],
                      'Start Date':start_date,
                        'Total Return':empyrical.cum_returns_final(returns=item['returns']),
                        'Annual Return':empyrical.annual_return(returns=item['returns'],annualization=daysinayear),
                        'Sharpe Ratio':empyrical.sharpe_ratio(returns=item['returns'],annualization=daysinayear),
                        'Max Drawdown':empyrical.max_drawdown(returns=item['returns']),
                        'Volatility':empyrical.annual_volatility(returns=item['returns'],annualization=daysinayear)}
                         ,ignore_index=True)
    print(table)
    return df


if __name__ == '__main__':

    testname='PortStrategy'
    port={
          'BIDU':0.3,
          '1810.HK':0.4,
          '0175.HK':0.3,
   
        
    }

    strategy_list=[
        {'name':'PortSMA',
         'strategy':st.PortSmaCross,
         'args':{'trailpercent':0.12,
                 'signalexit':False,
                 'fast_days':20,
                 'slow_days':60,
                 
                }
    
        },

        {'name':'Buy and Hold',
         'strategy':st.PortBuyAndRebalance1,
         'args':{}
        },
        
        
    ]
    results=pd.DataFrame()
    for year in range(2019,2020):
        for month in range(1,13):
            start_date=dt.date(year,month,1)
            end_date=start_date+dt.timedelta(days=365*3)
            daysinayer=250
            result=compare_strategy(strategy_list,port,start_date,end_date,daysinayer)
            results=results.append(result)
    
    results.to_csv('output/comparestrategy_%s.csv'%(testname))




    
    
    
    
