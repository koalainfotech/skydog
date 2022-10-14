import backtrader as bt
import datetime
from backtrader.order import BuyOrder
import pandas as pd
from backtrader import position
from backtrader import cerebro
from backtrader.utils.autodict import DotDict
from numpy.core.fromnumeric import size
from pandas.core.resample import f

class LongOnlySizer(bt.Sizer): #long default sizer
    params = (('stake', 1),

    )    
    def _getsizing(self, comminfo, cash, data, isbuy):        
        if isbuy:          
            return self.p.stake        
        position = self.broker.getposition(data)        
        if not position.size:            
            return 0        
        else:            
            return position.size        
        return self.p.stakeclass 
class AllinLongOnly(bt.Sizer): # 全仓做多Sizer
    params = (
            ('buffer',0.05),
             )

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            newsstake=int(cash*(1-self.p.buffer)/data.close)
            return newsstake
        else:
            position = self.broker.getposition(data)
            if not position.size:
                return 0  # do not sell if nothing is open
            else:
                return abs(position.size)

   
class PortBuyAndHold(bt.Strategy):#买入并持有
    params = ( ('printlog', False), )   

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:            
            dt = dt or self.datas[0].datetime.date(0)           
            print('%s, %s' % (dt.isoformat(), txt))    

    def __init__(self):
        pass
    
    def notify_order(self, order):        
        if order.status in [order.Submitted, order.Accepted]:            
            return

        if order.status in [order.Completed]:            
            if order.isbuy():               
                self.log('BUY EXECUTED, %s, Price: %.2f, Cost: %.2f, Comm %.2f' %                   
                (order.data._name,
                order.executed.price,
                order.executed.value,
                order.executed.comm)
                ,doprint=True)              
           
            else:             
                self.log('SELL EXECUTED, %s, Price: %.2f, Cost: %.2f, Comm %.2f' %                   
                (order.data._name,
                order.executed.price,
                order.executed.value,
                order.executed.comm)
                ,doprint=True)  

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:           
            self.log('Order Canceled/Margin/Rejected')        
        self.order = None 
    
    def next(self):
        total_value=self.broker.getvalue() #获取当前组合净资产

        #对组合的每一支股票进行操作：如果没有仓位，就按配置比例买入
        for d in self.datas[:-1]:

            #获取仓位
            pos=self.getposition(d).size
            if pos==0:
                stake=int((total_value*d.allocation/d.close[0])/100)*100
                self.buy(data=d,size=stake)

class PortBuyAndRebalance1(bt.Strategy): #按配置偏移程度再平衡
    params = ( 
        ('printlog', False),
        ('threshold', 0.1),
        ('buffer',0.05),
        ('start_date',datetime.date(2000,1,1)),
        )   

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:            
            dt = dt or self.datas[0].datetime.date(0)           
            print('%s, %s' % (dt.isoformat(), txt))    

    def __init__(self):
        print('Initializating Strategy...')
        self.predate=dict()
        for d in self.datas:
            self.predate[d]=None
    
    def notify_order(self, order):        
        if order.status in [order.Submitted, order.Accepted]:            
            return

        if order.status in [order.Completed]:            
            if order.isbuy():               
                self.log('BUY EXECUTED, %s, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f' %                   
                (order.data._name,
                order.executed.price,
                order.executed.size,
                order.executed.value,
                order.executed.comm)
                ,doprint=True)              
           
            else:             
                self.log('SELL EXECUTED, %s, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f' %                   
                (order.data._name,
                order.executed.price,
                order.executed.size,
                order.executed.value,
                order.executed.comm)
                ,doprint=True)  
                           
        elif order.status in [order.Canceled, order.Rejected]:           
            self.log('Order Canceled/Margin/Rejected',doprint=True)   
        elif order.status== order.Margin:
            self.log('Order Margin',doprint=True) 
        self.order = None 
    
    def next(self):
        if bt.num2date(self.datas[0].datetime[0]).date()<self.p.start_date:
            return

        total_value = self.broker.get_value() 
        self.log('Portfolio Value: %.2f, Cash Balance: %.2f' %(total_value,self.broker.get_cash()),doprint=False)
        trade_plan=dict()
        
        
        for d in self.datas:
            if d.datetime[0]==self.predate[d]:
                return
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
            
            self.predate[d]=d.datetime[0]
        

        for d,value in trade_plan.items():
            if value['unit']<0:
                self.sell(data=d,size=value['unit'])
            elif value['unit']>0:
                self.buy(data=d,size=value['unit'])

