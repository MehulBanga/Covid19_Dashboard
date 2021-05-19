from flask import Flask, render_template,session,request,redirect,url_for
from datetime import timedelta
import pandas as pd
import json
import sqlite3
from urllib.request import urlopen

app = Flask(__name__)



app.permanent_session_lifetime= timedelta(days= 13) #same as fb
app.secret_key = "keyyyyy"

#Working with APIs and json
def open(url):
    response = urlopen(url)
    source = response.read()
    js = json.loads(source)
    return js




js=open("https://coronavirus-19-api.herokuapp.com/countries") #Total_summary
#overhead
j= js[0]
Total_cases= j["cases"]
Total_recoveries = j["recovered"]
Death_cases = j["deaths"]
Death_rate = round((Death_cases/Total_cases)*100)
#for active/closed
currently_infected = j["active"]
closed_cases =  Total_cases - currently_infected
cases_today = j['todayCases']
deaths_today = j['todayDeaths']
critical_active = j["critical"]
recovered_closed_cases=Total_recoveries
closed_cases_death_percentage=round((Death_cases/closed_cases)*100)
closed_cases_recovered_percentage = 100 - closed_cases_death_percentage



js1 = open ("https://api.covid19api.com/summary") #countries_info

js2 = open("https://api.rootnet.in/covid19-in/stats/latest") #states_info

js3 = open("https://api.covid19india.org/state_district_wise.json")

#working with Csv files and Pandas:
#loading data from the source
country_df = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/web-data/data/cases_country.csv')

#Data cleaning 
#renamimg the df of column names to lower case
country_df.columns = map(str.lower, country_df.columns)  
#changing country_region to country
country_df = country_df.rename(columns = { 'country_region' : 'country'})
#sorting based on worst case
sorted_country_df = country_df.sort_values('confirmed', ascending = False)
#removing unnecessary columns
final_country_df = sorted_country_df.drop(["last_update", "lat","long_", "people_tested", "uid","people_hospitalized"], axis = 1)

#filtering data for Map plotting
country_confirmed = country_df[["iso3","confirmed"]]
country_codes = country_df["iso3"].values.tolist()
country_names = country_df["country"].values.tolist()
confirmed_list = country_df["confirmed"].values.tolist()

#Changing  data format for map-plot 
#import data format
import os
popdens = os.path.join(app.static_folder,'data','popdens.json')
data_fetch = pd.read_json(popdens)



#Pages

@app.route("/")
@app.route("/totals")
def totals():
    data_for_map =[]
    for i in country_codes:
        try:
            tempdf = data_fetch[data_fetch['code3']==i]
            temp ={}
            temp["code3"]= tempdf["code3"].values[0]
            temp["name"] = tempdf["name"].values[0]
            temp["value"] = confirmed_list[country_codes.index(temp["code3"])]
            temp["code"] = tempdf["code"].values[0]
            data_for_map.append(temp)
        except:
            pass
   
    return render_template("totals.html", total_cases= Total_cases, Total_recoveries = Total_recoveries , Death_cases= Death_cases, Death_rate = Death_rate,critical_active=critical_active, current_active_cases=currently_infected,closed_cases = closed_cases,closed_recovered= Total_recoveries , closed_dead=Death_cases,closed_death_percentage=closed_cases_death_percentage,closed_recovered_percentage=closed_cases_recovered_percentage,cases_today=cases_today,deaths_today=deaths_today,data_for_map=data_for_map )

@app.route("/world")
def world():
    con = sqlite3.connect("covid_19_countries.db")
    cur= con.cursor()
    cur.execute("DROP TABLE IF EXISTS countries")
    
    cur.execute('''CREATE TABLE IF NOT EXISTS countries( rid INTEGER,sr TEXT ,
                name TEXT UNIQUE ,
                confirmed INTEGER ,
                deaths INTEGER,
                recovered INTEGER)''') 
    for i in js1["Countries"]:
        rid= i["TotalDeaths"]
        sr = i["CountryCode"]
        country = i["Country"]
        confirmed = i["TotalConfirmed"]
        deaths = i["TotalDeaths"]
        recovered = i["TotalConfirmed"] - i["TotalDeaths"]
        cur.execute("INSERT OR REPLACE INTO countries(rid,sr,name,confirmed,deaths,recovered) VALUES(?,?,?,?,?,?)" , (rid,sr , country , confirmed , deaths , recovered, ))
    
    con.commit()
    cur.execute("SELECT ROW_NUMBER() OVER(ORDER BY confirmed DESC) AS rid,sr,name,confirmed,deaths,recovered FROM countries")
    countries = cur.fetchall()
    return render_template("world.html",countries = countries )

