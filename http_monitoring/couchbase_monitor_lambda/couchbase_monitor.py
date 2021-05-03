# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Licensed under the MIT-0 License. See the LICENSE accompanying this file
# for the specific language governing permissions and limitations under
# the License.

import base64
import boto3
import json
import logging
import urllib.request

from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')
secret_manager = boto3.client('secretsmanager')


def handler(event, context):
    logger.info('request: %s', json.dumps(event))

    cluster_credentials = get_cluster_credentials_secret(event['cluster_secret'])
    auth = create_auth_value(cluster_credentials['username'], cluster_credentials['password'])
    metric_data = []

    cluster_base_url = 'http://{}:{}/'.format(event['host'], event['port'])
    logger.info('will get stats for cluster <%s>', cluster_base_url)

    cluster_monitor_response = get_monitoring_details(cluster_base_url + '/pools/default', auth=auth)
    cluster_name = cluster_monitor_response['clusterName']
    nodes = len(cluster_monitor_response['nodes'])
    healthy_nodes = len([node for node in cluster_monitor_response['nodes'] if 'healthy' == node['status']])

    metric_data.append(create_cluster_metric('HealthyNodes', healthy_nodes, cluster_name, 'None'))
    metric_data.append(create_cluster_metric('NonHealthyNodes', nodes - healthy_nodes, cluster_name, 'None'))

    for node in cluster_monitor_response['nodes']:
        metric_data.append(create_cluster_node_metric(
            'Ops', node['interestingStats']['ops'],
            cluster_name, node['hostname'], node['nodeUUID'], 'None'))

    if 'buckets' in event:
        buckets = event['buckets']
    else:
        buckets = []

    logger.info('will also get stats for buckets <%s>', ' '.join(buckets))

    for bucket in buckets:
        bucket_monitor_response = get_monitoring_details(
            cluster_base_url + '/pools/default/buckets/{}/stats'.format(bucket), auth=auth)
        metric_data.append(
            create_bucket_metric('DiskDrain', bucket_monitor_response['op']['samples']['ep_queue_size'],
                                 cluster_name, bucket, 'None'))
        metric_data.append(
            create_bucket_metric('KeyCacheMisses', bucket_monitor_response['op']['samples']['ep_cache_miss_rate'],
                                 cluster_name, bucket, 'None'))
        metric_data.append(
            create_bucket_metric('Operations', bucket_monitor_response['op']['samples']['ops'],
                                 cluster_name, bucket, 'None'))
        metric_data.append(
            create_bucket_metric('Gets', bucket_monitor_response['op']['samples']['cmd_get'],
                                 cluster_name, bucket, 'None'))
        metric_data.append(
            create_bucket_metric('Sets', bucket_monitor_response['op']['samples']['cmd_set'],
                                 cluster_name, bucket, 'None'))

    cloudwatch.put_metric_data(MetricData=metric_data, Namespace='Couchbase')

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/json'
        },
        'body': {
            'metricsPublished': len(metric_data)
        }
    }


def create_cluster_metric(metric_name, metric_value, dim_cluster_name, unit):
    return {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'Cluster',
                'Value': dim_cluster_name  # For cluster level metrics we add cluster name as a dimension
            },
        ],
        'Unit': unit,
        'Value': metric_value,
        'StorageResolution': 60,  # This is a low resolution metrics as we have minute granuality data point
    }


def create_cluster_node_metric(metric_name, metric_value,
                               dim_cluster_name, dim_node_hostname, dim_node_id, unit):
    return {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'Cluster',
                'Value': dim_cluster_name  # For cluster level metrics we add cluster name as a dimension
            },
            {
                'Name': 'NodeHostName',
                'Value': dim_node_hostname
            },
            {
                'Name': 'NodeId',
                'Value': dim_node_id
            }
        ],
        'Unit': unit,
        'Value': metric_value,
        'StorageResolution': 60,  # This is a low resolution metrics as we have minute granularity data point
    }


def create_bucket_metric(metric_name, metric_values, dim_cluster_name, dim_bucket, unit):
    return {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'Cluster',
                'Value': dim_cluster_name  # For cluster level metrics we add cluster name as a dimension
            },
            {
                'Name': 'vBucket',
                'Value': dim_bucket  # For bucket level metrics we add bucket name as a dimension
            },
        ],
        'Unit': unit,
        'Values': metric_values,
        'StorageResolution': 1,  # This is a high resolution metrics as we have seconds granularity data point
    }


def get_cluster_credentials_secret(secret_name):
    try:
        get_secret_value_response = secret_manager.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        return json.loads(get_secret_value_response['SecretString'])


def create_auth_value(username, password):
    string = '%s:%s' % (username, password)
    return base64.standard_b64encode(string.encode('utf-8'))


def get_monitoring_details(url, auth):
    request = urllib.request.Request(
        url=url,
        headers={'Accept': 'application/json'},
        method='GET')
    request.add_header("Authorization", "Basic %s" % auth.decode('utf-8'))
    u = urllib.request.urlopen(request, timeout=2)
    return json.loads(u.read())