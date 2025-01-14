"""
This script accepts the AWS Access Key, AWS Secret Access Key and name of an output file as input
and stores the details of the instances, load_balancers, auto scaling groups, reservations into a 
file specified by the user
"""

import boto3
import argparse
import sys
import json
import datetime

def get_default_aws_details():
    """
    Fetching aws data using boto3 and the credentials and config details stored in
    .aws file and writing it into respective json files
    """
    try:
        # Using boto3 to get ec2
        ec2_response = boto3.client("ec2")

        # Using boto3 to get elb
        elb_response = boto3.client("elb")

        # Using boto3 to get elb_v2
        elbv2_response = boto3.client("elbv2")

        # Using boto3 to get asg
        asg_response = boto3.client("autoscaling")

        # Using boto3 to get sts
        sts_response = boto3.client("sts")

        # Get current session using boto3 and then use that to get region
        session = boto3.session.Session()
        region = session.region_name

        # Get aws_account_id from sts
        account_id = sts_response.get_caller_identity()["Account"]

        # Extracting all the instances and reserved instances from the response
        if ec2_response is not None:
            ec2_instances = ec2_response.describe_instances()
            ec2_reserved_instances = ec2_response.describe_reserved_instances()
        else:
            ec2_instances = None
            ec2_reserved_instances = None

        # Extracting all the v1 load_balancers from the response
        if elb_response is not None:
            load_balancers = elb_response.describe_load_balancers()
        else:
            load_balancers = None

        # Extracting all the v2 load_balancers from the response
        if elbv2_response is not None:
            v2_load_balancers = elbv2_response.describe_load_balancers()
        else:
            v2_load_balancers = None

        # Extracting all asg groups
        if asg_response is not None:
            asg_groups = asg_response.describe_auto_scaling_groups()
        else:
            asg_groups = None

        instance_to_v1_load_balancer_map = {}
        # Creating a map of instance_id to load_balancer_name for v1_load_balancer
        if load_balancers is not None:
            for load_balancer in load_balancers["LoadBalancerDescriptions"]:
                for instance in load_balancer['Instances']:
                    instance_to_v1_load_balancer_map[instance["InstanceId"]] = load_balancer["LoadBalancerName"]
                    

        instance_to_v2_load_balancer_map = {}
        # Creating a map of instance_id to load_balancer_name for v2_load_balancer
        if v2_load_balancers is not None:
            for elbv2_lb in v2_load_balancers["LoadBalancers"]:
                load_balancer_arn = elbv2_lb['LoadBalancerArn']
                load_balancer_name = elbv2_lb["LoadBalancerName"]
                target_groups = elbv2_response.describe_target_groups(
                    LoadBalancerArn=load_balancer_arn
                )
                if target_groups is None:
                    continue
                for target_group in target_groups["TargetGroups"]:
                    target_group_arn = target_group['TargetGroupArn']

                    target_healths = elbv2_response.describe_target_health(
                        TargetGroupArn=target_group_arn
                    )
                    if target_healths is None:
                        continue
                    for target_health in target_healths["TargetHealthDescriptions"]:
                        instance_to_v2_load_balancer_map[target_health["Target"]["Id"]] = load_balancer_name

        for ec2_instance in ec2_instances['Reservations']:
            for ec2i in ec2_instance["Instances"]:
                id = ec2i["InstanceId"]
                lb_v1 = instance_to_v1_load_balancer_map.get(id)
                lb_v2 = instance_to_v2_load_balancer_map.get(id)
                if lb_v1 is not None:
                    ec2i["LoadBalancerName"] = lb_v1
                elif lb_v2 is not None:
                    ec2i["LoadBalancerName"] = lb_v2
                else:
                    ec2i["LoadBalancerName"] = None
        
        data = {}
        # Stores instances into instances.json file
        if ec2_instances["Reservations"] and len(ec2_instances["Reservations"]):
            instances_file = open("instances.json","w+")
            data["account_id"] = account_id
            data["region"] = region
            data["instances"] = ec2_instances["Reservations"]
            json_data = json.dumps(data, default = myconverter)
            instances_file.write(json_data)
            instances_file.close()
        
        data = {}
        # Stores reserved instances into reservations.json file
        if (ec2_reserved_instances["ReservedInstances"] and len(ec2_reserved_instances["ReservedInstances"])):
            reservations_file = open("reservations.json","w+")
            data["account_id"] = account_id
            data["region"] = region
            data["reservations"] = ec2_reserved_instances["ReservedInstances"]
            json_data = json.dumps(data, default = myconverter)
            reservations_file.write(json_data)
            reservations_file.close()

        data = {}        
        # Stores v1_load_balancers into load_balancers.json
        if (load_balancers["LoadBalancerDescriptions"] and len(load_balancers["LoadBalancerDescriptions"])):
            load_balancers_file = open("load_balancers.json","w+")
            data["account_id"] = account_id
            data["region"] = region
            data["version"] = "elb"
            data["load_balancers"] = load_balancers["LoadBalancerDescriptions"]
            json_data = json.dumps(data, default = myconverter)
            load_balancers_file.write(json_data)
            load_balancers_file.close()

        data = {}
        # Stores v2_load_balancers into v2_load_balancers.json
        if (v2_load_balancers["LoadBalancers"] and len(v2_load_balancers["LoadBalancers"])):
            v2_load_balancers_file = open("v2_load_balancers.json","w+")
            data["account_id"] = account_id
            data["region"] = region
            data["version"] = "elbv2"
            data["load_balancers"] = v2_load_balancers["LoadBalancers"]
            json_data = json.dumps(data, default = myconverter)
            v2_load_balancers_file.write(json_data)
            v2_load_balancers_file.close()

        data = {}
        # Stores all asg_groups into autoscaling_groups.json
        if (asg_groups["AutoScalingGroups"] and len(asg_groups["AutoScalingGroups"])):
            asg_file = open("autoscaling_groups.json","w+")
            data["account_id"] = account_id
            data["region"] = region
            data["autoscaling_groups"] = asg_groups["AutoScalingGroups"]
            json_data = json.dumps(data, default = myconverter)
            asg_file.write(json_data)
            asg_file.close()
        
        print("File executed successfully")

    except Exception as custom_error:
        print(custom_error)


