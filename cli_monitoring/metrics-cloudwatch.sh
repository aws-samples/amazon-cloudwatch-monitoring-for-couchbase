#!/bin/bash

#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
EC2_AVAIL_ZONE=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)
EC2_REGION="`echo \"$EC2_AVAIL_ZONE\" | sed 's/[a-z]$//'`"

while getopts ":u:p:b:" opt; do
  case $opt in
  u)
    c_username="$OPTARG"
    ;;
  p)
    c_password="$OPTARG"
    ;;
  b)
    buckets="$OPTARG"
    ;;
  \?)
    echo "Invalid option -$OPTARG" >&2
    ;;
  esac
done

metric_data=$(python couchbase_monitor_cli.py "${c_username}" "${c_password}" "${buckets}" 0>&1)

aws cloudwatch put-metric-data --namespace "Couchbase" --metric-data "${metric_data}" --region "${EC2_REGION}"
