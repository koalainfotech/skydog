import datetime as dt
import pandas as pd
import yfinance as yf
import backtrader as bt

class PortTrailStopReblance(bt.Strategy):
    params = dict(
        printlog=False, #控制全局是否输出Log
        fast_days=20,  # period for the fast moving average
        slow_days=60,   # period for the slow moving average
        buffer=0.05,
        trailpercent=0, #追踪止损比例
        start_date=None,
        end_date=None,
    
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:            
            dt = dt or self.datas[0].datetime.date(0)           
            print('%s, %s' % (dt.isoformat(), txt)) 
    
    def notify_order(self, order):
        ticker=order.data._name
        self.log('Ticker: %s, order type:%s,status:%s,price:%.2f,size:%.2f'%
                (ticker,order.ExecTypes[order.exectype],order.Status[order.status],order.created.price,order.created.size)
                ,doprint=False)

        if order.status in [order.Submitted]:
            return
        
        if order.status in [order.Accepted]:
            self.log('Placed an %s order, ticker: %s, size:%.2f, price:%.2f'%
            (order.ExecTypes[order.exectype],ticker,order.created.size,order.created.price),doprint=False)  
               

        if order.status in [order.Completed]:            
            if order.isbuy():               
                self.log(                    
                'BUY EXECUTED, Ticker:%s, Type:%s, Price: %.2f, Quantity: %.2f, Cost: %.2f, Comm: %.2f' %                   
                (ticker,
                order.ExecTypes[order.exectype],
                order.executed.price,
                order.executed.size,
                order.executed.value,
                order.executed.comm),doprint=True)              
         
                
                if order.data.trailpercent>0:
                    self.stoptrailorder[ticker]=self.sell(data=order.data,exectype=bt.Order.StopTrail,size=order.executed.size,
                                            trailpercent=order.data.trailpercent,oco=self.sellorder[ticker])
                self.buyorder[ticker]=None
                              
                         
            else:             
                self.log('SELL EXECUTED, Ticker:%s, Type:%s, Price: %.2f, Quantity: %.2f, Cost: %.2f, Comm: %.2f' %                        
                     (ticker,
                    order.ExecTypes[order.exectype],
                     order.executed.price,
                     order.executed.size,
                     order.executed.value,
                     order.executed.comm,
                   ),doprint=True)
               
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:           
            self.log('Order Canceled/Margin/Rejected',doprint=True) 

    def __init__(self):
        self.numberoftickers=len(self.datas)
        self.fast_sma=[]
        self.slow_sma=[]
        self.sma_crossover=[]
        self.trade_signal=[]
        self.counter=[]
        self.buyorder={}
        self.sellorder={}
        self.stoptrailorder={}
        self.predate=dict()
        self.rebalance_date=pd.date_range(start_date,end_date,freq='1Q')
        self.first_call=True

        for i in range(0,self.numberoftickers):
            self.fast_sma.append(bt.ind.SMA(self.datas[i].close,period=self.p.fast_days))
            self.slow_sma.append(bt.ind.SMA(self.datas[i].close,period=self.p.slow_days))
            self.sma_crossover.append(bt.ind.CrossOver(self.fast_sma[i], self.slow_sma[i]))
            self.trade_signal.append(self.sma_crossover[i])
            self.counter.append(0)
            self.stoptrailorder[self.datas[i]._name]=None
            self.buyorder[self.datas[i]._name]=None
            self.sellorder[self.datas[i]._name]=None
            self.predate[i]=None
    
    def prenext(self): # indicator产生数据之前被调用
        pass


    def next(self): #indicator产生数据之后被调用
        if self.first_call==True: #策略启动的初始操作
            self.log('Strategy starting...',doprint=True)
        
            for i in range(0,self.numberoftickers):
                ticker=self.datas[i]._name
                allocation=self.datas[i].allocation
                trailpercent=self.datas[i].trailpercent
                budget=self.broker.getvalue()*(1-self.p.buffer)*allocation
                if trailpercent==0: #买入并持有
                    size=int(budget/self.datas[i].close[0])
                    self.buyorder[ticker]=self.buy(data=self.datas[i],size=size)
                elif trailpercent>0: #20日均线在60日均线上方买入
                    if self.fast_sma[i]>self.slow_sma[i]:
                        size=int(budget/self.data[i].close[0])
                        self.buyorder[ticker]=self.buy(data=self.datas[i],size=size)
                    else:
                        pass
            self.first_call=False
        
        else:
            #每一天，对于追踪止损的标的，判定是否是买入点
            for i in range(0,self.numberoftickers):
                if self.datas[i].datetime[0]==self.predate[i]:
                    return
                ticker=self.datas[i]._name
                budget=self.broker.getvalue()*(1-self.p.buffer)*self.datas[i].allocation
                if self.datas[i].trailpercent>0 and self.fast_sma[i]>self.slow_sma[i] and self.getposition(self.datas[i]).size<=0:
                    size=int(budget/self.data[i].close[0])
                    self.buyorder[ticker]=self.buy(data=self.datas[i],size=size)
            
            #在再平衡日对组合进行再平衡
            if self.datas[0].datetime[0] in self.rebalance_date:
                self.log('Rebalancing...',doprint=True)
                trade_plan=dict()
                total_value=self.broker.get_value()
                for d in self.datas:
                    trade_plan[d]=dict()
                    trade_plan[d]['unit']=0
                    value = self.broker.get_value(datas=[d])
                    actual_allocation = value / (total_value*(1-self.p.buffer))

                    self.log('Ticker: %s, Position: %.2f, Price: %.2f, Value: %.2f, Allocation: %.2f'
                        %(d._name,
                        self.getposition(d).size,
                        d.close[0],
                        value,
                        actual_allocation
                    ),
                    doprint=False 
                    )

                    if abs(actual_allocation/d.allocation-1)>self.p.threshold:
                        units_to_trade =int(((d.allocation - actual_allocation) * total_value*(1-self.p.buffer) / d.close[0])/100)*100
                        trade_plan[d]['unit']=units_to_trade
                        
                    




#参数
init_money=1000000
port={'QQQ':[0.5,0],
      'MCHI':[0.5,0.12]
}
start_date=dt.date(2015,12,31)
end_date=dt.date.today()



cerebro=bt.Cerebro()

for ticker,item in port.items():
    yfdata=yf.download(ticker,start_date-dt.timedelta(days=90),end_date)
    data=bt.feeds.PandasData(dataname=yfdata,plot=False)
    data.allocation=item[0]
    data.trailpercent=item[1]
    cerebro.adddata(data,name=ticker)

cerebro.broker.setcash(init_money)    
cerebro.broker.setcommission(commission=0.001)
cerebro.addstrategy(PortTrailStopReblance,start_date=start_date,end_date=end_date)

 # 启动回测   
print('Start Portfolio Value: %.2f' % cerebro.broker.getvalue()) 
thestrats=cerebro.run(stdstats=True) #参数stdstats控制是否显添加默认的observer
thestrat = thestrats[0] 
print('End Portfolio Value: %.2f' % cerebro.broker.getvalue()) 
    