def get_specified_aws_details_for_region(access_key_id, secret_access_key, region):
    """
    Fetching aws data using boto3 and the access_key_id and secret_access_key
    passed by the user and writing it into respective json file
    Parameters:
    access_key_id - AWS access key id
    secret_access_key - AWS secret access key
    region - AWS region to fetch the data from
    """
    try:
        # Using boto3 to get ec2
        ec2_response = boto3.client(
            "ec2",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
            )

        # Using boto3 to get elb
        elb_response = boto3.client(
            "elb",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
            )
        
        # Using boto3 to get elb_v2
        elbv2_response = boto3.client(
            "elbv2",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
            )

        # Using boto3 to get asg
        asg_response = boto3.client(
            "autoscaling",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
            )

        # Using boto3 to get sts
        sts_response = boto3.client(
            "sts",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
            )

        # Get aws_account_id from sts
        account_id = sts_response.get_caller_identity()["Account"]

        # Extracting all the instances and reserved instances from the response
        if ec2_response is not None:
            ec2_instances = ec2_response.describe_instances()
            ec2_reserved_instances = ec2_response.describe_reserved_instances()
        else:
            ec2_instances = None
            ec2_reserved_instances = None

        # Extracting all the v1 load_balancers from the response
        if elb_response is not None:
            load_balancers = elb_response.describe_load_balancers()
        else:
            load_balancers = None

        # Extracting all the v2 load_balancers from the response
        if elbv2_response is not None:
            v2_load_balancers = elbv2_response.describe_load_balancers()
        else:
            v2_load_balancers = None

        # Extracting all asg groups
        if asg_response is not None:
            asg_groups = asg_response.describe_auto_scaling_groups()
        else:
            asg_groups = None

        instance_to_v1_load_balancer_map = {}
        # Creating a map of instance_id to load_balancer_name for v1_load_balancer
        if load_balancers is not None:
            for load_balancer in load_balancers["LoadBalancerDescriptions"]:
                for instance in load_balancer['Instances']:
                    instance_to_v1_load_balancer_map[instance["InstanceId"]] = load_balancer["LoadBalancerName"]

        instance_to_v2_load_balancer_map = {}
        # Creating a map of instance_id to load_balancer_name for v2_load_balancer
        if v2_load_balancers is not None:
            for elbv2_lb in v2_load_balancers["LoadBalancers"]:
                load_balancer_arn = elbv2_lb['LoadBalancerArn']
                load_balancer_name = elbv2_lb["LoadBalancerName"]
                target_groups = elbv2_response.describe_target_groups(
                    LoadBalancerArn=load_balancer_arn
                )
                if target_groups is None:
                    continue
                for target_group in target_groups["TargetGroups"]:
                    target_group_arn = target_group['TargetGroupArn']

                    target_healths = elbv2_response.describe_target_health(
                        TargetGroupArn=target_group_arn
                    )
                    if target_healths is None:
                        continue
                    for target_health in target_healths["TargetHealthDescriptions"]:
                        instance_to_v2_load_balancer_map[target_health["Target"]["Id"]] = load_balancer_name


        for ec2_instance in ec2_instances['Reservations']:
            for ec2i in ec2_instance["Instances"]:
                id = ec2i["InstanceId"]
                lb_v1 = instance_to_v1_load_balancer_map.get(id)
                lb_v2 = instance_to_v2_load_balancer_map.get(id)
                if lb_v1 is not None:
                    ec2i["LoadBalancerName"] = lb_v1
                elif lb_v2 is not None:
                    ec2i["LoadBalancerName"] = lb_v2
                else:
                    ec2i["LoadBalancerName"] = None

        data = {}
        # Stores instances into instances.json file
        if ec2_instances["Reservations"] and len(ec2_instances["Reservations"]):
            instances_file = open("instances.json","a+")
            data["account_id"] = account_id
            data["region"] = region
            data["instances"] = ec2_instances["Reservations"]
            json_data = json.dumps(data, default = myconverter)
            instances_file.write(json_data)
            instances_file.close()
        
        data = {}
        # Stores reserved instances into reservations.json file
        if (ec2_reserved_instances["ReservedInstances"] and len(ec2_reserved_instances["ReservedInstances"])):
            reservations_file = open("reservations.json","a+")
            data["account_id"] = account_id
            data["region"] = region
            data["reservations"] = ec2_reserved_instances["ReservedInstances"]
            json_data = json.dumps(data, default = myconverter)
            reservations_file.write(json_data)
            reservations_file.close()
                
        data = {}
        # Stores v1_load_balancers into load_balancers.json
        if (load_balancers["LoadBalancerDescriptions"] and len(load_balancers["LoadBalancerDescriptions"])):
            load_balancers_file = open("load_balancers.json","a+")
            data["account_id"] = account_id
            data["region"] = region
            data["version"] = "elb"
            data["load_balancers"] = load_balancers["LoadBalancerDescriptions"]
            json_data = json.dumps(data, default = myconverter)
            load_balancers_file.write(json_data)
            load_balancers_file.close()

        data = {}
        # Stores v2_load_balancers into v2_load_balancers.json
        if (v2_load_balancers["LoadBalancers"] and len(v2_load_balancers["LoadBalancers"])):
            v2_load_balancers_file = open("v2_load_balancers.json","a+")
            data["account_id"] = account_id
            data["region"] = region
            data["version"] = "elbv2"
            data["load_balancers"] = v2_load_balancers["LoadBalancers"]
            json_data = json.dumps(data, default = myconverter)
            v2_load_balancers_file.write(json_data)
            v2_load_balancers_file.close()

        data = {}
        # Stores all asg_groups into autoscaling_groups.json
        if (asg_groups["AutoScalingGroups"] and len(asg_groups["AutoScalingGroups"])):
            asg_file = open("autoscaling_groups.json","a+")
            data["account_id"] = account_id
            data["region"] = region
            data["autoscaling_groups"] = asg_groups["AutoScalingGroups"]
            json_data = json.dumps(data, default = myconverter)
            asg_file.write(json_data)
            asg_file.close()

    except Exception as custom_error:
        print(custom_error)