class RunHistoryOrder(bt.Strategy):
    params = ( 
        ('printlog', False),
  
        ) 
    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:            
            dt = dt or self.datas[0].datetime.date(0)           
            print('%s, %s' % (dt.isoformat(), txt))    

    def __init__(self):
        pass
    
    def notify_order(self, order):        
        if order.status in [order.Submitted, order.Accepted]:            
            return

        if order.status in [order.Completed]:            
            if order.isbuy():               
                self.log('BUY EXECUTED, %s, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f' %                   
                (order.data._name,
                order.executed.price,
                order.executed.size,
                order.executed.value,
                order.executed.comm)
                ,doprint=True)              
           
            else:             
                self.log('SELL EXECUTED, %s, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f' %                   
                (order.data._name,
                order.executed.price,
                order.executed.size,
                order.executed.value,
                order.executed.comm)
                ,doprint=True)  
                           
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:           
            self.log('Order Canceled/Margin/Rejected',doprint=True)        
        self.order = None 
    
    def next(self):
        pass
   

class SmaCross(bt.Strategy): #简单均线交叉
    # list of parameters which are configurable for the strategy
    params = dict(
        printlog=False, #控制全局是否输出Log
        fast_days=20,  # period for the fast moving average
        slow_days=60,   # period for the slow moving average
        buffer=0.05, # 现金buffer，避免超买
        trailpercent=0, #追踪止损比例
        signalexit=False, #均线死叉是否退出
        buyatstart=False, # 策略启动时以过了金叉点是否买入
        valuationcheck=False, #估值判断指标
        offset=0, # 穿越buffer
       
    )

 

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:            
            dt = dt or self.datas[0].datetime.date(0)           
            print('%s, %s' % (dt.isoformat(), txt)) 
    
    def notify_order(self, order):
        self.log('order type:%s,status:%s,price:%.2f,size:%.2f'%
                (order.ExecTypes[order.exectype],order.Status[order.status],order.created.price,order.created.size)
                ,doprint=False)

        if order.status in [order.Submitted]:
            return
        
        if order.status in [order.Accepted]:
            self.log('Placed an %s order, size:%.2f, price:%.2f'%
            (order.ExecTypes[order.exectype],order.created.size,order.created.price),doprint=False)  
               

        if order.status in [order.Completed]:            
            if order.isbuy():               
                self.log(                    
                'BUY EXECUTED, Type:%s, Price: %.2f, Quantity: %.2f, Cost: %.2f, Comm: %.2f' %                   
                (order.ExecTypes[order.exectype],
                order.executed.price,
                order.executed.size,
                order.executed.value,
                order.executed.comm),doprint=False)              
                self.buyprice = order.executed.price              
                self.buycomm = order.executed.comm
                #trailpercent=st.trailpercentopt()
                if self.p.trailpercent>0:
                    self.stoptrailorder=self.sell(exectype=bt.Order.StopTrail,size=order.executed.size,
                                            trailpercent=self.p.trailpercent,oco=self.sellorder)
                self.buyorder=None
                              
                         
            else:             
                self.log('SELL EXECUTED, Type:%s, Price: %.2f, Quantity: %.2f, Cost: %.2f, Comm: %.2f' %                        
                     (order.ExecTypes[order.exectype],
                     order.executed.price,
                     order.executed.size,
                     order.executed.value,
                     order.executed.comm,
                   ),doprint=False)
               
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:           
            self.log('Order Canceled/Margin/Rejected',doprint=False) 

    def __init__(self):

        self.setsizer(AllinLongOnly())
        self.fast_sma = bt.ind.SMA(period=self.p.fast_days)  # fast moving average
        self.slow_sma = bt.ind.SMA(period=self.p.slow_days)  # slow moving average
        self.sma_crossover = bt.ind.CrossOver(self.fast_sma, self.slow_sma*(1+self.p.offset))  # crossover signal
        self.trade_signal=self.sma_crossover
        self.buyprice=0
        self.stopprice=0
        self.sellorder=None
        self.buyorder=None
        self.stoptrailorder=None
        self.counter=0

    

    def next(self):
        self.log('Position:%.2f,Close Price:%.2f,Cross:%.0f'
                %(self.position.size,self.datas[0].close[0],self.sma_crossover[0]),
                doprint=True)
        if self.counter==0 and self.p.buyatstart and self.fast_sma>self.slow_sma:
            self.buyorder=self.buy()
        
        if self.trade_signal > 0 and self.position.size<=0:
            if self.p.valuationcheck and self.data.valuation_thredhold[0]>0: #and pd.isna(self.data.valuation_thredhold[0]) is False:
                if self.data.valuation_ratio<self.data.valuation_thredhold:
                    self.buyorder=self.buy()
                else:
                    self.log('Buy stopped by valuation check:%.2f-%.2f'%(self.data.valuation_ratio[0],self.data.valuation_thredhold[0]),doprint=True)
            else:
                self.buyorder=self.buy()
           
        elif self.trade_signal<0 and self.p.signalexit:
            self.sellorder=self.sell(oco=self.stoptrailorder)
        
        self.counter=self.counter+1


