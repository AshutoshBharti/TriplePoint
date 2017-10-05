#!/usr/bin/python
# author: Ashutosh Bharti<ashutosh@helpshift.com>
# description: This script checks for the instances without a name or without a tag 'Name'
#              returns their region, id and state

import boto.ec2
import sys
import argparse

regions = [
    'us-west-1',
    'us-east-1',
    'us-west-2',
    'eu-west-1',
    'ap-southeast-1'
    ]

def connect_to_ec2(region, acc_id, key):
  try:
    conn = boto.ec2.connect_to_region(
                region,
                aws_access_key_id=acc_id,
                aws_secret_access_key=key
                )
    return conn
  except Exception, e:
    print "Exception occurred : {}".format(e)
    sys.exit(3)


def  get_instance_without_name(regions, acc_id, key):
  result=[]
  for region in regions:
    conn = connect_to_ec2(region, acc_id, key)
    reservations = conn.get_all_instances()
    for res in reservations:
      for inst in res.instances:
       if 'Name' not in inst.tags or inst.tags['Name']=="":
         result.append((region, inst.id, inst.state))
  return result

def main():
  parser = argparse.ArgumentParser(description='Check for instances without a name or a Name tag')

  parser.add_argument(
            '-i',
            '--acc_id',
            help="AWS access id",
            required=True)

  parser.add_argument(
            '-k',
            '--key',
            help="AWS secret key",
            required=True)

  args = parser.parse_args()

  result = get_instance_without_name(regions, args.acc_id, args.key)

  if len(result) > 0:
    print "Critical: Instances found without Name/Name tag: " + str(result)
    sys.exit(2)
  else:
    print "OK: Every instance in inventory has a Name"
    sys.exit(0)

if __name__ == "__main__":
  main()
