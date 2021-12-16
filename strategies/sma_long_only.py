import datetime
from matplotlib.pyplot import plot, subplot, title
import pandas
import yfinance as yf
import backtrader as bt
import os
import sys
class GenericCSV_PE(bt.feeds.GenericCSVData):
    lines = ('pe',)
    params = (('pe', 6),)
class PandasData_Fundamentals(bt.feeds.PandasData):
    lines = ('pe_ttm','pe_ftm','val_pe_deducted_ttm','profit_ttm','gr_ttm',)
    params = (
            ('pe_ttm', -1),
            ('pe_ftm', -1),
            ('val_pe_deducted_ttm', -1),
            ('profit_ttm', -1),
            ('gr_ttm', -1),
        # ('val_pe_percentile',-1),
    )
    def __init__(self):
        super(PandasData_Fundamentals, self).__init__()
        for attr in ['pe_ttm','pe_ftm','val_pe_deducted_ttm','profit_ttm','gr_ttm']:
            self.datafields.append(attr)
        # self.datafields.append("pe_ttm")
class WaddahAttarExplosion(bt.Indicator):
    lines = ('macd', 'utrend', 'dtrend', 'dead', 'exp', )

    params = (
        ('sensitivity', 150),
        ('fast', 20),
        ('slow', 40),
        ('channel', 20),
        ('mult', 2.0),
        ('dead', 3.7)

    )

    plotlines = dict(macd=dict(_plotskip=True, ),
                     utrend=dict(_method='bar',),
                     dtrend=dict(_method='bar',)
                     )

    plotinfo = dict(
        plot=True,
        plotname='Waddah Attar Explosion',
        subplot=True,
        plotlinelabels=True)

    def __init__(self):
        # Plot horizontal Line

        self.l.macd = bt.indicators.MACD(
            self.data, period_me1=self.p.fast, period_me2=self.p.slow).macd
        boll = bt.indicators.BollingerBands(
            self.data, period=self.p.channel, devfactor=self.p.mult)

        t1 = (self.l.macd(0)-self.l.macd(-1))*self.p.sensitivity
        self.l.exp = boll.top - boll.bot

        self.l.utrend = bt.If(t1 >= 0, t1, 0.0)
        self.l.dtrend = bt.If(t1 < 0, -1.0*t1, 0.0)
        self.l.dead = bt.indicators.AverageTrueRange(
            self.data, period=50).atr*self.p.dead


class SMALong(bt.Strategy):
    params = dict(
        fast_period=15,
        slow_period=40,
        maxrisk=0.10,
        channel_break_period=7,
        printlog=True,
        start_trade_date=None,
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.data.datetime.datetime(0)
            print('%s,%s' % (dt.strftime("%Y-%m-%d %H:%M"), txt))

    def __init__(self):
        self.pe_ftm_rank=bt.ind.PercentRank(self.data.pe_ftm,period=200, subplot=True, plotname="fwd pe rank")
        self.pe_ftm = bt.ind.SMA(self.data.pe_ftm, period=1, subplot=True, plotname="fwd_pe_ratio")
        self.pe_deducted_ttm = bt.ind.SMA(self.data.val_pe_deducted_ttm, period=1, subplot=True, plotname="pe_deducted_ttm")
        self.cross_happend_date = None
        self.start_trade_date = self.params.start_trade_date or self.data.datetime.date(0)
        self.open_order = None
        self.close_order = None
        self.fast_ma = bt.ind.SMA(self.data, period=self.params.fast_period)
        self.slow_ma = bt.ind.SMA(self.data, period=self.params.slow_period)
        self.highest = bt.ind.Highest(self.data, period=20, subplot=False, plot=False)
        self.lowest = bt.ind.Lowest(self.data, period=20, subplot=False, plot=False)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma, plot=False)
        self.WAE = WaddahAttarExplosion(self.data,plot=False)
        

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            self.open_order = None
            size_abs = abs(order.executed.size)
            if order.isbuy():
                self.log("Buy executed @%.2f"%order.executed.price)
                self.log("StopTrail Sell order placed size=%d" %
                            size_abs)
                self.close_order = self.sell(
                    exectype=bt.Order.StopTrail, size=size_abs, trailpercent=self.params.maxrisk)
            else: #only long
                self.log("Sell executed @%.2f"%order.executed.price)
                pass

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def get_open_size(self):
        # allow_loss = self.broker.getvalue() * self.params.maxrisk
        return round(self.broker.getvalue() / self.data.close[0],-2)
        

    def enter_signal(self):
        # if self.crossover>0:
        #     self.cross_happend_date = self.data.datetime.date(0)
        # if not self.cross_happend_date:
        #     return False
        # channel_break_period = datetime.timedelta(days=self.params.channel_break_period)
        # if self.data.datetime.date(0) - self.cross_happend_date < channel_break_period:
        #     if self.data.high[0]>self.highest[0]:
        #         return True
        # return False
        return self.crossover>0 and self.pe_ftm[0]<32
        #and self.data.high[0]>self.highest[0]
        #return self.crossover>0 and self.WAE.utrend[0] > self.WAE.dead[0]
        #return self.fast_ma > self.slow_ma and self.data.high[0]>self.highest[0]

    def next(self):
        if self.data.datetime.date(0)<self.start_trade_date:
            return
        if self.open_order or self.position:
            return
        signal = self.enter_signal()
        if signal:
            size = self.get_open_size()
            self.open_order = self.buy(size=size)
            self.log("order open: Buy size=%d" % size)

    def stop(self):
        self.log('maxrisk=%.2f, fa=%d,sl=%d Ending Value %.2f maxdrw=%.2f' %
                 (self.params.maxrisk,self.params.fast_period,self.params.slow_period, 
                 self.broker.getvalue(), self.stats.drawdown.maxdrawdown[-1]), doprint=True)

class MyBuySell(bt.observers.BuySell):
    def __init__(self):
        self.plotlines.sell.color="orange"
class MyBroker(bt.Observer):
    lines = ('value',)

    plotinfo = dict(plot=True, subplot=True)

    def next(self):
        self.lines.value[0] = value = self._owner.broker.getvalue()
    
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    import os
    import sys
    df = yf.download("0700.hk", start="2015-6-1",end="2020-1-1", auto_adjust=True)
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath,"../data/0700.fundamental.csv")
    df2=pandas.read_csv(datapath)
    # df2.drop("close",axis=1)
    df2.Date=pandas.to_datetime(df2.Date)
    df2=df2.set_index("Date")
    df3=df.join(df2)
    data = PandasData_Fundamentals(
        dataname=df3,name="0700.hk",
        # attrs=["pe_ttm",'ev2_to_ebitda','eps_ttm','pe_ttm','val_pe_deducted_ttm','profit_ttm','gr_ttm']
    )
    
    cerebro.adddata(data)

    strats = cerebro.addstrategy(SMALong, maxrisk=0.11, start_trade_date=datetime.date(2017, 1, 1))
    
    cerebro.broker.setcash(1000000.0)
    cerebro.broker.setcommission(commission=0.001,leverage=2)
    cerebro.addobserver(bt.observers.DrawDown)
    # cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='mysharpe')
    # print('quit_signals;ma_period;sig_cnt;RVI;val;maxdrw')
    # cerebro.addobserver(MyBuySell)
    # cerebro.addobserver(MyBroker)
    thestrat=cerebro.run()#stdstats=False
    cerebro.plot()#style='candlestick',bardown="purple"