class Turtle(bt.Strategy): # 海龟通道突破做多
    params = (('printlog', False), 
             ('atrperiod', 14),  
             ('highperiod', 20), 
             ('lowperiod', 10), 
             ('risk', 0.01),
             ('buffer',0.05),
             ('doshort',False),
             ('start_date',datetime.date(2000,1,1))

            
            )   
    
    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:            
            dt = dt or self.datas[0].datetime.date(0)           
            print('%s,Total Value:%.2f, Position:%i, Close: %.2f,  %s' 
            % (dt.isoformat(), 
            self.broker.getvalue(),
            self.position.size,
            self.data.close[0],
            txt))    

    def __init__(self):  
        self.setsizer(LongOnlySizer())   
        self.dataclose = self.datas[0].close      
        self.datahigh = self.datas[0].high        
        self.datalow = self.datas[0].low     
        self.order = None      
        self.tradeprice = 0      
        self.tradecomm = 0      
        self.newstake = 0      
        self.tradetime = 0   
        self.direction=''   

        # 参数计算，唐奇安通道上轨、唐奇安通道下轨、ATR        
        self.DonchianHi = bt.indicators.Highest(self.datahigh(-1), period=self.p.highperiod, subplot=False)        
        self.DonchianLo = bt.indicators.Lowest(self.datalow(-1), period=self.p.lowperiod, subplot=False)       
        self.TR = bt.indicators.Max((self.datahigh(0)- self.datalow(0)), abs(self.dataclose(-1) -   self.datahigh(0)), abs(self.dataclose(-1)  - self.datalow(0) ))        
        self.ATR = bt.indicators.SimpleMovingAverage(self.TR, period=self.p.atrperiod, subplot=True)       
        # 唐奇安通道上轨突破、唐奇安通道下轨突破       
        self.CrossoverHi = bt.ind.CrossOver(self.dataclose(0), self.DonchianHi)        
        self.CrossoverLo = bt.ind.CrossOver(self.dataclose(0), self.DonchianLo)    
    
    def notify_order(self, order):        
        if order.status in [order.Submitted, order.Accepted]:            
            return

        if order.status in [order.Completed]:            
            if order.isbuy():               
                self.log('BUY EXECUTED, Quantity: %i, Price: %.2f, Cost: %.2f' %                   
                        (order.executed.size,
                        order.executed.price,
                        order.executed.value,
                        ),doprint=True)              
                                
            else:             
                self.log('SELL EXECUTED, Quantity: %i, Price: %.2f, Cost: %.2f' %                        
                        (order.executed.size,
                        order.executed.price,
                        order.executed.value,
                        ),doprint=True)                             
                   
            self.tradeprice = order.executed.price              
            self.tradecomm = order.executed.comm     
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:           
            self.log('Order Canceled/Margin/Rejected',doprint=True)        
        self.order = None    

    def notify_trade(self, trade):      
        if not trade.isclosed:
            return        
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm)) 

    def next(self): 
        if bt.num2date(self.datas[0].datetime[0]).date()<self.p.start_date:
            return
        if self.order:
            return        
        #入场, 做多        
        if self.CrossoverHi > 0 and self.tradetime == 0: 
            self.log('Do long...',doprint=True)                                
            self.newstake = self.broker.getvalue() * (1-self.p.buffer)*self.p.risk / self.ATR            
            self.newstake = int(self.newstake / 100) * 100                             
            self.tradetime = 1            
            self.order = self.buy(size=self.newstake)
            self.direction='long' 
        #入场，做空
        elif self.CrossoverLo<0 and self.tradetime==0 and self.p.doshort==True:
            self.log('Do short...',doprint=True)
            self.newstake = self.broker.getvalue() * (1-self.p.buffer)*self.p.risk / self.ATR            
            self.newstake = int(self.newstake / 100) * 100                             
            self.tradetime = 1            
            self.order = self.sell(size=self.newstake)
            self.direction='short'         
        
        #多头，加仓        
        elif self.direction=='long' and self.datas[0].close >self.tradeprice+0.5*self.ATR[0] and self.tradetime > 0 and self.tradetime < 5:           
            self.log('Add long position...',doprint=True)
            self.newstake = self.broker.getvalue() *(1-self.p.buffer)* self.p.risk / self.ATR            
            self.newstake = int(self.newstake / 100) * 100               
            self.order = self.buy(size=self.newstake)           
            self.tradetime = self.tradetime + 1      
       
        #空头，加仓
        elif self.direction=='short' and self.datas[0].close <self.tradeprice-0.5*self.ATR[0] and self.tradetime > 0 and self.tradetime < 5:           
            self.log('Add short position...',doprint=True)
            self.newstake = self.broker.getvalue() *(1-self.p.buffer)* self.p.risk / self.ATR            
            self.newstake = int(self.newstake / 100) * 100               
            self.order = self.sell(size=self.newstake)           
            self.tradetime = self.tradetime + 1   
        
        
        #多头，出场        
        elif self.direction=='long' and self.CrossoverLo < 0 and self.tradetime > 0:
            self.log('Closing long position...',doprint=True)            
            self.order = self.close()            
            self.tradetime = 0 
            self.direction=''    
        
        #空头，出场        
        elif self.direction=='short' and self.CrossoverLo > 0 and self.tradetime > 0:   
            self.log('Closing short position...',doprint=True)         
            self.order = self.close()            
            self.tradetime = 0  
            self.direction=''  
        
        #多头，止损        
        elif self.direction=='long' and self.datas[0].close < (self.tradeprice - 4*self.ATR[0]) and self.tradetime > 0:           
            self.log('Stop loss for long position',doprint=True)
            self.order = self.close()
            self.tradetime = 0 
            self.direction=''  
        
        #多头，止损        
        elif self.direction=='short' and self.datas[0].close > (self.tradeprice + 4*self.ATR[0]) and self.tradetime > 0:           
            self.log('Stop loss for short position',doprint=True)
            self.order = self.close()
            self.tradetime = 0 
            self.direction=''
    
    def stop(self):        
        self.log('(MA Period %2d) Ending Value %.2f' % (self.params.atrperiod, self.broker.getvalue()), doprint=True)


            
