#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 12 09:29:59 2019

@author: Thomas
"""

"""Main process"""

"""restart the databases"""

import sqlite3
conn = sqlite3.connect('Data/investData.db')
cur = conn.cursor()

cur.execute("drop table if exists orders")
conn.commit()

cur.execute("create table orders (date string, type text, ticker string, quantity real, pru real)")
conn.commit()

conn = sqlite3.connect('Data/investData.db')
cur.execute("drop table if exists priceTab")
conn.commit()

cur.execute("create table priceTab ( date string, ticker text, price real)")
conn.commit()

conn.close()
"""end the databases"""

"""add orders"""
date=input('Date ? (format yyyy-mm-dd)')
ttype=input('B/S ?')
ticker=input('Ticker ?')
quantity=input('Quantity ?')
pru=input('PRU ?')

conn = sqlite3.connect('Data/investData.db')
cur = conn.cursor()
cur.execute("insert into orders values (?, ?, ?, ?, ?)",(date , ttype , ticker , quantity , pru ))
conn.commit()
conn.close
"""end add orders"""


"""import past prices """
import pandas as pd
pastPrice = pd.read_csv('Data/initialPrices.csv')

conn = sqlite3.connect('Data/investData.db')
cur = conn.cursor()

for iLine in range(len(pastPrice)):
    cur.execute("insert into priceTab values (?, ?, ?)",(pastPrice['date'][iLine] , pastPrice['ticker'][iLine] , pastPrice['close'][iLine] ))
    conn.commit()
conn.close
"""end add orders"""


"""loop job"""
#import the sql data 

import sqlite3
import numpy as np
import datetime
conn = sqlite3.connect('Data/investData.db')
cur = conn.cursor()
#Place the cursor on the begining of the db
cur.execute('Select * FROM orders')
orders=cur.fetchall()
cur.execute('Select * FROM priceTab')
priceHist=cur.fetchall()
conn.close

#convert to a dataframe
orders=pd.DataFrame(orders,columns=['date' , 'ttype' , 'ticker' , 'quantity' , 'pru' ])
priceHist=pd.DataFrame(priceHist,columns=['date' , 'ticker' , 'price' ])

#Define the time vector

newIndex=orders.sort_values('date').index #sort by date
allTickers=orders['ticker'].unique()
today=datetime.datetime.now().strftime("%Y-%m-%d")
yesterday=datetime.datetime.now()-datetime.timedelta(days=1)
yesterday=yesterday.strftime("%Y-%m-%d")
invDate=priceHist['date'].unique()

fundComp=np.zeros((len(invDate),len(allTickers)))
fundVal=np.zeros((len(invDate),len(allTickers)))
fundVal=np.zeros((len(invDate),len(allTickers)))
fundPMV=np.zeros((len(invDate),len(allTickers)))


iOrderDate=0
for iAllDate in range(len(invDate)):
        for iOrderB in range(iOrderDate,len(orders)):
            if invDate[iAllDate]>orders['date'][newIndex[iOrderB]]:
                for iAllB in range(iAllDate,len(invDate)):
                    tick=orders['ticker'][newIndex[iOrderB]]
                    iStock=sum((allTickers==tick)*range(len(allTickers)))
                    if orders['ttype'][newIndex[iOrderB]]=='B':
                        sens=1
                    else:
                        sens=-1
                    fundComp[iAllB,iStock]=fundComp[iAllB,iStock]+sens*orders['quantity'][newIndex[iOrderB]]
                    
                    lastPrice=0#Necessary as trade day may differ from investments 
                    dayPrice=priceHist[(priceHist['date']==invDate[iAllB]) & (priceHist['ticker']==tick)]
                    if dayPrice==[]:
                        dayPrice=lastPrice
                    else:
                        lastPrice=dayPrice
                    fundVal[iAllB,iStock]=fundVal[iAllB,iStock]+sens*orders['quantity'][newIndex[iOrderB]]*dayPrice
                    fundPMV[iAllB,iStock]=fundPMV[iAllB,iStock]+sens*orders['quantity'][newIndex[iOrderB]]*dayPrice-sens*orders['quantity'][newIndex[iOrderB]]*orders['pru'][newIndex[iOrderB]]
                iOrderDate+=1
