"""
This script needs to be run on an aws instance and it will generate instances,
load_balancers, v2_load_balancers, autoscaling_groups json files
"""
import boto3
import datetime
import json

def get_aws_data_for_region(region):
    """
    Fetching aws data using boto3 and the credentials and config details stored in
    .aws file and writing it into respective json files
    """
    try:
        # Using boto3 to get ec2
        ec2_response = boto3.client("ec2",region_name=region)

        # Using boto3 to get elb
        elb_response = boto3.client("elb",region_name=region)

        # Using boto3 to get elb_v2
        elbv2_response = boto3.client("elbv2",region_name=region)

        # Using boto3 to get asg
        asg_response = boto3.client("autoscaling",region_name=region)

        # Using boto3 to get sts
        sts_response = boto3.client("sts",region_name=region)

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

        # Getting a map of instance_id to load_balancer_name for v1_load_balancers
        instance_to_v1_load_balancer_map = instance_to_v1_load_balancers_map(load_balancers)

        # Getting a map of instance_id to load_balancer_name for v2_load_balancers
        instance_to_v2_load_balancer_map = instance_to_v2_load_balancers_map(v2_load_balancers,elbv2_response)

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

        spot_instances = []
        # Extracting all spot instances from ec2_instances
        for ec2_instance in ec2_instances['Reservations']:
            for ec2i in ec2_instance['Instances']:
                if ec2i.get('InstanceLifecycle') == 'spot':
                    spot_instances.append(ec2_instance)
    
        # Stores the instances into instances.json
        if (ec2_instances["Reservations"] and len(ec2_instances["Reservations"])):
            instances_file = open("instances.json","a+")
            create_json_file(
                instances_file,
                ec2_instances,
                "Reservations",
                "instances",
                account_id,
                region
            )
            instances_file.close()

        # Storing all spot_instances into a file
        if (spot_instances is not None and len(spot_instances)):
            spot_instances_file = open("spot_instances.json","a+")
            for spot_instance in spot_instances:
                create_json_file(
                    spot_instances_file,
                    spot_instance,
                    "Instances",
                    "instances",
                    account_id,
                    region
                )
            spot_instances_file.close()

        # Stores the reserved instances into reservations.json
        if (ec2_reserved_instances["ReservedInstances"] and len(ec2_reserved_instances["ReservedInstances"])):
            reservations_file = open("reservations.json","a+")
            create_json_file(
                reservations_file,
                ec2_reserved_instances,
                "ReservedInstances",
                "reservations",
                account_id,
                region
            )
            reservations_file.close()

        # Stores v1_load_balancers into load_balancers.json
        if (load_balancers["LoadBalancerDescriptions"] and len(load_balancers["LoadBalancerDescriptions"])):
            load_balancers_file = open("load_balancers.json","a+")
            create_json_file_for_load_balancers(
                load_balancers_file,
                load_balancers,
                "LoadBalancerDescriptions",
                "load_balancers",
                "elb",
                account_id,
                region
            )
            load_balancers_file.close()

        # Stores v2_load_balancers into v2_load_balancers.json
        if (v2_load_balancers["LoadBalancers"] and len(v2_load_balancers["LoadBalancers"])):
            v2_load_balancers_file = open("v2_load_balancers.json","a+")
            create_json_file_for_load_balancers(
                v2_load_balancers_file,
                v2_load_balancers,
                "LoadBalancers",
                "load_balancers",
                "elbv2",
                account_id,
                region
            )
            v2_load_balancers_file.close()

        # Stores all asg_groups into autoscaling_groups.json
        if (asg_groups["AutoScalingGroups"] and len(asg_groups["AutoScalingGroups"])):
            asg_file = open("autoscaling_groups.json","a+")
            create_json_file(
                asg_file,
                asg_groups,
                "AutoScalingGroups",
                "autoscaling_groups",
                account_id,
                region
            )
            asg_file.close()

    except Exception as custom_error:
        print(custom_error)

def instance_to_v1_load_balancers_map(load_balancers):
    """
    Returns a dictionary of instance_id to v1_load_balancer_name
    of all instances under v1 load balancers
    Parameters : 
    load_balancers - list of v1 load balancers
    """
    instance_to_v1_load_balancer_map = {}
    for load_balancer in load_balancers["LoadBalancerDescriptions"]:
        for instance in load_balancer['Instances']:
            list_of_load_balancer_names = instance_to_v1_load_balancer_map.get(instance["InstanceId"])
            if list_of_load_balancer_names is None:
                list_of_load_balancer_names = []
                list_of_load_balancer_names.append(load_balancer["LoadBalancerName"])
                instance_to_v1_load_balancer_map[instance["InstanceId"]] = list_of_load_balancer_names
            else:
                list_of_load_balancer_names.append(load_balancer["LoadBalancerName"])
                instance_to_v1_load_balancer_map[instance["InstanceId"]] = list_of_load_balancer_names
    return instance_to_v1_load_balancer_map

def instance_to_v2_load_balancers_map(v2_load_balancers, elbv2_response):
    """
    Returns a dictionary of instance_id to v2_load_balancer_name
    of all instances under v2 load balancers
    Parameters :
    v2_load_balancers - list of v2 load balancers
    """
    instance_to_v2_load_balancer_map = {}
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
                if target_health['TargetHealth']['State'] == 'healthy':
                    list_of_v2_load_balancer_names = instance_to_v2_load_balancer_map.get(
                        target_health["Target"]["Id"]
                        )
                    if list_of_v2_load_balancer_names is None:
                        list_of_v2_load_balancer_names = []
                        list_of_v2_load_balancer_names.append(load_balancer_name)
                        instance_to_v2_load_balancer_map[target_health["Target"]["Id"]] = list_of_v2_load_balancer_names
                    else:
                        list_of_v2_load_balancer_names.append(load_balancer_name)
                        instance_to_v2_load_balancer_map[target_health["Target"]["Id"]] = list_of_v2_load_balancer_names
    return instance_to_v2_load_balancer_map

def create_json_file(file_name, dictionary, key, field, account_id, region):
    """
    This will accept the parameters and create the json files
    """
    data = {}
    data["account_id"] = account_id
    data["region"] = region
    data[field] = dictionary[key]
    json_data = json.dumps(data, default = myconverter)
    file_name.write(json_data)

def create_json_file_for_load_balancers(file_name, dictionary, key, field, version, account_id, region):
    """
    """
    data = {}
    data["account_id"] = account_id
    data["region"] = region
    data[field] = dictionary[key]
    data["version"] = version
    json_data = json.dumps(data, default = myconverter)
    file_name.write(json_data)
    

def fetch_data():
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
            "us-west-2"
        )

        # Getting all AWS regions
        regions = ec2_regions.describe_regions()
        for region in regions["Regions"]:
            print("For region "+region["RegionName"])
            get_aws_data_for_region(
                region=region["RegionName"]
                )
        print("File executed successfully")

    except Exception as error:
        print(error)

# To handle the date cannot be serialized error
def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

fetch_data()
