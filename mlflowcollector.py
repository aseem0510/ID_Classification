import pymongo
import datetime
import json
from urllib.parse import quote 
import concurrent.futures
import mlflow
import mlflow.sklearn
import time
from mlflow.tracking import MlflowClient
import pytz
import re

def aggregatedata(model_name,desired_model,experiment_id):
    
    print("started logging ",model_name )
    mlflow.set_tracking_uri(
    "/root/logs/"
    )
    
    try:
        experiment_id = mlflow.create_experiment(model_name)
    except Exception as e:
        pass
    
    #experiment = mlflow.get_experiment(experiment_id)
    #mlflow.set_backend_store_uri("/home/supriya/WORK/Signzy/Astra/mlflowtutorals/modellogs/mlruns")
    
    print("artifact store : ", mlflow.get_artifact_uri())
    params = {"alpha": 0.5, "l1_ratio": 0.01}
    
    db_connection = desired_model.get("db_connection", {})
    db_host = db_connection.get("db_host", "a728b149150f84d0ba1838e85013c22a-99557889.us-west-2.elb.amazonaws.com")
    db_port = db_connection.get("db_port", "27017")
    db_name = db_connection.get("db_name", "my-database")
    db_driver = db_connection.get("db_driver", "mongodb")
    db_user = db_connection.get("db_user", "my-user")
    db_password = db_connection.get("db_password", "my-password")
    collecton_name_dest=db_connection.get("collection_name_dest", "id-classificationlogsummary")
    collecton_name_source=db_connection.get("collection_name_source", "id-classification-logs")
    collecton_name_source_store =db_connection.get("collection_name_source_store", "id-classificatioingposurls")

    time_metrics = desired_model.get("time_metrics", {})
    group_by = time_metrics.get("groupby","m")
    no_of_units = time_metrics.get("no_of",5)
    url="mongodb://localhost:27017/"
    url_string = url
    myclient = pymongo.MongoClient(url_string)
    mydb = myclient[db_name]
    mycol_src = mydb[collecton_name_source]
    mycol_dest = mydb[collecton_name_dest]
    mycol_src_store = mydb[collecton_name_source_store]
    
    print(type(no_of_units))
    no_of_units=int(no_of_units)
    
    if group_by=="m":
        units_of_time=no_of_units 
    elif group_by=="h":
        units_of_time=no_of_units*60 
    elif group_by=="d":
        units_of_time=no_of_units*24*60
    
    
    while True:
    
        todate=datetime.datetime.now(tz=pytz.UTC)
        fromdate=datetime.datetime.now(tz=pytz.UTC)-datetime.timedelta(minutes=units_of_time)
        print(fromdate,todate)
    
        #print(todate,type(todate))
        time_check_pipeline = [
            {"$match": {"datetime": {"$gte": fromdate,
                    "$lte": todate},
                        }
             }
        ]
        print(mycol_src)
        time_check_data = list(
                mycol_src.aggregate(time_check_pipeline))
        print(time_check_data)
        no_of_records=len(time_check_data)
    
        print(model_name,"----->",no_of_records)
        
        # matching threshold
        match_thres = 0.1
        
        # variables for positive, negative and error cases
        positive_cases=0
        negative_cases=0
        no_of_errors=0
        thresh_0_20=0
        thresh_20_80=0
        thresh_80_100=0
        ratio_neg_pos=0
        
        # looping through no. of records for every 5 min
        for i in range(no_of_records):
            
            # check whether response is string type or not 
            try:
                
                temp = float(time_check_data[i]["response"]) 
        
                # checking response value with match_thres and storing negative cases into collection
                if temp < match_thres:
                    negative_cases+=1 
                    
                    dic={}
                    dic['url']=time_check_data[i]['image_from_url']
                    dic['response']=time_check_data[i]['response']
                    
                    mycol_src_store.insert_one(dic)
                    
                else:
                    positive_cases+=1 

            except:
                no_of_errors+=1
            
            
            thresh=temp*100
    
            if thresh>0 and thresh<=20:
                thresh_0_20+=1 
            elif thresh>20 and thresh<=80:
                thresh_20_80+=1 
            else:
                thresh_80_100+=1 

            ratio_neg_pos = negative_cases / positive_cases
            
        # dict which is storing analysis of log for every 5 min
        mydict = {"fromdate": fromdate, "todate": todate, "positive_cases": positive_cases, 
                  "negative_cases": negative_cases, "frequency of error": no_of_errors, 
                  "probabilities_0-20": thresh_0_20, "probabilities_21-80" : thresh_20_80, 
                  "probabilities_81-100": thresh_80_100, "ratio_neg_pos": ratio_neg_pos}
        
        if positive_cases>0 or negative_cases>0 or no_of_errors>0:
    
            # storing analysis into destination collection
            mycol_dest.insert_one(mydict)

            print("record inserted successfully")

            # sending data to UI
            with mlflow.start_run(nested=True):
                mlflow.log_param("todate", str(todate))
                mlflow.log_param("fromdate", str(fromdate))
                mlflow.log_param("model name",model_name)
                mlflow.log_param("frequency of positive predictions", positive_cases)
                mlflow.log_param("frequency of negative predictions", negative_cases)
                mlflow.log_param("frequency of error",no_of_errors)
    
        time.sleep(units_of_time*60)
         

#url="mongodb://localhost:27017/"
with open('config.json', 'rb') as fin:
    
        deployment_config = json.loads(fin.read())
        default_model = deployment_config.get(
        "models", {})
    
        models=list(default_model.keys())
        activated_models=[] 

for i in models:
    flag=default_model.get(i,0)
    if flag==1:
        activated_models.append(i) 
        
environment_specs = deployment_config.get("environment_specs", {})
with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(activated_models)
        ) as executor:
            future_notes = []
            exp=0
            
            for model in activated_models:
                future_notes.append(
                    executor.submit(
                        aggregatedata,
                        model_name=model,
                        desired_model= environment_specs.get(model, {}),
                        experiment_id=exp
                    )
                )
                exp+=1

            for future in concurrent.futures.as_completed(future_notes):
                 
                try:
                    output = future.result()
                    print("Stopped service")
                except Exception as e:
                    
                    print("Error Occured",e)
        
        