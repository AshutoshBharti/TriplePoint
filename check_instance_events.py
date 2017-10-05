#!/usr/bin/env python2
import boto.ec2
import argparse
import sys


regions = [
    'us-west-1',
    'us-east-1',
    'us-west-2',
    'eu-west-1',
    'ap-southeast-1'
    ]


def connect_to_ec2(reg, id, key):
    try:
        conn = boto.ec2.connect_to_region(
                reg,
                aws_access_key_id=id,
                aws_secret_access_key=key
                )
        return conn
    except Exception, e:
        print "Exception occoured : {}".format(e)
        sys.exit(3)


def get_instance_info(region, id, key):
    instance_info = {}
    for reg in regions:
        conn = connect_to_ec2(reg, id, key)
        reservations = conn.get_all_instances()
        for res in reservations:
            for instance in res.instances:
                iid = str(instance.id)
                tag = instance.tags.get("env", "Unknown")
                host = instance.tags.get("Name", "Unknown")
                instance_info[iid] = [tag, host]
    return instance_info


def get_events(region, id, key):
    events = {}
    try:
        for reg in regions:
            conn = connect_to_ec2(reg, id, key)
            all_status = conn.get_all_instance_status()
            for status in all_status:
                if status.events:
                    iid = status.id
                    for event in status.events:
                        events[iid] = {}
                        events[iid]['code'] = str(event.code)
                        events[iid]['description'] = str(event.description)
                        events[iid]['not_before'] = str(event.not_before)
                        events[iid]['not_after'] = str(event.not_after)
        return events
    except Exception, e:
        print "Exception occoured in {} : {}".format(sys.argv[0], e)
        sys.exit(3)


def main():
    schd_instance = {}
    parser = argparse.ArgumentParser(
        description='Check scheduled events for any aws instances')
    parser.add_argument(
            '-i',
            '--id',
            help="Amazon id",
            required=True)
    parser.add_argument(
            '-k',
            '--key',
            help="Amazon secret key",
            required=True)
    args = parser.parse_args()
    instance_info = get_instance_info(regions, args.id, args.key)
    schd_instance = get_events(regions, args.id, args.key)
    rc = 0
    if schd_instance:
        for instance_id, event in schd_instance.iteritems():
            if event['not_before'] != "None":
                event_schedule = "Starts on : " + event['not_before']
            elif event['not_after'] != "None":
                event_schedule = "Finishes on : " + event['not_after']
            else:
                event_schedule = ("Starts on : " + event['not_before'] + "and Finishes on : " + event['not_after'])
            if not event['description'].startswith('[Completed]'):
                print "Instance : {} ({}/{}) has scheduled event : {} ( {} ) {}" .format(
                        instance_info[instance_id][1],
                        instance_id,
                        instance_info[instance_id][0],
                        event['code'],
                        event['description'],
                        event_schedule)
                rc = 2
        sys.exit(rc)
    else:
        sys.exit(rc)


if __name__ == "__main__":
    main()
