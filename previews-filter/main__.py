import json
import boto3
import yaml
import pathlib
import urllib.parse
import os

client = boto3.client('lambda')

def read_yaml(file):
  with open(file, "r") as stream:
    try:
      return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
      print(exc)
      raise exc

def invoke_lambda(name, request):
  client.invoke(
    FunctionName=name,
    InvocationType='Event',
    Payload=json.dumps(request)
  )

def get_original_file(s3_path):
  s3_path = s3_path.split("asp-preview/", 1)[1]
  s3_path = os.path.splitext(s3_path)[0]
  return s3_path

def remove_tags(s3, bucket, key):
  try:
    tags = s3.get_object_tagging(
      Bucket=bucket,
      Key=key
    )["TagSet"]
    new_tags = []
    for tag in tags:
      if tag["Key"] == "previews" or tag["Key"] == "previews-location":
        continue
      new_tags.append(tag)
    s3.put_object_tagging(
      Bucket=bucket,
      Key=key,
      Tagging={
        "TagSet": new_tags
      }
    )
    print(f"Removed tags to {key}")
  except Exception as e:
    print(e)

def main(event, context):
  print(event)
  key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
  event_type = event["Records"][0]["eventName"]
  if "ObjectRemoved" in event_type:
    s3 = boto3.client("s3")
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    source_file_name = get_original_file(key)
    remove_tags(s3, bucket, source_file_name)
  else:
    if "previews" in key:
      raise Exception("Preview files are ignored")
    script_path = str(pathlib.Path(__file__).parent.resolve())
    formats = read_yaml(f"{script_path}/file_formats.yml")
    config = read_yaml(f"{script_path}/config.yml")
    is_video = key.lower().endswith(tuple(formats["video"]))
    is_image = key.lower().endswith(tuple(formats["image"]))
    if not is_video and not is_image:
      raise Exception("File extension not supported")

    response1 = client.get_function_configuration(FunctionName=config['high_resource_lambda_name'])
    response2 = client.get_function_configuration(FunctionName=config['low_resource_lambda_name'])
    if int(response1['MemorySize']) > int(response2['MemorySize']):
      video_lambda = config['high_resource_lambda_name']
      image_lambda = config['low_resource_lambda_name']
    else:
      video_lambda = config['low_resource_lambda_name']
      image_lambda = config['high_resource_lambda_name']

    if is_video:
      invoke_lambda(video_lambda, event)
      print(f"Invoked previews video with file: {key}")
    else:
      invoke_lambda(image_lambda, event)
      print(f"Invoked previews image with file: {key}")
  return {
    'statusCode': 200,
    'body': json.dumps('Hello from Lambda!')
  }
