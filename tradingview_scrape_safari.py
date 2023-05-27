from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
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
        self.ticker = ticker.upper()
        self.exchange = exchange.capitalize()
        self.url_ticker = f'{self.exchange}-{self.ticker}'
        self.url_base = 'https://www.tradingview.com/symbols/'
        self.incomestatement = self.get_incomestatement()
        self.balancesheet = self.get_balancesheet()
        self.cashflow = self.get_cashflow()
        self.currency = None
        
        
    def get_incomestatement(self):
        """
        Returns DataFrame of income statement.
        """

        todrop = ['Non-operating income, total', 'Equity in earnings','Non-controlling/minority interest',
                  'After tax other income/expense', 'Net income before discontinued operations', 'Discontinued operations', 
                  'Dilution adjustment', 'Preferred dividends','Diluted net income available to common stockholders',
                  'Diluted earnings per share (Diluted EPS)','Average basic shares outstanding', 'Diluted shares outstanding']
        
        url = self.url_base + self.url_ticker + '/financials-income-statement/'
        
        scrp = self.scrape_financials(url=url, lblsec_cls="container-OWKkVLyj",
                      currency_cls="firstColumn-OWKkVLyj",
                      lblyear_cls="value-OxVAcLqi",
                      mtrsec_cls="container-C9MdAMrq",
                      mtrname_cls="titleText-C9MdAMrq",
                      mtrdata_cls="value-OxVAcLqi")
        
        scrp = scrp.drop(todrop, axis=0)
        return scrp
    
    
    def get_balancesheet(self):
        """
        Based on given parameters, returns balance sheet statement in pandas.DataFrame format. 
        If no parameters are given, it includes all parameters into statement.
        """
    
        url = self.url_base + self.url_ticker + '/financials-balance-sheet/'

        todrop = ["Total liabilities & shareholders' equities"]
        
        scrp = self.scrape_financials(url=url, lblsec_cls="container-OWKkVLyj",
                      currency_cls="firstColumn-OWKkVLyj",
                      lblyear_cls="value-OxVAcLqi",
                      mtrsec_cls="container-C9MdAMrq",
                      mtrname_cls="titleText-C9MdAMrq",
                      mtrdata_cls="value-OxVAcLqi")
        
        scrp = scrp.drop(todrop, axis=0)
        return scrp
    
    
    def get_cashflow(self):
        """
        Based on given parameters, returns cashflow statement in pandas.DataFrame format. 
        If no parameters are given, it includes all parameters into statement.
        """
        url = self.url_base + self.url_ticker + '/financials-cash-flow/'

        todrop = []
        
        scrp = self.scrape_financials(url=url, lblsec_cls="container-OWKkVLyj",
                      currency_cls="firstColumn-OWKkVLyj",
                      lblyear_cls="value-OxVAcLqi",
                      mtrsec_cls="container-C9MdAMrq",
                      mtrname_cls="titleText-C9MdAMrq",
                      mtrdata_cls="value-OxVAcLqi")
        
        scrp = scrp.drop(todrop, axis=0)
        return scrp

    
    def scrape_financials(self, url: list, lblsec_cls: str, currency_cls: str, 
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
        
        labelsection = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, lblsec_cls)))
        #labelsection = driver.find_element(by=By.CLASS_NAME, value=lblsec_cls)
        currency = labelsection.find_element(by=By.CLASS_NAME, value=currency_cls).text 
        labelyears = [i.text for i in labelsection.find_elements(by=By.CLASS_NAME, value=lblyear_cls)]
        data[currency] = labelyears
        
        self.currency = currency
        
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

    
    def bar(self, financialstatement: pd.DataFrame):
        """
        Ploting basic metrics into bar graph.
        """
        metrics = None
        colors = None
        
        if financialstatement.equals(self.incomestatement):
            metrics = ['Total revenue', 'Gross profit', 'Operating income', 'Pretax income', 'Net income']
            colors = ['blue', 'green', 'purple', 'red', 'orange', 'white']
        elif financialstatement.equals(self.balancesheet):
            metrics = ['Total assets', 'Total liabilities']
            colors = ['blue', 'green', 'white']
        elif financialstatement.equals(self.cashflow):
            metrics = ['Cash from operating activities', 'Cash from investing activities', 'Cash from financing activities',
                       'Free cash flow']
            colors = ['blue', 'green', 'red', 'orange', 'white']
        else:
            raise ValueError("Not a financial statement name")
        
        data = financialstatement.loc[metrics]
        # Data for last 5 periods
        data = data.iloc[:,-6:-1]
        data = self.to_float(data)
        
        num_metrics = data.shape[0]
        num_periods = data.shape[1]
        
        # Each time period has white-space between them (excluding the last one)
        x = range(num_metrics * num_periods + (num_periods -1))
        y = []
        x_labels = list(data.columns)

        for period in range(num_periods):
            y += list(data.iloc[:,period]) + [0]
        y.pop()
        
        # Plotting 
        plt.bar(x, y, color=colors, zorder=2)
        
        if 'Total revenue' in metrics:
            plt.xticks(range(2, len(x), num_metrics+1), x_labels)
            plt.title(self.ticker + " Income Statement")
        elif 'Total assets' in metrics:
            plt.xticks(range(1, len(x), num_metrics+1), x_labels)
            plt.title(self.ticker + " Balance Sheet")
        elif 'Free cash flow' in metrics:
            plt.xticks(range(2, len(x), num_metrics+1), x_labels)
            plt.title(self.ticker + " Cash Flow")
        
        # Extend ylim to have space for legend
        plt.ylim(plt.ylim()[0], plt.ylim()[1] * 1.25)
        # Get the current locations of y-labels.
        locs, _ = plt.yticks()  
        # Change labels to display in shorter form with unit
        labels = [self.float_to_str(i) for i in list(locs)]
        plt.yticks(locs, labels)    
        
        # Create the legend
        legend_patches = [plt.Rectangle((0,0),1,1, color=color) for color in colors]
        plt.legend(legend_patches, metrics, fontsize='small')
        
        # Turning on the grid
        plt.grid(True, zorder=1)
        
        plt.show()
        
    
    def to_float(self, arr: pd.DataFrame):
        """
        Input is pandas.DataFrame and function returns converted values with its unit (e.g. '52.11M') 
        into float value (-> '52_110_000')
        """
        res = pd.DataFrame(index=arr.index, columns=arr.columns)
        for col in range(len(arr.columns)):
            for row in range(len(arr.iloc[:,col])):
                unit = arr.iloc[row,col][-1]
                # Replace the invalid minus sign character
                res.iloc[row,col] = float(arr.iloc[row,col][:-1].replace('−', '-')) * (10**self.unit_to_exponent(unit))
        return res
    
    
    def unit_to_exponent(self, unit: str): 
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
        
    def float_to_str(self, num: float):
        """
        Converts number into string-based number (e.g. 1_500_000 into 1.5M)
        """
        ans = ""
        negative = False
        if num < 0:
            negative = True
            num = abs(num)
        
        if (num / 1000) < 1:
            ans = str(num)
        elif (num / 1_000_000) < 1:
            ans =  f"{num/1000:.1f}K"
        elif (num / 1_000_000_000) < 1:
            ans = f"{num/1_000_000:.1f}M"
        else:
            ans = f"{num/1_000_000_000:.1f}B"
            
        if negative:
            ans = '-' + ans
            
        return ans
         
    
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
                        ebit: bool = False):
        """
        Based on given parameters, returns income statement in pandas.DataFrame format. 
        If no parameters are given, it includes all parameters into statement.
        """
        
        todrop = []
        
        if (totalrevenue or cogs or grossprofit or operatingexpenses or operatingincome or 
            pretaxincome or taxes or netincome or totaloperexpenses or eps or ebitda or ebit) == True:
            if totalrevenue == False:
                todrop.append("Total revenue")
            if cogs == False:
                todrop.append("Cost of goods sold")
            if grossprofit == False:
                todrop.append("Gross profit")
            if operatingexpenses == False:
                todrop.append("Operating expenses (excl. COGS)")
            if operatingincome == False:
                todrop.append("Operating income")
            if pretaxincome == False:
                todrop.append("Pretax income")
            if taxes == False:
                todrop.append("Taxes")
            if netincome == False:
                todrop.append("Net income")
            if totaloperexpenses == False:
                todrop.append("Total operating expenses")
            if eps == False:
                todrop.append("Basic earnings per share (Basic EPS)")
            if ebitda == False:
                todrop.append("EBITDA")
            if ebit == False:
                todrop.append("EBIT")
        
        income_copy = self.incomestatement.copy()
        income_copy = income_copy.drop(todrop, axis=0)
        return income_copy
        

    def balancesheet(self,
                     totalassets: bool = False, 
                     totalliabilities: bool = False,
                     totalequity: bool = False,
                     totaldebt: bool = False,
                     netdebt: bool = False,
                     bookvaluepershare: bool = False):
        """
        Based on given parameters, returns balance sheet statement in pandas.DataFrame format. 
        If no parameters are given, it includes all parameters into statement.
        """
        
        todrop = []
        
        if (totalassets or totalliabilities or totalequity or totaldebt or netdebt or 
            bookvaluepershare) == True:
            if totalassets == False:
                todrop.append("Total assets")
            if totalliabilities == False:
                todrop.append("Total liabilities")
            if totalequity == False:
                todrop.append("Total equity")
            if totaldebt == False:
                todrop.append("Total debt")
            if netdebt == False:
                todrop.append("Net debt")
            if bookvaluepershare == False:
                todrop.append("Book value per share")
        
        balance_copy = self.balancesheet.copy()
        balance_copy = balance_copy.drop(todrop, axis=0)
        return balance_copy
    
    
    def cashflow(self,
                 operating: bool = False, 
                 investing: bool = False,
                 financing: bool = False,
                 freecashflow: bool = False):
        """
        Based on given parameters, returns cashflow statement in pandas.DataFrame format. 
        If no parameters are given, it includes all parameters into statement.
        """
        
        todrop = []
        
        if (operating or investing or financing or freecashflow) == True:
            if operating == False:
                todrop.append("Cash from operating activities")
            if investing == False:
                todrop.append("Cash from investing activities")
            if financing == False:
                todrop.append("Cash from financing activities")
            if freecashflow == False:
                todrop.append("Free cash flow")
        
        cash_copy = self.cashflow.copy()
        cash_copy = cash_copy.drop(todrop, axis=0)
        return cash_copy