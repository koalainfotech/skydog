#比较不同的strategy的表现

import backtrader as bt
from backtrader import strategy
from empyrical.stats import cum_returns
from numpy.lib.function_base import append
import strategies.kingStrategies as st
import datetime as dt
import yfinance as yf
import pyfolio as pf
import empyrical
import prettytable
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

class mypandadata(bt.feeds.PandasData):
        lines=('valuation_ratio','valuation_thredhold',)
        params=(('valuation_ratio',-1),
                ('valuation_thredhold',-1),
            
        )


def compare_strategy(strategy_list,ticker_list,start_date,end_date,daysinayear=250,plotchart=False,valuationtype=None):
    allreturns=[]

    for ticker in ticker_list:
        #准备回测数据
        sourcedata=yf.download(ticker,start_date,end_date,auto_adjust=True)
        buyandholdreturn=(sourcedata.Close/sourcedata.Close.shift(1)-1)
        allreturns.append({'ticker':ticker,'strategy':'BuyandHold','returns':buyandholdreturn})
        if valuationtype is not None:
            valuations=pd.read_csv('data/valuations.csv')
            valuations=valuations[valuations['ticker']==ticker]
            valuations['date']=pd.to_datetime(valuations.date)
            valuations=valuations.set_index(['date'])[valuationtype]
            valuations.name='valuation_ratio'
            valuations=valuations.sort_index()
            sourcedata=sourcedata.join(valuations)
            sourcedata=sourcedata.fillna(method='pad')
            valuationthredhold=sourcedata['valuation_ratio'].rolling(window=250).quantile(0.9)
            valuationthredhold.name='valuation_thredhold'
            sourcedata=sourcedata.join(valuationthredhold)

        for strategy in strategy_list:
            print('Testing Startegy: %s, Ticker:%s '%(strategy['name'],ticker))
            cerebro=bt.Cerebro()   
            data=mypandadata(dataname=sourcedata,plot=True)
            cerebro.adddata(data)
            
            # Analyzers
            cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer,_name='mytrades')
            # broker设置资金、手续费
            cerebro.broker.setcash(1000000.0)    
            cerebro.broker.setcommission(commission=0.002,leverage=10)
            #添加策略
            cerebro.addstrategy(strategy['strategy'],**strategy['para'],trade_start_date=start_date)

            print('Starting Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(),cerebro.broker.getcash()))  
            thestrats=cerebro.run() #参数stdstats控制是否显添加默认的observer
            thestrat = thestrats[0]
            print('End Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(),cerebro.broker.getcash())) 
            pyfoliozer = thestrat.analyzers.getbyname('pyfolio')
            returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
            
            allreturns.append({'ticker':ticker,'strategy':strategy['name'],'returns':returns[start_date+dt.timedelta(days=strategy['para']['slow_days']):]})
        
    table=prettytable.PrettyTable(['Ticker','Strategy','Start Date','Total Return','Annual Return','Sharpe Ratio','Max Drawdown','Volatility'])
    df=pd.DataFrame(columns=['Ticker','Strategy','Start Date','Total Return','Annual Return','Sharpe Ratio','Max Drawdown','Volatility'])
    for item in allreturns:
        table.add_row([item['ticker'],
                        item['strategy'],
                        start_date,
                        empyrical.cum_returns_final(returns=item['returns']),
                        empyrical.annual_return(returns=item['returns'],annualization=daysinayear),
                        empyrical.sharpe_ratio(returns=item['returns'],annualization=daysinayear),
                        empyrical.max_drawdown(returns=item['returns']),
                        empyrical.annual_volatility(returns=item['returns'],annualization=daysinayear)])
      
        df=df.append({'Ticker':item['ticker'],
                      'Strategy': item['strategy'],
                      'Start Date':start_date,
                        'Total Return':empyrical.cum_returns_final(returns=item['returns']),
                        'Annual Return':empyrical.annual_return(returns=item['returns'],annualization=daysinayear),
                        'Sharpe Ratio':empyrical.sharpe_ratio(returns=item['returns'],annualization=daysinayear),
                        'Max Drawdown':empyrical.max_drawdown(returns=item['returns']),
                        'Volatility':empyrical.annual_volatility(returns=item['returns'],annualization=daysinayear)}
                         ,ignore_index=True)
        
            
    #print(table)
    
    if plotchart:
        for item in allreturns:
            returns=item['returns']
            ((returns+1).cumprod()-1).plot(label='%s-%s'%(item['ticker'],item['strategy']))
        plt.legend()
        plt.show()
    
    return df



if __name__ == '__main__':
    testname='PortStrategyTest'
    results=pd.DataFrame()
    ticker_list=['KWEB']
    valuationtype='pbttm'
    fast_days_range=[10]  
    slow_days_range=[30] 
    trailpercent_range=[0.15]
    signalexit_range=[False]
    buyatstart_range=[True]
    valuationcheck_range=[True,False]
    strategy_list=[]
    for fast_days in fast_days_range:
        for slow_days in slow_days_range:
            for trailpercent in trailpercent_range:
                for signalexit in signalexit_range:
                    for buyatstart in buyatstart_range:
                        for valuationcheck in valuationcheck_range:
                            if fast_days<slow_days:
                                strategy_list.append({'name':'SMA_Fast%.0f_Slow%.0f_TrailStop%.2f_SiganlExit:%s_BuyatStart:%s_ValuationCheck:%s'
                                    %(fast_days,slow_days,trailpercent,signalexit,buyatstart,valuationcheck),
                                'strategy':st.SmaCross,
                                'para':{'fast_days':fast_days,'slow_days':slow_days,'trailpercent':trailpercent,'signalexit':signalexit,'buyatstart':buyatstart,'valuationcheck':valuationcheck}})
                
    # strategy_list=[ {'name':'SMA1','strategy':st.SmaCross,'para':{'fast_days':5,'slow_days':20,'trailpercent':0}},          
    #                 {'name':'SMA2','strategy':st.SmaCross,'para':{'fast_days':5,'slow_days':20,'trailpercent':0.05}},    
    #                 {'name':'SMA3','strategy':st.SmaCross,'para':{'fast_days':5,'slow_days':20,'trailpercent':0.1}},  
    #                 {'name':'SMA4','strategy':st.SmaCross,'para':{'fast_days':5,'slow_days':20,'trailpercent':0.15}},      
    #             ]

    # strategy_list=[{'name':'Turtle20-10-14-0.01','strategy':st.TurtleLong,'para':{'risk':0.01}},
    #                {'name':'Turtle20-10-14-0.01','strategy':st.TurtleLong,'para':{'risk':0.015}},
    #                {'name':'Turtle20-10-14-0.02','strategy':st.TurtleLong,'para':{'risk':0.02}},
    
    
    # ]


    for year in range(2015,2020):
        for month in [1,4,7,10]:
            start_date=dt.date(year,month,1)
            end_date=start_date+dt.timedelta(days=365*2)
            print('from %s to %s'%(start_date,end_date))
            daysinayer=250
            result=compare_strategy(strategy_list,ticker_list,start_date,end_date,daysinayer,valuationtype=valuationtype)
            results=results.append(result)
    
    results.to_csv('output/comparestrategy_%s.csv'%(testname))
    
  

