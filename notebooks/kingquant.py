import yfinance as yf
import pandas as pd
import datetime as dt
from scipy import stats

def get_stock_info(ticker):
    stock_info={}
    df=yf.download(ticker,start=dt.date.today()-dt.timedelta(days=366),auto_adjust=True,progress=True)
    stock_info=yf.Ticker(ticker).info
    stock_info['1w_chg_pct']=100*(df.loc[max(df.index)-dt.timedelta(weeks=1):,'Close'][-1]/df.loc[max(df.index)-dt.timedelta(weeks=1):,'Close'][0]-1)
    stock_info['1m_chg_pct']=100*(df.loc[max(df.index)-dt.timedelta(days=30):,'Close'][-1]/df.loc[max(df.index)-dt.timedelta(days=30):,'Close'][0]-1)
    stock_info['1y_chg_pct']=100*(df.loc[max(df.index)-dt.timedelta(days=365):,'Close'][-1]/df.loc[max(df.index)-dt.timedelta(days=365):,'Close'][0]-1)
    stock_info['max_drawdown']=100*(df.Close[-1]/max(df.Close)-1)
    stock_info['ticker']=ticker
    return stock_info

def get_port_holding_info(df_port):
    df_port.columns=['ticker','weight']
    df_stock=pd.DataFrame()
    for ticker in df_port.ticker:
        try:
            stock_info=get_stock_info(ticker)
            df_stock=df_stock.append(stock_info,ignore_index=True)
        except:
            pass
    
    df_stock['ratecode']=df_stock['financialCurrency']+'-USD'
    df_stock['ratecode2']=df_stock['currency']+'-USD'
    df_stock['USD-USD']=1
    df_stock['CNY-USD']=yf.Ticker('CNYUSD=X').history().Close[-1]
    df_stock['TWD-USD']=yf.Ticker('TWDUSD=X').history().Close[-1]
    df_stock['HKD-USD']=yf.Ticker('HKDUSD=X').history().Close[-1]
    df_stock['EUR-USD']=yf.Ticker('EURUSD=X').history().Close[-1]
    df_stock['rate']=df_stock['USD-USD'].where(df_stock['ratecode']=='USD-USD')
    df_stock.loc[df_stock['rate'].isna(),['rate']]=df_stock['CNY-USD'].where(df_stock['ratecode']=='CNY-USD')
    df_stock.loc[df_stock['rate'].isna(),['rate']]=df_stock['TWD-USD'].where(df_stock['ratecode']=='TWD-USD')
    df_stock.loc[df_stock['rate'].isna(),['rate']]=df_stock['EUR-USD'].where(df_stock['ratecode']=='EUR-USD')
    df_stock.loc[df_stock['rate'].isna(),['rate']]=df_stock['HKD-USD'].where(df_stock['ratecode']=='HKD-USD')

    df_stock['rate2']=df_stock['USD-USD'].where(df_stock['ratecode2']=='USD-USD')
    df_stock.loc[df_stock['rate2'].isna(),['rate2']]=df_stock['CNY-USD'].where(df_stock['ratecode2']=='CNY-USD')
    df_stock.loc[df_stock['rate2'].isna(),['rate2']]=df_stock['TWD-USD'].where(df_stock['ratecode2']=='TWD-USD')
    df_stock.loc[df_stock['rate2'].isna(),['rate2']]=df_stock['EUR-USD'].where(df_stock['ratecode2']=='EUR-USD')
    df_stock.loc[df_stock['rate2'].isna(),['rate2']]=df_stock['HKD-USD'].where(df_stock['ratecode2']=='HKD-USD')

  

    return df_stock

