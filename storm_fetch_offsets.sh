#!/bin/bash

set -e

[ -z "$1" -o -z "$2" ] && { echo -e "Usage: $0 CONSUMER_GROUP PARTITIONS [TOPIC]\nTOPIC is required for multitopic consumers"; exit 1; }

CONSUMER_GROUP="$1"
PARTITIONS="$2"
TOPIC="$3"

for n in $(seq 0 $((PARTITIONS-1))); do
   if [ -n "$TOPIC" ]; then
      ZNODE="/$CONSUMER_GROUP/$TOPIC/partition_$n"
   else
      ZNODE="/$CONSUMER_GROUP/partition_$n"
   fi
  echo $ZNODE
  set +e
  zookeepercli -servers localhost:2181 -c get $ZNODE
  [ "$?" != 0 ] && { echo -e "FAILED! You may need to pass topic name for multi-topic topologies\nCommand was : $CMD"; exit 1;}
  set -e
done
