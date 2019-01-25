#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 12 09:29:59 2019

@author: Thomas
"""

"""Main process"""
import sqlite3
import numpy as np
import pandas as pd

def restart_all():
    """restart the databases"""
    conn = sqlite3.connect('Data/investData.db')
    cur = conn.cursor()
    
    cur.execute("drop table if exists orders")
    conn.commit()
    
    cur.execute("create table orders (date string, type text, ticker string, quantity real, pru real)")
    conn.commit()
    
    cur.execute("drop table if exists priceTab")
    conn.commit()
    
    cur.execute("create table priceTab ( date string, ticker text, price real)")
    conn.commit()
    
    conn.close()
    """end the databases"""

def add_order():
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

def import_past_prices():
    """import past prices """
    pastPrice = pd.read_csv('Data/initialPrices.csv')
    
    conn = sqlite3.connect('Data/investData.db')
    cur = conn.cursor()
    
    for iLine in range(len(pastPrice)):
        cur.execute("insert into priceTab values (?, ?, ?)",(pastPrice['date'][iLine] , pastPrice['ticker'][iLine] , pastPrice['close'][iLine] ))
        conn.commit()
    conn.close
    """end import"""

def loop_job():
    """loop job"""
    #import the sql data 
    
    import datetime
    import requests
   
    from bs4 import BeautifulSoup
    
    day=datetime.datetime.now().isoweekday()
    if day != 1 or day != 7: #No news on sundays & monday
            
        
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
        
        newsIn={'ticker':[],'news':[]}
        allNews=pd.DataFrame(data=newsIn)
        #Add yesterday to the base
        for tick in allTickers:
            site = "https://finance.yahoo.com/quote/"+tick+"?p="+tick
            page = requests.get(site).text #Import all html data as text
            soup = BeautifulSoup(page,'lxml')
            table = soup.find('td', {'data-test':'PREV_CLOSE-value'})
            lastClose=table.string.strip()
            priceHist.loc[len(priceHist)] = [yesterday,tick,float(lastClose)]
            #Add to the sql base !! commented for test purposes
            #conn = sqlite3.connect('Data/investData.db')
            #cur = conn.cursor()
            #cur.execute("insert into priceTab values (?, ?, ?)",(yesterday , tick , lastClose))
            #conn.commit()
            #conn.close
            newsTable = soup.find('ul', {'class':'Mb(0) Ov(h) P(0) Wow(bw)'})

            for row in newsTable.findAll('p'):
                #allNews.append(str(row.string.strip()))
                allNews.loc[len(allNews)] = [tick,str(row.string.strip())]

        invDate=priceHist['date'].unique()
        invDate.sort()
        
        fundComp=np.zeros((len(invDate),len(allTickers)))
        fundVal=np.zeros((len(invDate),len(allTickers)))
        fundVal=np.zeros((len(invDate),len(allTickers)))
        fundPMV=np.zeros((len(invDate),len(allTickers)))
        Comp=np.zeros((len(invDate),len(allTickers)))
        iOrderDate=0
        for iAllDate in range(len(invDate)):
                for iOrderB in range(iOrderDate,len(orders)):
                    if invDate[iAllDate]>orders['date'][newIndex[iOrderB]]:
                        tick=orders['ticker'][newIndex[iOrderB]]
                        iStock=sum((allTickers==tick)*range(len(allTickers)))
                        if orders['ttype'][newIndex[iOrderB]]=='B':
                            sens=1
                        else:
                            sens=-1
                            
                        #Introduce a compensatory variable
                        for iAllB in range(iAllDate):
                            Comp[iAllB,iStock]=fundVal[iAllB,iStock]+sens*orders['quantity'][newIndex[iOrderB]]*orders['pru'][newIndex[iOrderB]]
                        
                        for iAllB in range(iAllDate,len(invDate)):
                            
                            fundComp[iAllB,iStock]=fundComp[iAllB,iStock]+sens*orders['quantity'][newIndex[iOrderB]]
                            
                            lastPrice=0#Necessary as trade day may differ from investments 
                            if sum((priceHist['date']==invDate[iAllB]) & (priceHist['ticker']==tick))==1:
                                dayPrice=sum(priceHist[(priceHist['date']==invDate[iAllB]) & (priceHist['ticker']==tick)]['price'])
                                lastPrice=dayPrice
                            else:
                                dayPrice=lastPrice
                                
                            if dayPrice>0:
                                fundVal[iAllB,iStock]=fundVal[iAllB,iStock]+sens*orders['quantity'][newIndex[iOrderB]]*dayPrice
                                fundPMV[iAllB,iStock]=fundPMV[iAllB,iStock]+sens*orders['quantity'][newIndex[iOrderB]]*dayPrice-sens*orders['quantity'][newIndex[iOrderB]]*orders['pru'][newIndex[iOrderB]]
                        iOrderDate+=1
        
        """prepare data to export"""
        #Sum the value for the whole portfolio
        sumFundVal=np.sum(fundVal,1)+np.sum(Comp,1)
        sumFundPmv=np.sum(fundPMV,1)+np.sum(Comp,1)
        
        #Basic info at date
        FundValLast=sumFundVal[len(sumFundVal)-1]
        FundPmvLast=sumFundPmv[len(sumFundPmv)-1]
        #define the reporting date vector
        startDate=min(orders['date'])
        reportIndex=invDate>=startDate
        #reportDate=invDate[reportIndex]
        reportFundValue=sumFundVal[reportIndex]
        
        #number of element in the reporting depend on the number of historic    
        weekM=datetime.datetime.now()-datetime.timedelta(days=7)
        weekM=weekM.strftime("%Y-%m-%d")
        
        #monthM=datetime.datetime.now()-datetime.timedelta(days=30)
        #monthM=monthM.strftime("%Y-%m-%d")
        startYear=datetime.datetime.now().strftime("%Y")+"-01-01"
        
        deltALast=sumFundVal[len(invDate)-1]-sumFundVal[len(invDate)-2]
        deltRLast=sumFundVal[len(invDate)-1]/sumFundVal[len(invDate)-2]-1
        d={' ':['last'],'Delta abs':[round(deltALast,2)],'Delta %':[str(round(deltRLast*100,2))+"%"]}
        perfTab=pd.DataFrame(data=d)
        
        if weekM>=startDate:
            weekIndex=invDate>=weekM
            weekVal=sumFundVal[weekIndex]
            deltALast=sumFundVal[len(invDate)-1]-weekVal[0]
            deltRLast=sumFundVal[len(invDate)-1]/weekVal[0]-1
            perfTab.loc[len(perfTab)] = ['week',round(deltALast,2),str(round(deltRLast*100,2))+"%"]
        
        if startYear>=startDate:
            ytdIndex=invDate>=startYear
            ytdVal=sumFundVal[ytdIndex]
            deltALast=sumFundVal[len(invDate)-1]-ytdVal[0]
            deltRLast=sumFundVal[len(invDate)-1]/ytdVal[0]-1
            perfTab.loc[len(perfTab)] = ['YtD',round(deltALast,2),str(round(deltRLast*100,2))+"%"]
            
        deltALast=sumFundVal[len(invDate)-1]-reportFundValue[0]
        deltRLast=sumFundVal[len(invDate)-1]/reportFundValue[0]-1
                             
        perfTab.loc[len(perfTab)] = ['Inception',round(deltALast,2),str(round(deltRLast*100,2))+"%"]
        
        compReport=np.zeros((len(allTickers),4))
        compReport[:,0]=fundComp[len(invDate)-1]
        compReport[:,1]=Comp[0]/compReport[:,0]
        compReport[:,2]=fundVal[len(invDate)-1]/compReport[:,0]
        compReport[:,3]=fundPMV[len(invDate)-1]
        
        d={'tickers': allTickers, 'Number of stocks':compReport[:,0], 'PRU':compReport[:,1], 'Value':compReport[:,2], 'UGL':compReport[:,3]}
        tabReport=pd.DataFrame(data=d)
        #if weekM<startDate:#Less than a week of historical data
        
        """prepare graphs"""
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(nrows=1, ncols=1)
        ax.set_facecolor('#414141')
        fig.patch.set_facecolor('#414141')
        plt.plot(reportFundValue)
        
        fig.savefig('reports/img1.jpg', facecolor='#414141', edgecolor='#414141')
        

        pd.options.display.max_colwidth = 500 #CHoose the max number of characters displayed in the dataframes (for the news)
         
        """write in the template"""
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("reports/template.html")
        template_vars = {"date" : today,
                     "fundVal": FundValLast,
                     "fundPmv": FundPmvLast,
                     "FundHist":perfTab.to_html(),
                     "Stocks":tabReport.to_html(),
                     "News":allNews.to_html()}
        html_out = template.render(template_vars)
        
        """send the mail"""
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage
        
        me="thomas.laure.work@outlook.fr" #Insert mail adress here
        fromaddr = me
        toaddr ='thomas.laure@me.com'
        msg = MIMEMultipart('related')
        msg['From'] = me
        msg['To'] = toaddr
        msg['Subject'] = "Daily portfolio reporting "+today
        msg.preamble = 'Daily Updated'
        
        #msgAlternative = MIMEMultipart('alternative')
        #msg.attach(msgAlternative)
        
        #msgText = MIMEText('This is the alternative plain text message.')
        #msgAlternative.attach(msgText)
    
        msgText=MIMEText(html_out, 'html')
        msg.attach(msgText)
        
        #Add graph
        fp = open('reports/img1.jpg', 'rb')
        msgImage = MIMEImage(fp.read())
        fp.close()
        
        # Define the image's ID as referenced above
        msgImage.add_header('Content-ID', '<image1>')
        msg.attach(msgImage)
         
        server = smtplib.SMTP('Smtp.live.com', 587) #Depend on your mail server
        server.starttls()
        server.login(me, "MPSI2010tlau") #Add your email account password
        text = msg.as_string()
        server.sendmail(fromaddr, toaddr, text)
        server.quit()

def menu():

    print('Menu :')
    print('1. restart all')
    print('2. add order')
    print('3. load past prices')
    print('4. run')
    choice=input('selection : ')
    if choice=='1':
        restart_all()
    elif choice=='2':
        add_order()
    elif choice=='3':
        import_past_prices()
    elif choice=='4':
        loop_job()
    elif choice=='exit':
        print('process ended')
    else:
        menu()

if __name__ == '__main__':
    menu()