def get_port_holding_metric(df_stock):
    df_metric=pd.DataFrame()
    df_metric['ticker']=df_stock['ticker']
    #df_metric['weight']=df_stock['weight']
    df_metric['price']=df_stock['currentPrice']
    df_metric['1w_chg_pct']=df_stock['1w_chg_pct']
    df_metric['1m_chg_pct']=df_stock['1m_chg_pct']
    df_metric['drawdown']=df_stock['max_drawdown']
    df_metric['target_price']=df_stock['targetMedianPrice']

        
    df_metric['market_cap']=df_stock['marketCap']*df_stock['rate2']
    df_metric['weight']=df_metric['market_cap']/df_metric['market_cap'].sum()
    df_metric['revenue']=df_stock['totalRevenue']*df_stock['rate']
    df_metric['revenue_last_year']=df_metric['revenue']/(1+df_stock['revenueGrowth'])
    df_metric['gross_profit']=df_stock['grossProfits']*df_stock['rate']
    df_metric['cashflow']=df_stock['operatingCashflow']*df_stock['rate']
    df_metric['net_income']=df_stock['netIncomeToCommon']*df_stock['rate']

    df_metric['pcf']=df_metric['market_cap']/df_metric['cashflow']
    df_metric['pe_ttm']=df_stock['trailingPE']
    df_metric['eps_ttm']=df_stock['trailingEps']
    df_metric['fwd_eps']=df_stock['forwardEps']
    df_metric['pe_fwd']=df_stock['forwardPE']
    df_metric['peg']=df_stock['pegRatio']
    df_metric['revenue_growth']=100*df_stock['revenueGrowth']
    df_metric['est_earning_growth']=(df_stock['forwardEps']/df_stock['trailingEps']-1)
    df_metric['fwd_peg']=df_metric['pe_fwd']/df_metric['est_earning_growth']

    df_metric['roe']=100*df_stock['returnOnEquity']
    df_metric['gross_margin']=100*df_stock['grossMargins']
    df_metric['cf_margin']=100*df_metric['cashflow']/df_metric['revenue']
    df_metric['net_margin']=100*df_stock['profitMargins']



    return df_metric

def get_port_metric(df_metric):
    port_stat=dict()
    port_stat['market_cap']=df_metric['market_cap'].sum()
    port_stat['revenue']=df_metric['revenue'].sum()
    port_stat['revenue_growth']=(port_stat['revenue']/df_metric['revenue_last_year'].sum()-1)
    port_stat['ps']=port_stat['market_cap']/port_stat['revenue']

    port_stat['gross_profit']=df_metric['gross_profit'].sum()
    port_stat['pgp']=port_stat['market_cap']/port_stat['gross_profit']
    port_stat['gross_margin']=port_stat['gross_profit']/port_stat['revenue']

    port_stat['cashflow']=df_metric['cashflow'].sum()
    port_stat['pcf']=port_stat['market_cap']/port_stat['cashflow']
    port_stat['cf_rate']=1/port_stat['pcf']
    port_stat['cf_margin']=port_stat['cashflow']/port_stat['revenue']

    port_stat['net_income']=df_metric['net_income'].sum()
    port_stat['pe']=port_stat['market_cap']/port_stat['net_income']
    port_stat['income_rate']=1/port_stat['pe']
    port_stat['profit_margin']=port_stat['net_income']/port_stat['revenue']
    port_stat['est_net_income']=(df_metric['net_income']*(1+df_metric['est_earning_growth'])).sum()
    port_stat['fwd_pe']=port_stat['market_cap']/port_stat['est_net_income']
    port_stat['fwd_income_growth']=(port_stat['est_net_income']/port_stat['net_income']-1)

    
    

    return port_stat

def get_price_change(ticker):
    price_info={}
    df=yf.download(ticker,start=dt.date.today()-dt.timedelta(days=366),auto_adjust=True,progress=False)
    price_info['ticker']=ticker
    price_info['last_price']=df.Close[-1]
    price_info['1w_chg_pct']=100*(df.loc[max(df.index)-dt.timedelta(weeks=1):,'Close'][-1]/df.loc[max(df.index)-dt.timedelta(weeks=1):,'Close'][0]-1)
    price_info['2w_chg_pct']=100*(df.loc[max(df.index)-dt.timedelta(weeks=2):,'Close'][-1]/df.loc[max(df.index)-dt.timedelta(weeks=2):,'Close'][0]-1)
    price_info['1m_chg_pct']=100*(df.loc[max(df.index)-dt.timedelta(days=30):,'Close'][-1]/df.loc[max(df.index)-dt.timedelta(days=30):,'Close'][0]-1)
    price_info['1y_chg_pct']=100*(df.loc[max(df.index)-dt.timedelta(days=365):,'Close'][-1]/df.loc[max(df.index)-dt.timedelta(days=365):,'Close'][0]-1)
    price_info['drawdown']=100*(df.Close[-1]/max(df.Close)-1)
    price_info['diff_to_60d_avg']=100*(df.Close[-1]/df.Close[-60:].mean()-1)
    price_info['diff_to_200d_avg']=100*(df.Close[-1]/df.Close[-200:].mean()-1)
   
    return price_info

def cal_rolling_cov(s1,s2,period):
    start_date=s1.index[0]
    cov=dict()
    while start_date<s1.index.max()-dt.timedelta(days=period):
        end_date=start_date+dt.timedelta(days=period)
        a1=s1[start_date:end_date]
        a2=s2[start_date:end_date]
        cov[end_date]=stats.pearsonr(a1, a2)[0]
        start_date=start_date+dt.timedelta(days=1)
    cov=pd.Series(cov)
    cov.name=s1.name+'-'+s2.name

    return pd.Series(cov)