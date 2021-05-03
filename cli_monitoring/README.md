<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. SPDX-License-Identifier: MIT-0 -->

## CLI monitoring

The scripts here are an example of supporting scripts that use Couchbase `HTTP` endpoints and `CBStats` tool 
to forward detailed monitoring to Amazon CloudWatch.

The scripts are intended to be installed on a node. 
To achieve this in an automated way you *can* consider the following options

* If you're deploying Couchbase on Amazon EC2 instances directly
  * Use an [AMI (Amazon Machine Images)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html) 
    that contains such scripts. You can build your AMIs with [EC2 Image Builder](https://aws.amazon.com/image-builder/)
  * Deploy scripts to your instances with [AWS CodeDeploy](https://aws.amazon.com/codedeploy/)
  * Automate installation from [Amazon S3](https://aws.amazon.com/s3/) as part of an instance configuration using 
    [AWS Systems Manager](https://aws.amazon.com/systems-manager/) or
    [AWS OpsWorks](https://aws.amazon.com/opsworks/)
* When deployed using containers you can bake those scripts in your container image

## Prerequisites
1. `python 2` environment to execute the scripts
1. AWS CLI environment and AWS credentials.
    1. Amazon Linux2 images running on EC2 instance have the AWS CLI preinstalled. 
       The instance will utilize instance profile to obtain credentials
   1. To install AWS CLI and provide credentials on other environments, [check the following guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) 
1. The AWS credentials are allowed to have permissions to put Amazon CloudWatch metrics, a sample policy can be
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "Couchbase"
        }
      },
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*",
      "Effect": "Allow"
    }
  ]
}
```

## Get Started

1. Install scripts using any of the above mention ways
1. Script `couchbase_monitor_cli.py` accepts parameters 
   1. couchbase username
   1. couchbase password
   1. buckets to monitor
1. the shell script `metrics-cloudwatch.sh` is an example of calling the Python script and also accepts 
   the above mentioned parameters.
1. You can use host schedule mechanism to call the script every desired time. Below is an example of crontab config.
   ```shell
   * * * * * /opt/aws/couchbase-monitor/metrics-cloudwatch.sh user password bucket1,bucket2
   ```