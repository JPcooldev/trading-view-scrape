from selenium import webdriver
from selenium.webdriver.common.by import By
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time

"""https://www.tradingview.com/symbols/{exchange}-{ticker}/financials-{statement-name}"""

class Ticker:
    """parameters:
            ticker - string or list of strings, e.g. 'AAPL'
            TTM - boolean, TTM included or not
            
    """
    def __init__(self, ticker: str, exchange: str):
        self.ticker = ticker.capitalize()
        self.exchange = exchange.capitalize()
        self.url_ticker = f'{self.exchange}-{self.ticker}'
        self.url_base = 'https://www.tradingview.com/symbols/'

    def incomestatement(self,
                        totalrevenue: bool = False, 
                        cogs: bool = False,
                        grossprofit: bool = False,
                        operatingexpenses: bool = False,
                        operatingincome: bool = False,
                        pretaxincome: bool = False,
                        taxes: bool = False,
                        netincome: bool = False,
                        totaloperexpenses:bool = False,
                        eps: bool = False,
                        ebitda: bool = False,
                        ebit: bool = False,
                        all: bool = True):
        url = self.url_base + self.url_ticker + '/financials-income-statement/'

        #if (totalrevenue or cogs or grossprofit or operatingexpanses or 
        #    operatingincome or pretaxincome or taxes or netincome) == False:
        scrp = self.scrape_financials(url=url, lblsec_cls="container-OWKkVLyj",
                      currency_cls="firstColumn-OWKkVLyj",
                      lblyear_cls="value-OxVAcLqi",
                      mtrsec_cls="container-C9MdAMrq",
                      mtrname_cls="titleText-C9MdAMrq",
                      mtrdata_cls="value-OxVAcLqi")
        todrop = ['Non-operating income, total', 'Equity in earnings','Non-controlling/minority interest',
                  'After tax other income/expense', 'Net income before discontinued operations', 'Discontinued operations', 
                  'Dilution adjustment', 'Preferred dividends','Diluted net income available to common stockholders',
                  'Diluted earnings per share (Diluted EPS)','Average basic shares outstanding', 'Diluted shares outstanding']
        
        scrp = scrp.drop(todrop, axis=0)
        return scrp
    
    def balancesheet(self,
                     totalassets: bool = False, 
                     totalliabilities: bool = False,
                     totalequity: bool = False,
                     totaldebt: bool = False,
                     netdebt: bool = False,
                     bookvaluepershare: bool = False,
                     all: bool = True):
        url = self.url_base + self.url_ticker + '/financials-balance-sheet/'

        scrp = self.scrape_financials(url=url, lblsec_cls="container-OWKkVLyj",
                      currency_cls="firstColumn-OWKkVLyj",
                      lblyear_cls="value-OxVAcLqi",
                      mtrsec_cls="container-C9MdAMrq",
                      mtrname_cls="titleText-C9MdAMrq",
                      mtrdata_cls="value-OxVAcLqi")
        todrop = ["Total liabilities & shareholders' equities"]
        
        scrp = scrp.drop(todrop, axis=0)
        return scrp
    
    def cashflow(self,
                 operating: bool = False, 
                 investing: bool = False,
                 financing: bool = False,
                 freecashflow: bool = False,
                 all: bool = True):
        """
        Based on given parameters, returns cashflow statement in pandas.DataFrame format. 
        If no parameters are given, it includes all parameters into statement.
        """
        url = self.url_base + self.url_ticker + '/financials-cash-flow/'

        scrp = self.scrape_financials(url=url, lblsec_cls="container-OWKkVLyj",
                      currency_cls="firstColumn-OWKkVLyj",
                      lblyear_cls="value-OxVAcLqi",
                      mtrsec_cls="container-C9MdAMrq",
                      mtrname_cls="titleText-C9MdAMrq",
                      mtrdata_cls="value-OxVAcLqi")
        return scrp

    def scrape_financials(self, url: str, lblsec_cls: str, currency_cls: str, 
                 lblyear_cls: str, mtrsec_cls: str, mtrname_cls: str, 
                 mtrdata_cls: str):
        """
        Scrapes wanted data from tradingview website and return it in pandas.DataFrame format.
        1. Finds section for title, then scrapes used currency and period in which data occured.
        2. Finds sections for each financial metric and its data.
        """
        driver = webdriver.Safari()
        driver.get(url)
        time.sleep(0.7)

        dfs = []
        data = {}

        labelsection = driver.find_element(by=By.CLASS_NAME, value=lblsec_cls)
        currency = labelsection.find_element(by=By.CLASS_NAME, value=currency_cls).text 
        labelyears = [i.text for i in labelsection.find_elements(by=By.CLASS_NAME, value=lblyear_cls)]
        data[currency] = labelyears
        
        metricsection = driver.find_elements(by=By.CLASS_NAME, value=mtrsec_cls)
        
        for sec in metricsection:
            metricname = sec.find_element(by=By.CLASS_NAME, value=mtrname_cls).text
            metricdata = sec.find_elements(by=By.CLASS_NAME, value=mtrdata_cls)

            data[metricname] = [re.sub(r'[\u202a\u202c]', '', i.text) for i in metricdata]
        
        columns = data[currency]
        
        del data[currency]
        
        tab = pd.DataFrame(index=data.keys(), columns=columns)
        for key, val in data.items():
            tab.loc[key] = val  
            
        dfs.append(tab)

        df = pd.concat(dfs, axis=1)
                                
        driver.quit()

        return df

    # so far just for income statement
    def plot_bars(self, financialstatement: pd.DataFrame):
        pltdata = financialstatement.loc[['Total revenue', 'Gross profit', 'Operating income', 'Net income']]
        pltdata = pltdata.iloc[:,-5:-1]
        pltval = self.to_float(pltdata)
       
        x = range(pltval.shape[0] * pltval.shape[1] + 1 * pltval.shape[1])
    
        y = []
        for col in pltval.columns:
            y += list(pltval.loc[:,col]) + [0]
        colors = ['blue', 'green', 'red', 'orange', 'white']
        
        plt.bar(x,y, color=colors)
        plt.xticks([])
    
    def to_float(self, arr: pd.DataFrame):
        """
        Input is pandas.DataFrame and function returns converted values with its unit (e.g. '52.11M') into float value (-> '52_110_000')
        """
        res = pd.DataFrame(index=arr.index, columns=arr.columns)
        for col in range(len(arr.columns)):
            for row in range(len(arr.iloc[:,col])):
                unit = arr.iloc[row,col][-1]
                res.iloc[row,col] = float(arr.iloc[row,col][:-1]) * (10**self.exponent(unit))
        return res
    
    
    def exponent(self, unit: str): 
        """
        Returns exponent based on unit (billion, million, thousand).
        """
        if unit == 'B':
            return 9
        elif unit == 'M':
            return 6
        elif unit == 'K':
            return 3
        else:
            return 0
    #next
        
