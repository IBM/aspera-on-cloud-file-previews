#!/bin/bash

buckets=$(echo $(echo 'jsonencode(var.bucket_names)' | terraform console) | sed 's/\\//g;s/"//g;s/[][]//g' | tr , ' ')
count=0
for bucket_name in $buckets; do
  terraform import 'module.s3'"[$count]"'.aws_s3_bucket.previews' $bucket_name
  (( count++ ))
done
