#! /usr/bin/env ruby
#
#   kafka-burrow-metrics
#
# DESCRIPTION:
# Gathers kafka topic and consumer metrics from burrow
#
# PARAMETERS:
# -u URL -- URL burrow is listening on (i.e., http://burrow.com:8000/endpoint)
#
# RETURNS:
#  Consumer lag metrics in Graphite format :
#  <kafka_cluster>.<topic>.<consumer_name>.lag.<partition> <lag>
#  <kafka_cluster>.<topic>.<consumer_name>.status <burrow_status>
#

require 'sensu-plugin/metric/cli'
require 'net/http'
require 'json'

class KafkaBurrowMetrics < Sensu::Plugin::Metric::CLI::Graphite

  option :burrow_url,
          required: true,
          description: 'Burrow base url',
          short: '-u URL',
          long: '--url URL'

  STATUS_CODES = {
    'NOTFOUND' => 0,
    'OK' => 0,
    'WARN' => 1,
    'ERR' => 2,
    'STOP' => 2,
    'STALL' => 2,
    'REWIND' => 0
  }
  STATUS_CODES.default = 0

  @timestamp = Time.now.to_i
  @http = nil

  def make_request(url)
    req = Net::HTTP::Get.new(url)
    res = @http.request(req)
    res_json = JSON.parse(res.body)
    if res_json['error']
      print "Error in response for #{url}, response was #{res_json}"
      critical
    end
    return res_json
  end

  def consumer_metrics(cluster, consumer)
    consumer_lag_url = "#{config[:request_uri]}v2/kafka/#{cluster}/consumer/#{consumer}/lag"
    res = make_request(consumer_lag_url)

    # Used after the loop for burrow status metric
    topic_name = nil
    # Lag for every partition
    res['status']['partitions'].each do |partition|
      topic_name = partition['topic']
      metric = [cluster, topic_name, consumer, 'lag', partition['partition']].join('.')
      output(metric, partition['end']['lag'], @timestamp)
    end

    # Burrow lag status for the topic
    if topic_name
      metric = [cluster, topic_name, consumer, 'status'].join('.')
      output(metric, STATUS_CODES[res['status']['status']], @timestamp)
    end
  end

  def cluster_metrics(cluster)
    consumers_url = "#{config[:request_uri]}v2/kafka/#{cluster}/consumer"
    res = make_request(consumers_url)
    res['consumers'].each do |consumer|
      consumer_metrics(cluster, consumer)
    end
  end

  def run
    uri = URI.parse(config[:burrow_url])
    config[:host] = uri.host
    config[:port] = uri.port
    config[:request_uri] = uri.request_uri
    @http = Net::HTTP.new(config[:host], config[:port], nil, nil)

    clusters_url = "#{config[:request_uri]}v2/kafka"
    res = make_request(clusters_url)
    res['clusters'].each do |cluster|
      cluster_metrics(cluster)
    end
    ok
  end
end
