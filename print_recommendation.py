import json

with open('./recommendation_response.json') as json_file:
    data = json.load(json_file)
    account_id = data["account_id"]
    print()
    print("FOR THE AWS ACCOUNT ID "+account_id)
    savings_by_region = data["savings_by_region"]
    for saving in savings_by_region:
        print("---------------------------------------------------------------------")
        print("IN THE REGION "+saving["region"])
        print()
        for saving_type in saving["savings_by_rule_type"]:
            if saving_type["recommended_type"] == "SPOT":
                print("Convert the following instances to SPOT to save "+saving_type["total_savings"]+" USD ")
                for index,detail in enumerate(saving_type["details"]):
                    print("{}) Instance ID: ".format(index+1)+detail["InstanceId"]+" of type "+detail["InstanceType"])

                print()
            elif saving_type["recommended_type"] == "RESERVATIONS":
                print("RESERVE the following instances to save "+saving_type["total_savings"]+" USD")
                for index,detail in enumerate(saving_type["details"]):
                    print(
                        "{}) ".format(index+1)+
                         detail["RecommendedNumberOfInstancesToPurchase"]+
                         " "+
                         detail["InstanceType"]+
                         " for a period of "+
                         detail["Term"]+
                         " years for the upfront cost of "+
                         detail["UpfrontCost"]
                         )
                print()
        print()