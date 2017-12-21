#!/usr/bin/env python

import sys
import boto3
import datetime
import argparse

parser = argparse.ArgumentParser(description='collect cloudwatch metric for a resource and alert on it',
                                 epilog='https://boto3.readthedocs.io/en/latest/reference/services/cloudwatch.html#CloudWatch.Client.get_metric_statistics',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-r', '--region',
                    default='us-east-1',
                    help='region where cloudwatch metrics are stored')

parser.add_argument('-n', '--namespace',
                    required=True, type=str,
                    help='namespace to check for, e.g. AWS/CloudFront')

parser.add_argument('-m', '--metric-name',
                    required=True,
                    type=str,
                    help='metric to collect, e.g. 4xxErrorRate')

parser.add_argument('-d', '--dimensions',
                    action='append',
                    type=str,
                    help='dimensions for the metric, e.g DistributionId=E18QJ2SFFU30CQ,Region=Global')

parser.add_argument('-s', '--statistics',
                    choices=['Average', 'Sum', 'SampleCount', 'Maximum', 'Minimum'],
                    help='The metric statistics, other than percentile')

parser.add_argument('-u', '--unit',
                    choices=['Seconds', 'Microseconds', 'Milliseconds', 'Bytes', 'Kilobytes', 'Megabytes', 'Gigabytes',
                             'Terabytes', 'Bits', 'Kilobits', 'Megabits', 'Gigabits', 'Terabits', 'Percent', 'Count'
                             'Bytes/Second', 'Kilobytes/Second', 'Megabytes/Second', 'Gigabytes/Second',
                             'Terabytes/Second', 'Bits/Second', 'Kilobits/Second', 'Megabits/Second', 'Gigabits/Second',
                             'Terabits/Second', 'Count/Second', None],
                    help='Cloudwatch metric unit')

parser.add_argument('-st', '--start-time',
                    type=str,
                    help='time stamp that determines the first data point to return, must be in UTC, '
                         'Format DD/MM/YY HH:MM eg 18/12/17 07:52')

parser.add_argument('-et', '--end-time',
                    type=str,
                    help='time stamp that determines the last data point to return, must be in UTC, '
                         'Format DD/MM/YY HH:MM eg 18/12/17 07:52')

parser.add_argument('-p', '--period',
                    default=60,
                    type=int,
                    help='the granularity in seconds, '
                         'If the StartTime parameter specifies a time stamp that is greater than 3 hours ago, '
                         'you must specify the period as follows or no data points in that time range is returned: '
                         'Start time between 3 hours and 15 days ago - Use a multiple of 60 seconds (1 minute) '
                         'Start time between 15 and 63 days ago - Use a multiple of 300 seconds (5 minutes) '
                         'Start time greater than 63 days ago - Use a multiple of 3600 seconds (1 hour)')

parser.add_argument('-w', '--warning',
                    type=float,
                    help='warning threshold')

parser.add_argument('-c', '--critical',
                    type=float,
                    help='critical threshold')

parser.add_argument('-pm', '--print-metric',
                    default=False,
                    type=bool,
                    help='if TRUE will print the metrics in format: Timestamp: metric_value')

args = parser.parse_args()

if args.namespace == 'AWS/CloudFront':
    dim = [{'Name': 'Region', 'Value': 'Global'}]
else:
    dim = []

if args.start_time:
    stime = datetime.datetime.strptime(args.start_time, "%d/%m/%y %H:%M")
else:
    stime = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)

if args.end_time:
    etime = datetime.datetime.strptime(args.end_time, "%d/%m/%y %H:%M")
else:
    etime = datetime.datetime.utcnow()

for entry in args.dimensions:
    j = entry.split("=")
    dim.append({'Name': j[0], 'Value': j[1]})


def get_metric():
    result = {}
    cw = boto3.client('cloudwatch', region_name=args.region)
    try:
        metric = cw.get_metric_statistics(Namespace=args.namespace,
                                          MetricName=args.metric_name,
                                          Dimensions=dim,
                                          StartTime=stime,
                                          EndTime=etime,
                                          Period=args.period,
                                          Statistics=[args.statistics])
        for data in metric['Datapoints']:
            result.update({"{}".format(data['Timestamp']): data[args.statistics]})
        return result
    except Exception, e:
        print e


def print_metrics():
    result = get_metric()
    for key in sorted(result):
       print "%s: %s" % (key, result[key])


def main():
    """
    The script's default behaviour is to return one datapoint corresponding to the metric for the last minute only.
    For any other behaviour --start-time and --end-time must be used.
    Default granularity is 60 seconds. Check --help before using any other granularity.

    When --print-metric is TRUE, it also prints the metrics in the format Timestamp: metric_value.
    """
    if args.print_metric:
        print_metrics()

    result = get_metric()
    last_metric_value = result[sorted(result.keys())[-1]]

    if args.critical and last_metric_value >= args.critical:
        print "{}: {} more than the specified critical threshold".format(args.metric_name, last_metric_value)
        sys.exit(2)
    elif args.warning and last_metric_value >= args.warning:
        print "{}: {} more than the specified warning threshold".format(args.metric_name, last_metric_value)
        sys.exit(1)
    else:
        print "{}: {} OK".format(args.metric_name, last_metric_value)


if __name__ == "__main__":
    main()
