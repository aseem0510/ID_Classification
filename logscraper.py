import pymongo
import datetime
import time
import pytz
url="mongodb://localhost:27017/"

url_string = f"mongodb://my-user:my-password@a54db3bede3864330a228f68c68f2379-1179598598.us-west-2.elb.amazonaws.com:27017/my-database"

myclient = pymongo.MongoClient(url)
print(myclient)

mydb = myclient["my-database"]
print(mydb.list_collection_names())
mycol = mydb["id-classification-logs"]
print(mycol)
print(mydb.list_collection_names())

lineno=0
while True: 
    
    file1 = open(r"D:\idclassification\id.log", "r") 
    logs=file1.readlines()
    
    n=len(logs) 
    lineno=4
    
    curtime=datetime.datetime.now(tz=pytz.UTC)
    prevtime=datetime.datetime.now(tz=pytz.UTC)-datetime.timedelta(minutes=5)
    print(prevtime)
    print("started scraping")
    for i in range(lineno,n,2):
        
        print("reading line no",i)
        values=logs[i].split(' ')
        
        resptime=datetime.datetime.fromisoformat(str(values[0].split(':')[-1])+" "+str(values[1]))
        response=values[-1]
        # cardno = values[-2] 
        image_from_url =values[-3]
        print(resptime, image_from_url)
        
        #x = mycol.insert_one(mydict)
        if resptime>=prevtime:
            mydict = { "datetime": resptime,   "image_from_url": image_from_url,"response":response}

            x = mycol.insert_one(mydict)
            print("inserting",x)
    
    x = mycol.find()
    time.sleep(5*60)
    print("found col",x)
    
