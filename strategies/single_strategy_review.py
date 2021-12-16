# all imports and setups here
from backtrader.observers import benchmark
import yfinance as yf
import pandas as pd
import numpy as np
#import pyfolio as pf
import backtrader as bt
import prettytable
import empyrical
#import matplotlib.pyplot as plt
from IPython.core.debugger import set_trace
import strategies.kingStrategies as st
import datetime
import warnings
warnings.filterwarnings('ignore')




class mypandadata(bt.feeds.PandasData):
        lines=('valuation_ratio','valuation_thredhold',)
        params=(('valuation_ratio',-1),
                ('valuation_thredhold',-1),
            
        )

#参数
ticker='QQQ'
valuationtype='pettm'
daysinayear=250
start_date=datetime.date(2000,1,1)
end_date=datetime.date.today()

# mystrategy={'name':'SMACrossLong','strategy':st.SmaCrossLongShort,
#         'args':{'tradeatstart':True,
#                 'fast_days':5,
#                 'slow_days':200,
#                 'trailpercent':0,
#                 'signalexit':True,
#                 'dolong':True,
#                 'doshort':False,
#                 'start_date':start_date,
            
        
#         }                           
#         }

mystrategy={'name':'PriceAboveSMA','strategy':st.PriceAboveSMA,
        'args':{'sma_days':200,
                'offset':0.01
            
        
        }                           
        }
# mystrategy={'name':'TurtleLong','strategy':st.Turtle,
#            'args':{'doshort':True,
#                    'atrperiod':14,
#                    'highperiod':50,
#                    'lowperiod':50,
#                    'risk':0.01,
#                    'start_date':start_date
           
           
#            }


# }







#获取数据
sourcedata=yf.download(ticker,start_date-datetime.timedelta(days=365),end_date,auto_adjust=True)
benchmarkdata=sourcedata[start_date:]
buyandhold_returns=benchmarkdata.Close/benchmarkdata.Close.shift(1)-1
if valuationtype is not None:
        valuations=pd.read_csv('data/valuations.csv')
        valuations=valuations[valuations['ticker']==ticker]
        valuations['date']=pd.to_datetime(valuations.date)
        valuations=valuations.set_index(['date'])[valuationtype]
        valuations.name='valuation_ratio'
        valuations=valuations.sort_index()
        sourcedata=sourcedata.join(valuations)
        sourcedata=sourcedata.fillna(method='pad')
        valuationthredhold=sourcedata['valuation_ratio'].rolling(window=daysinayear).quantile(0.9)
        valuationthredhold.name='valuation_thredhold'
        sourcedata=sourcedata.join(valuationthredhold)

  
        


#pf.show_perf_stats(buyandhold_returns)

#策略回测


cerebro = bt.Cerebro()
feeddata=mypandadata(dataname=sourcedata)
cerebro.adddata(feeddata)
cerebro.broker.setcash(1000000.0)
cerebro.broker.setcommission(commission=0.002,leverage=10)
cerebro.broker.set_checksubmit(False)
cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
cerebro.addobserver(bt.observers.Benchmark,data=feeddata,timeframe=bt.TimeFrame.Years)
cerebro.addobserver(bt.observers.Benchmark,data=feeddata,timeframe=bt.TimeFrame.NoTimeFrame)


strats = cerebro.addstrategy(mystrategy['strategy'],**mystrategy['args'])
print('Starting Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(),cerebro.broker.getcash()))
thestrats=cerebro.run() #参数stdstats控制是否显添加默认的observer
print('End Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(),cerebro.broker.getcash()))
thestrat = thestrats[0] 
pyfoliozer = thestrat.analyzers.getbyname('pyfolio')
returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
table=prettytable.PrettyTable(['Strategy','Total Return','Annual Return','Sharpe Ratio','Max Drawdown','Volatility'])
table.add_row(['Buy and Hold',
                '{:.2%}'.format(empyrical.cum_returns_final(returns=buyandhold_returns)),
                '{:.2%}'.format(empyrical.annual_return(returns=buyandhold_returns,annualization=daysinayear)),
                '{:.2f}'.format(empyrical.sharpe_ratio(returns=buyandhold_returns,annualization=daysinayear)),
                '{:.2%}'.format(empyrical.max_drawdown(returns=buyandhold_returns)),
                '{:.2%}'.format(empyrical.annual_volatility(returns=buyandhold_returns,annualization=daysinayear))])
table.add_row(['Strategy',
                '{:.2%}'.format(empyrical.cum_returns_final(returns=returns)),
                '{:.2%}'.format(empyrical.annual_return(returns=returns,annualization=daysinayear)),
                '{:.2f}'.format(empyrical.sharpe_ratio(returns=returns,annualization=daysinayear)),
                '{:.2%}'.format(empyrical.max_drawdown(returns=returns)),
                '{:.2%}'.format(empyrical.annual_volatility(returns=returns,annualization=daysinayear))])
print(table)

cerebro.plot()