class PortSmaCross(bt.Strategy): #简单均线交叉
    # list of parameters which are configurable for the strategy
    params = dict(
        printlog=False, #控制全局是否输出Log
        fast_days=20,  # period for the fast moving average
        slow_days=60,   # period for the slow moving average
        buffer=0.05,
        trailpercent=0, #追踪止损比例
        signalexit=True,
        buyatstart=True,
        start_date=datetime.date(2000,1,1)
       
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
         
                
                if self.p.trailpercent>0:
                    self.stoptrailorder[ticker]=self.sell(data=order.data,exectype=bt.Order.StopTrail,size=order.executed.size,
                                            trailpercent=self.p.trailpercent,oco=self.sellorder[ticker])
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
    

    def next(self):
        if bt.num2date(self.datas[0].datetime[0]).date()<self.p.start_date:
            return

        for i in range(0,self.numberoftickers):
            if self.datas[i].datetime[0]==self.predate[i]:
                return
            ticker=self.datas[i]._name
            if ticker=='Benchmark':
                return
            
            self.log('Ticker:%s, Position:%.2f,Close Price:%.2f,Cross:%.0f'
                    %(ticker,self.getposition(self.datas[i]).size,self.datas[i].close[0],self.sma_crossover[i][0]),
                    doprint=False)
            if self.counter[i]==0 and self.p.buyatstart and self.fast_sma[i]>self.slow_sma[i]:
                size=int(self.broker.getvalue()*(1-self.p.buffer)*self.datas[i].allocation/self.datas[i].close[0])
                self.buyorder[ticker]=self.buy(data=self.datas[i],size=size)
            
            if self.trade_signal[i] > 0 and self.getposition(self.datas[i]).size<=0: 
                size=int(self.broker.getvalue()*(1-self.p.buffer)*self.datas[i].allocation/self.datas[i].close[0])
                self.buyorder[ticker]=self.buy(data=self.datas[i],size=size)
            
            elif self.trade_signal[i]<0 and self.p.signalexit:
                size=self.getposition(self.datas[i]).size
                if self.p.trailpercent>0:
                    self.sellorder[ticker]=self.sell(data=self.datas[i],size=size,oco=self.stoptrailorder[ticker])
                else:
                    self.sellorder[ticker]=self.sell(data=self.datas[i],size=size)
            
            self.counter[i]=self.counter[i]+1
            self.predate[i]=self.datas[i].datetime[0]
        
        
class SmaCrossLongShort(bt.Strategy): #简单均线交叉
    # list of parameters which are configurable for the strategy
    params = dict(
        printlog=False, #控制全局是否输出Log
        fast_days=20,  # period for the fast moving average
        slow_days=60,   # period for the slow moving average
        buffer=0.05, # 现金buffer，避免超买
        trailpercent=0, #追踪止损比例
        signalexit=False, #反向信号是否退出
        tradeatstart=True, # 策略启动时以过了交叉点是否交易
        doshort=False, #是否做空
        dolong=True, #是否做多
        offset=0,
        start_date=datetime.date(2000,1,1)

       
    )

 

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:            
            dt = dt or self.datas[0].datetime.date(0)           
            print('%s, %s' % (dt.isoformat(), txt)) 
    
    def notify_order(self, order):
        self.log('order type:%s,status:%s,price:%.2f,size:%.2f'%
                (order.ExecTypes[order.exectype],order.Status[order.status],order.created.price,order.created.size)
                ,doprint=False)

        if order.status in [order.Submitted]:
            return
        
        if order.status in [order.Accepted]:
            self.log('Placed an %s order, size:%.2f, price:%.2f'%
            (order.ExecTypes[order.exectype],order.created.size,order.created.price),doprint=False)  
               

        if order.status in [order.Completed]: 
                      
            if order.isbuy():               
                self.log(                    
                'BUY EXECUTED, Type:%s, Price: %.2f, Quantity: %.2f, Cost: %.2f, Comm: %.2f' %                   
                (order.ExecTypes[order.exectype],
                order.executed.price,
                order.executed.size,
                order.executed.value,
                order.executed.comm),doprint=True)              
              
                if self.p.trailpercent>0 and order.exectype==0: 
                    self.longstoporder=self.sell(exectype=bt.Order.StopTrail,size=order.executed.size,
                                            trailpercent=self.p.trailpercent,oco=self.sellorder)
                    self.log('Stop order for long position placed',doprint=True)
                self.buyorder=None
                              
                         
            else:             
                self.log('SELL EXECUTED, Type:%s, Price: %.2f, Quantity: %.2f, Cost: %.2f, Comm: %.2f' %                        
                     (order.ExecTypes[order.exectype],
                     order.executed.price,
                     order.executed.size,
                     order.executed.value,
                     order.executed.comm,
                   ),doprint=True)
              
                if self.p.trailpercent>0 and order.exectype==0:
                    self.shortstoporder=self.buy(exectype=bt.Order.StopTrail,size=order.executed.size,
                                            trailpercent=self.p.trailpercent,oco=self.buyorder)
                    self.log('Stop order for short position placed',doprint=True)
                self.sellorder=None
               
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:           
            self.log('%s Order Canceled/Margin/Rejected'%order.ExecTypes[order.exectype],doprint=True) 

    def __init__(self):

        self.fast_sma = bt.ind.SMA(period=self.p.fast_days)  # fast moving average
        self.slow_sma = bt.ind.SMA(period=self.p.slow_days)  # slow moving average
        self.sma_crossover = bt.ind.CrossOver(self.fast_sma, self.slow_sma)  # crossover signal
        self.trade_signal=self.sma_crossover
        self.buyprice=0
        self.stopprice=0
        self.sellorder=None
        self.buyorder=None
        self.longstoporder=None
        self.shortstoporder=None
        self.firstday=True

    

    def next(self):
        if bt.num2date(self.datas[0].datetime[0]).date()<self.p.start_date:
            return

        
        self.log('Position:%.2f,Close Price:%.2f,Cross:%.0f'
                %(self.position.size,self.datas[0].close[0],self.sma_crossover[0]),
                doprint=False)
        
        if self.firstday==True and self.p.tradeatstart==True: # 策略启动时的交易
            if self.fast_sma>self.slow_sma and self.p.dolong==True:
                self.log('Fast SMA:%.2f, Slow SMA:%.2f. Initial Trade, Long.'
                        %(self.fast_sma[0],self.slow_sma[0])
                        ,doprint=True)
                tradesize=int(self.broker.get_value()*(1-self.p.buffer)/self.data0.close[0])
                self.buyorder=self.buy(size=tradesize)

            elif self.fast_sma<self.slow_sma and self.p.doshort==True:
                self.log('Fast SMA:%.2f, Slow SMA:%.2f. Initial Trade, Short.'
                        %(self.fast_sma[0],self.slow_sma[0])
                        ,doprint=True)
                tradesize=int(self.broker.get_value()*(1-self.p.buffer)/self.data0.close[0])
                self.sellorder=self.sell(size=tradesize)
        
        
        elif self.trade_signal >0: #做多信号
            #case1 position=0并且允许做多，买入
            #case2 position<0,不允许做多，平仓
            #case3 position<0, 允许做多，平仓，然后做多
            #其他情况不操作
            pos=self.position.size
            if pos==0 and self.p.dolong==True:
                self.log('Position:%i,Trade Signal:%i,Long'
                        %(pos,self.trade_signal[0])
                        ,doprint=True)
                tradesize=int(self.broker.get_value()*(1-self.p.buffer)/self.data0.close[0])
                self.buyorder=self.buy(size=tradesize,oco=self.shortstoporder)
            elif pos<0 and self.p.signalexit==True and self.p.dolong==False:
                self.log('Position:%i,Trade Signal:%i,Close position'
                        %(pos,self.trade_signal[0])
                        ,doprint=True)
                self.buyorder=self.buy(size=pos*-1,oco=self.shortstoporder)
            elif pos<0 and self.p.signalexit==True and self.p.dolong==True:
                self.log('Position:%i,Trade Signal:%i,Long'
                        %(pos,self.trade_signal[0])
                        ,doprint=True)
                tradesize=int(self.broker.get_value()*(1-self.p.buffer)/self.data0.close[0])+pos*-1
                self.buyorder=self.buy(size=tradesize,oco=self.shortstoporder)

             
        elif self.trade_signal<0: #做空信号
            #case1 position=0并且允许做空，卖出
            #case2 position>0,不允许做空，平仓
            #case3 position>0, 允许做空，平仓，然后卖出
            #其他情况不操作
            pos=self.position.size
            if pos==0 and self.p.doshort==True:
                self.log('Position:%i,Trade Signal:%i,Short'
                        %(pos,self.trade_signal[0])
                        ,doprint=True)
                tradesize=int(self.broker.get_value()*(1-self.p.buffer)/self.data0.close[0])
                self.sellorder=self.sell(size=tradesize,oco=self.longstoporder)
            elif pos>0 and self.p.signalexit==True and self.p.doshort==False:
                self.log('Position:%i,Trade Signal:%i,Close position'
                        %(pos,self.trade_signal[0])
                        ,doprint=True)
                self.sellorder=self.sell(size=pos,oco=self.longstoporder)
            elif pos>0 and self.p.signalexit==True and self.p.doshort==True:
                self.log('Position:%i,Trade Signal:%i,Short'
                        %(pos,self.trade_signal[0])
                        ,doprint=True)
                tradesize=int(self.broker.get_value()*(1-self.p.buffer)/self.data0.close[0])+pos
                self.sellorder=self.sell(size=tradesize,oco=self.longstoporder)
            
        
        self.firstday=False


class PriceAboveSMA(bt.Strategy): #价格在均线上方
    # list of parameters which are configurable for the strategy
    params = dict(
        printlog=False, #控制全局是否输出Log
        sma_days=20,  # period for the moving average
        slow_days=60,   # period for the slow moving average
        buffer=0.05, # 现金buffer，避免超买
        offset=0, # 价格偏离均线buffer
       
    )

 

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:            
            dt = dt or self.datas[0].datetime.date(0)           
            print('%s, %s' % (dt.isoformat(), txt)) 
    
    def notify_order(self, order):
        self.log('order type:%s,status:%s,price:%.2f,size:%.2f'%
                (order.ExecTypes[order.exectype],order.Status[order.status],order.created.price,order.created.size)
                ,doprint=False)

        if order.status in [order.Submitted]:
            return
        
        if order.status in [order.Accepted]:
            self.log('Placed an %s order, size:%.2f, price:%.2f'%
            (order.ExecTypes[order.exectype],order.created.size,order.created.price),doprint=False)  
               

        if order.status in [order.Completed]:            
            if order.isbuy():               
                self.log(                    
                'BUY EXECUTED, Type:%s, Price: %.2f, Quantity: %.2f, Cost: %.2f, Comm: %.2f' %                   
                (order.ExecTypes[order.exectype],
                order.executed.price,
                order.executed.size,
                order.executed.value,
                order.executed.comm),doprint=False)              
                self.buyprice = order.executed.price              
                self.buycomm = order.executed.comm
                self.buyorder=None
                              
                         
            else:             
                self.log('SELL EXECUTED, Type:%s, Price: %.2f, Quantity: %.2f, Cost: %.2f, Comm: %.2f' %                        
                     (order.ExecTypes[order.exectype],
                     order.executed.price,
                     order.executed.size,
                     order.executed.value,
                     order.executed.comm,
                   ),doprint=False)
               
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:           
            self.log('Order Canceled/Margin/Rejected',doprint=False) 

    def __init__(self):

        self.setsizer(AllinLongOnly())
        self.sma = bt.ind.SMA(period=self.p.sma_days)  # moving average
        self.buyprice=0
        self.sellorder=None
        self.buyorder=None

    

    def next(self):
        self.log('Position:%.2f, Close Price:%.2f, SMA:%.0f'
                %(self.position.size,self.datas[0].close[0],self.sma[0]),
                doprint=True)
        
        if self.datas[0].close >=self.sma*(1+self.p.offset) and self.position.size<=0:
            self.buyorder=self.buy()
                       
        elif self.datas[0]<self.sma*(1-self.p.offset) and self.position.size>0:
            self.sellorder=self.sell()
   