@app.route("/india",methods=["POST","GET"])
def india():
    #INDIA SUMMARY
    i = js2["data"]["summary"]
    tc = i["total"]
    ri = i["discharged"]
    di = i["deaths"]    
    
    #STATES_STUFF #Table 
    
    con = sqlite3.connect("covid_19_india_states.db")
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS states")
    cur.execute('''CREATE TABLE IF NOT EXISTS states(rid INTEGER,name
                TEXT UNIQUE,
                confirmed INTEGER ,
                deaths INTEGER ,
                recovered INTEGER)''')
    
    #Inserting data about states
    for i in js2["data"]["regional"]:
        state = i["loc"]
        ccs = i["totalConfirmed"]
        ds = i["deaths"]
        rs= i["discharged"]
        rid = i["discharged"]
        cur.execute(" INSERT OR REPLACE INTO states(rid,name, confirmed, deaths, recovered) VALUES(?,?,?,?,?)" , (rid,state , ccs , ds , rs))
    con.commit()
    cur.execute("SELECT ROW_NUMBER() OVER(ORDER BY confirmed DESC) AS rid,name,confirmed,deaths,recovered FROM states ")
    states=cur.fetchall()
    
    #District stuff
    empty_list = []
    for i in js3:
        for cities in js3[i]["districtData"]:
            empty_list.append(cities)
        
    #reading users input
    if request.method == "POST":
        state = request.form["state"]
        city = request.form["city"]
        session.permanent = True
        session["c"] = city
        session["s"]= state
        return redirect(url_for("cityresults"))
    return render_template("india.html" , states = states , total_cases = tc , total_deaths = di , total_recovered = ri, name_states = js3, cities = empty_list )



@app.route("/citysearch")
def cityresults():
    
    state = session["s"]
    city = session["c"]
    i=js3[state]["districtData"][city]
    total_confirmed = i["confirmed"]
    total_dead = i["deceased"]
    total_recovered = i["recovered"]
    return render_template("cityresults.html",total_cases = total_confirmed, Death_cases = total_dead, Total_recoveries = total_recovered, city_name = city, state_name = state )

@app.route("/plots")
def plots(chartID = "chart_ID",chart_type = "scatter"):
    


    
    #Data for Series
    list1 = [] #(x,x_lable,y)
    list2=[]
    for i in range(len(js1["Countries"])):
        list1.append([js1["Countries"][i]["Country"],js1["Countries"][i]["TotalConfirmed"]])
    list1.sort(key = lambda x:x[1],reverse = True)
    for i in range(10):
        list2.append([5*(i+1),list1[i][1]])
    series=[{
        "name": 'Countries',
        'color': 'rgba(223, 83, 83, .5)',
        "data": list2
        }]
    return render_template("test.html",series = series)   
 
'''
@app.route("/home")
def test():
    data_for_map =[]
    for i in country_codes:
        try:
            tempdf = data_fetch[data_fetch['code3']==i]
            temp ={}
            temp["code3"]= tempdf["code3"].values[0]
            temp["name"] = tempdf["name"].values[0]
            temp["value"] = confirmed_list[country_codes.index(temp["code3"])]
            temp["code"] = tempdf["code"].values[0]
            data_for_map.append(temp)
        except:
            pass
    return render_template("hcs.html",data_for_map=data_for_map)
'''
 
@app.errorhandler(404)
def page_not_found(e):
    return "Page Not Found, Try again or Refresh"

if __name__ == "__main__":
    app.run()
    
    

    
    
    
    
    
    
    
    
