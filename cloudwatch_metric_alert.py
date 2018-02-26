#!/usr/bin/env python
# Author: Ashutosh Bharti <ashutosh@helpshift.com>

import sys
import boto3
import datetime
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(
        epilog='https://boto3.readthedocs.io/en/latest/reference/services/cloudwatch.html#CloudWatch.Client.get_metric_statistics',
        description='Alert on cloudwatch metrics by specifying thresholds'
                    'The scripts default behaviour is to return one datapoint corresponding to the metric for the '
                    'last minute only. For any other behaviour --start-time and --end-time must be specified.'
                    'Default granularity is 60 seconds. Check --help before using any other granularity. '
                    'When --print-metric is TRUE, it also prints the metrics in the format, Timestamp: metric_value',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-r', '--region', default='us-east-1', help='region where cloudwatch metrics are stored')

    parser.add_argument('-n', '--namespace', required=True, type=str,
                        help='namespace to check for, e.g. AWS/CloudFront, AWS/EC2, AWS/S3 etc')

    parser.add_argument('-m', '--metric-name', required=True, type=str, help='metric to alert on, e.g. 4xxErrorRate')

    parser.add_argument('-d', '--dimensions', action='append', type=str,
                        help='dimensions for the metric, use -d to add more dimensions '
                             'e.g -d DistributionId=E18QJ2SFFU30CQ -d Region=Global')

    parser.add_argument('-s', '--statistics', choices=['Average', 'Sum', 'SampleCount', 'Maximum', 'Minimum'],
                        help='The metric statistics, other than percentile')

    parser.add_argument('-u', '--unit',
                        choices=['Seconds', 'Microseconds', 'Milliseconds', 'Bytes', 'Kilobytes', 'Megabytes',
                                 'Gigabytes', 'Terabytes', 'Bits', 'Kilobits', 'Megabits', 'Gigabits', 'Terabits',
                                 'Percent', 'Count', 'Bytes/Second', 'Kilobytes/Second', 'Megabytes/Second',
                                 'Gigabytes/Second', 'Terabytes/Second', 'Bits/Second', 'Kilobits/Second',
                                 'Megabits/Second', 'Gigabits/Second', 'Terabits/Second', 'Count/Second'],
                        help='Cloudwatch metric unit')

    parser.add_argument('-st', '--start-time', type=int, default=60,
                        help='time duration in seconds since when metrics are needed')

    parser.add_argument('-et', '--end-time', type=int, default=0,
                        help='time duration in seconds till when metrics are needed')

    parser.add_argument('-p', '--period', default=60, type=int,
                        help='the granularity in seconds, '
                             'If the StartTime parameter specifies a time stamp that is greater than 3 hours ago, '
                             'you must specify the period as follows or no data points in that time range is returned: '
                             'Start time between 3 hours and 15 days ago - Use a multiple of 60 seconds (1 minute) '
                             'Start time between 15 and 63 days ago - Use a multiple of 300 seconds (5 minutes) '
                             'Start time greater than 63 days ago - Use a multiple of 3600 seconds (1 hour)')

    parser.add_argument('-w', '--warning', type=float, help='warning threshold')

    parser.add_argument('-c', '--critical', required=True, type=float, help='critical threshold')

    parser.add_argument('-pm', '--print-metric', default=False, type=bool,
                        help='if TRUE will print the metrics in format: Timestamp: metric_value')

    parser.add_argument('-ak', '--access-key', required=True,
                        help='aws access key for boto3 client to connect to cloudwatch')

    parser.add_argument('-sk', '--secret-key', required=True,
                        help='aws secret key for boto3 client to connect to cloudwatch')

    args = parser.parse_args()
    return args


def get_metric(namespace, metric_name, dimensions, start_time, end_time, period, statistics, print_metric,
               region, access_key, secret_key):
    result = {}
    try:
        cw = boto3.client('cloudwatch',
                          region,
                          aws_access_key_id=access_key,
                          aws_secret_access_key=secret_key)

        metric = cw.get_metric_statistics(Namespace=namespace,
                                          MetricName=metric_name,
                                          Dimensions=dimensions,
                                          StartTime=start_time,
                                          EndTime=end_time,
                                          Period=period,
                                          Statistics=statistics)
        for data in metric['Datapoints']:
            data_point = dict([(data['Timestamp'], data[statistics[0]])])
            result.update(data_point)
        if print_metric:
            for key in sorted(result):
                print "%s: %s" % (key, result[key])
        return result
    except Exception, e:
        print e
        sys.exit(3)


def main():
    args = parse_arguments()

    namespace_dimensions = {'AWS/CloudFront': [{'Name': 'Region', 'Value': 'Global'}]}
    try:
        dim = namespace_dimensions[args.namespace]
    except KeyError:
        dim = []

    stime = datetime.datetime.utcnow() - datetime.timedelta(seconds=args.start_time)
    etime = datetime.datetime.utcnow() - datetime.timedelta(seconds=args.end_time)

    for entry in args.dimensions:
        name, value = entry.split("=")
        dim.append({'Name': name, 'Value': value})

    result = get_metric(args.namespace, args.metric_name, dim, stime, etime, args.period, [args.statistics], args.print_metric,
                        args.region, args.access_key, args.secret_key)
    last_metric_value = result[result.keys()[-1]]

    if args.critical and last_metric_value >= args.critical:
        print "{}: value {} more than the specified critical threshold {}".format(args.metric_name, last_metric_value, args.critical)
        sys.exit(2)
    elif args.warning and last_metric_value >= args.warning:
        print "{}: value {} more than the specified warning threshold {}".format(args.metric_name, last_metric_value, args.warning)
        sys.exit(1)
    else:
        print "{}: value {} within threshold {} OK".format(args.metric_name, last_metric_value, args.warning or args.critical)


if __name__ == "__main__":
    main()
