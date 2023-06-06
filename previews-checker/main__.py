import json
import boto3
import os
import yaml
import pathlib
from datetime import datetime
from dateutil import parser

client = boto3.client('lambda')

def read_yaml(file):
  with open(file, "r") as stream:
    try:
      return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
      print(exc)
      raise exc
      
def check_preview_tag(tags):
  print(tags)
  for tag in tags:
    if tag["Key"] == 'previews' and tag["Value"] == 'true':
      return True
  return False

def invoke_lambda(name, request):
  client.invoke(
    FunctionName=name,
    InvocationType='Event',
    Payload=json.dumps(request)
  )


def main(event, context):
  s3_client = boto3.client('s3')
  MINIMUM_REMAINING_TIME_MS = 5000
  s3 = boto3.resource('s3')
  last_item = event['marker'] if 'marker' in event else ''
  bucket = event['bucket'] if 'bucket' in event else ''
  path = event['path'] if 'path' in event else "N/A"
  if path == "N/A" or bucket == '':
    raise Exception("Missing required params, either path or bucket")
  my_bucket = s3.Bucket(bucket)
  start_datetime = parser.parse(event['start_time']) if 'start_time' in event else datetime.now()
  skip_words = ['previews/', '.asp-preview'] # Just in case there's a file with the name of preview in it
  script_path = str(pathlib.Path(__file__).parent.resolve())
  formats = read_yaml(f"{script_path}/file_formats.yml")
  config = read_yaml(f"{script_path}/config.yml")
  in_progress = False

  response1 = client.get_function_configuration(FunctionName=config['high_resource_lambda_name'])
  response2 = client.get_function_configuration(FunctionName=config['low_resource_lambda_name'])
  if int(response1['MemorySize']) > int(response2['MemorySize']):
    video_lambda = config['high_resource_lambda_name']
    image_lambda = config['low_resource_lambda_name']
  else:
    video_lambda = config['low_resource_lambda_name']
    image_lambda = config['high_resource_lambda_name']
  

  for my_bucket_object in my_bucket.objects.filter(Prefix=path, Marker=last_item):
    if context.get_remaining_time_in_millis() < MINIMUM_REMAINING_TIME_MS:
      in_progress = True
      break
    last_item = my_bucket_object.key
    if my_bucket_object.last_modified.replace(tzinfo = None) > start_datetime:
      print("Too recent file, skipped: ", my_bucket_object.key)
      continue
    if any(word in my_bucket_object.key for word in skip_words):
      print("Skipped: ", my_bucket_object.key)
      continue
    tags = s3_client.get_object_tagging(
      Bucket=bucket,
      Key=my_bucket_object.key
    )
    print(my_bucket_object)
    print(f"tags: {tags['TagSet']}")
    file_name = os.path.basename(my_bucket_object.key)
    is_video = file_name.lower().endswith(tuple(formats['video']))
    is_image = file_name.lower().endswith(tuple(formats['image']))
    if check_preview_tag(tags["TagSet"]) or (not is_video and not is_image):
      print("Skipped: ", my_bucket_object.key)
      continue
    item = s3.Object(bucket, my_bucket_object.key)
    print(item.content_length)
    new_event = {
      "Records": [{
        "s3":{
          "bucket":{
            "name": bucket
          },
          "object":{
            "key": my_bucket_object.key,
            "size": item.content_length
          }
        }
      }]
    }
    if is_video:
      invoke_lambda(video_lambda, new_event)
      print(f"Invoked video lambda with: {my_bucket_object.key}")
    else:
      print(f"Invoked image lambda with: {my_bucket_object.key}")
      invoke_lambda(image_lambda, new_event)
    print("=====================")
    
  if in_progress:
    print("Timeout approaching and the task is still pending, calling another lambda to finish the job")
    new_event = {
      "bucket": bucket,
      "start_time": start_datetime.isoformat(),
      "marker": last_item,
      "path": path
    }
    invoke_lambda(context.function_name, new_event)
  return {
    'statusCode': 200,
    'body': json.dumps('Hello from Lambda!')
  }
