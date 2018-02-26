#! /usr/bin/env ruby
#
# check-burrow-kafka-consumers-status
#
# DESCRIPTION:
# Connect to a burrow instance and pull statuses for all consumers on
# all clusters monitored by burrow.
#
# PARAMETERS:
# -u URL -- URL burrow is listening on (i.e., http://burrow.com:8000/endpoint)
#
# RETURNS:
# - CRITICAL if any consumer is STOP, ERR or STALL
# - WARNING if a consumer is WARN (i.e., falling behind)
# - UNKNOWN if NOTFOUND
# - OK otherwise
#

require 'sensu-plugin/check/cli'
require 'net/http'
require 'json'

class CheckKafkaConsumers  < Sensu::Plugin::Check::CLI

  ERROR_CODES = {
      'NOTFOUND' => :unknown,
      'OK' => :ok,
      'WARN' => :warn,
      'ERR' => :critical,
      'STOP' => :critical,
      'STALL' => :critical,
      'REWIND' => :ok
  }
  ERROR_CODES.default = :unknown

  option :burrow_url,
         description: 'Base burrow url',
         short: '-u URL',
         long: '--url URL'

  option :kafka_consumers,
         description: 'csv of kafka_consumers in kafka_cluster to check lag for',
         short: '-c KAFKA-CONSUMERS',
         long: '--kafka-consumers KAFKA-CONSUMERS',
         proc: proc {|a| a.split(',')},
         default: nil

  option :kafka_cluster,
         description: 'csv of kafka cluster for which consumers have to be checked. Must be same as defined in the burrow.cfg',
         short: '-k KAFKA-CLUSTER',
         long: '--kafka-cluster KAFKA-CLUSTER',
         proc: proc {|a| a.split(',')},
         default: nil

  option :kafka_consumer_regex,
         description: 'regex to match the kafka consumer group name',
         short: '-r KAFKA-CONSUMER-REGEX',
         long: '--kafka-consumer-regex KAFKA-CONSUMER-REGEX',
         default: nil

  def check_consumer(cluster, consumer, http)
    consumers_url = "#{config[:base_uri]}/v2/kafka/#{cluster}/consumer/#{consumer}/status"
    req = Net::HTTP::Get.new(consumers_url)
    res = http.request(req)

    consumer_status = JSON.parse(res.body)
    return consumer_status['status']['status']
  end

  def check_cluster(cluster, http)
    consumers = {}
    consumer_results = {}
    if config[:kafka_consumers]
      consumers['consumers'] = config[:kafka_consumers]
    else
      consumers_url = "#{config[:base_uri]}/v2/kafka/#{cluster}/consumer"
      req = Net::HTTP::Get.new(consumers_url)
      res = http.request(req)
      consumers = JSON.parse(res.body)
      if consumers['error']
        return false
      end
    end
    re = /#{config[:kafka_consumer_regex]}/
    consumers['consumers'].each do|consumer|
      if config[:kafka_consumer_regex] and not re =~ consumer
        next
      else
        result = check_consumer(cluster, consumer, http)
        consumer_results[consumer] = result
      end
    end
    return consumer_results
  end

  def run
    uri = URI.parse(config[:burrow_url])
    config[:host] = uri.host
    config[:port] = uri.port
    config[:request_uri] = uri.request_uri
    config[:ssl] = uri.scheme == 'https'

    http = Net::HTTP.new(config[:host], config[:port], nil, nil)
    clusters_url = "#{config[:base_uri]}/v2/kafka"
    # get the set of clusters monitored by burrow
    if config[:kafka_cluster]
     clusters = config[:kafka_cluster]
    else
      req =  Net::HTTP::Get.new(clusters_url)
      res = http.request(req)
      clusters = JSON.parse(res.body)['clusters']
    end
    cluster_results = {}

    # pull down the status of all consumers in the clusters
    aggregates = {}
    aggregates.default = 0

    clusters.each do |cluster|
      consumer_results = check_cluster(cluster, http)
      consumer_results.each do |_, result|
        aggregates[ERROR_CODES[result]] += 1
      end
      cluster_results[cluster] = consumer_results.select {|k,v| v != "OK"}
    end

    pretty_results = JSON.pretty_generate(cluster_results)
    if aggregates[:critical] > 0
      critical("consumer in error: #{pretty_results}")
    elsif aggregates[:warn] > 0
      critical("consumer lagging: #{pretty_results}")
    elsif aggregates[:unknown] > 0
      unknown("consumer check failed: #{pretty_results}")
    else
      ok("consumer check ok: #{pretty_results}")
    end
  end
end