def get_specified_aws_details(access_key_id, secret_access_key):
    """
    This function is called when the user does not pass the region
    as an argument and subsequently the inventory is fetched from all
    aws regions and stored into a file
    Parameters:
    access_key_id - AWS access key id
    secret_access_key - AWS secret access key
    """
    try:
        ec2_regions = boto3.client(
            "ec2",
            "us-west-2",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )

        # Getting all AWS regions
        regions = ec2_regions.describe_regions()
        for region in regions["Regions"]:
            print("For region "+region["RegionName"])
            get_specified_aws_details_for_region(
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                region=region["RegionName"]
                )

        print("File executed successfully")

    except Exception as error:
        print(error)

# To handle the date cannot be serialized error
def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

# Initializing the parser
PARSER = argparse.ArgumentParser()

# Adding parameters
PARSER.add_argument("--accesskeyid", help="AWS Access Key")
PARSER.add_argument("--secretaccesskey", help="AWS Secret Access key")
PARSER.add_argument("--region", help="Enter region")

# Parse the arguments
ARGS = PARSER.parse_args()

# Extracting the access key id
access_key_id = ARGS.accesskeyid

# Extracting the secret access key
secret_access_key =ARGS.secretaccesskey

# Extracting the region
region = ARGS.region

if access_key_id is None or secret_access_key is None:
    get_default_aws_details()

elif region is not None:
    get_specified_aws_details_for_region(access_key_id, secret_access_key, region)

else:
    get_specified_aws_details(access_key_id, secret_access_key)
