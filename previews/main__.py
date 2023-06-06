import datetime
import json
import math
import os
import pathlib
import re
import shlex
import subprocess as sp
import time
import urllib.parse
import uuid
from shlex import quote

import ibm_boto3
import yaml
from ibm_botocore.client import ClientError, Config

if os.environ.get("LAMBDA_TASK_ROOT"):
    import boto3  # For some reason can't find boto3 when using IBM Functions even though it works just fine in AWS
    from botocore.exceptions import ClientError

key = ""
is_downloaded = False
s3 = ""
bucket = ""
provider = ""
uuid_str = ""
cpu_cores = 0

def get_video_duration(file, is_downloaded):
  try:
    if is_downloaded:
      cmd = "/function/bin/ffprobe -v error -show_entries format=duration -of "\
      f"default=noprint_wrappers=1:nokey=1 {file}"
      return float(os.popen(cmd).read())
    
    # ffmpeg doesn't seem to like when the input is just a string with this structure
    cmd = ["/function/bin/ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", \
    "default=noprint_wrappers=1:nokey=1", "-"]
    duration = sp.run(cmd, input=file, capture_output=True)
    return float(duration.stdout)
  except ValueError as e:
    print(e)
    error = "Unable to get video duration, please check file extension"
    export_error(error)

def pdf_thumb(file, output):
  print(f"Creating pdf thumbnail for {output}")
  if is_downloaded:
    os.system(f"convert -size x800 -background white -flatten {file}[0] {output}")
  else:
    cmd = ["convert", "-size", "x800", "-background", "white", "-flatten", "-[0]", f"{output}"]
    sp.run(cmd, input=file)

def image_thumb(file, output):
  print(f"Creating image thumbnail for {output}")
  if is_downloaded:
    cmd = f"convert {file}[0] -auto-orient -thumbnail 800x800\\>"\
      f" -quality 95 +dither -posterize 40 '{output}'; optipng '{output}'"
    os.system(cmd)
  else:
    cmd = ["convert", "-[0]", "-auto-orient", "-thumbnail", "800x800", "-quality", "95", "+dither", "-posterize", "40", f"{output}"]
    cmd2 = ["optipng", f"{output}"]
    sp.run(cmd, input=file)
    sp.run(cmd2)

def txt_thumb(file, output, height):
  cmd = f"convert -size x{height}\\> -background white {file}[0] {output}"
  return os.system()

# Old method to generate a clip, can still be used later on for other cloud providers.
def generate_clip(file, output, is_downloaded, duration, clip_duration, max_mem_size=""):
  time_offset = duration // 2
  encoder = "libsvtav1"
  if os.system("test -e /usr/local/lib/libx264*") == 0:
    encoder = "libx264"
  elif os.system("test -e /usr/local/lib/libopenh264*") == 0:
    encoder = "libopenh264"
  print(f"Generating clip with output: {output} using encoder: {encoder}")
  if is_downloaded:
    cmd = f"/function/bin/ffmpeg -y -ss {time_offset} -t {clip_duration} -i {file} -vf fps=24,scale=1280x720 -b:v 1400k -an -cpu-used -{cpu_cores} -deadline realtime {output}"
    return os.system(cmd)
  cmd = ["/function/bin/ffmpeg", "-y",  "-ss", f"{time_offset}", "-t", f"{clip_duration}", "-i", "-", "-vf", "fps=24,scale=1280x720", "-an", "-cpu-used", f"-{cpu_cores}", "-deadline", "realtime", output]
  sp.run(cmd, input=get_item(max_mem_size))

def generate_clipv2(url, output, clip_duration, preview_audio):
  start = time.time()
  encoder = "libvpx-vp9"
  audio_arg = "-an"
  if os.system("test -e /usr/local/lib/libx264*") == 0:
    encoder = "libx264"
  elif os.system("test -e /usr/local/lib/libopenh264*") == 0:
    encoder = "libopenh264"
  elif os.system("test -e /usr/local/lib/libSvtAv1Enc*") == 0:
    encoder = "libsvtav1"
  print(f"Generating clip with output: {output} using encoder: {encoder}")

  if preview_audio:
    audio_arg = "-b:a 96k"

  cmd = "/function/bin/ffmpeg -y -i \"" + url + f"\" -t {clip_duration} \
  -c:v {encoder} -vf fps=24,scale=1280x720 -b:v 1400k {audio_arg} -cpu-used -{cpu_cores} -deadline realtime {output}"
  command = shlex.split(cmd)
  sp.run(command)
  video_thumb(url, "/tmp/thumb.jpg")
  end = time.time()
  print(end - start, " FINISHED GENERATING A CLIP")

def video_thumb(url, output):
  cmd = "/function/bin/ffmpeg -y -i \"" + url + f"\" -vf 'scale=320:320:force_original_aspect_ratio=decrease' -vframes 1 {output}"
  command = shlex.split(cmd)
  sp.run(command)

def pdf_thumbv2(url, output):
  start = time.time()
  cmd = f"convert -size x800 -background white -flatten {url}[0] {output}"
  command = shlex.split(cmd)
  sp.run(command)
  end = time.time()
  print(end - start, " FINISHED GENERATING A PDF THUMBNAIL")

def image_thumbv2(url, output):
  start = time.time()
  cmd = f"convert {url}[0] -auto-orient -thumbnail 800x800\\>"\
      f" -quality 95 +dither -posterize 40 '{output}'"
  command = shlex.split(cmd)
  sp.run(command)
  # cmd2 = ["optipng", f"{output}"]
  # sp.run(cmd2)
  end = time.time()
  print(end - start, " FINISHED GENERATING A PNG THUMBNAIL")
  
def create_presigned_url_aws(expiration=600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    try:
        response = s3.generate_presigned_url("get_object",
                                                    Params={"Bucket": bucket,
                                                            "Key": key},
                                                    ExpiresIn=expiration)
        # The response contains the presigned URL
        return response
    except ClientError as e:
        print(e)
        export_error(e)
    
def upload_file(file_name, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
      object_name = os.path.basename(file_name)

    # Upload the file
    try:
      start = time.time()
      if provider == "AWS": # Match case is available until Python 3.10
        response = s3.upload_file(file_name, bucket, object_name)
      elif provider == "IBM":
        s3.meta.client.upload_file(file_name, bucket, object_name)
      print(f"Uploaded file: {object_name}")
      end = time.time()
      print(end - start, f"FINISHED UPLOADING: {object_name}")
    except ClientError as e:
        print(e)
        export_error(e)
    return True

def get_item(max_mem_size):
  try:
    print(f"Downloading file data: {key}")
    start = time.time()
    if provider == "AWS":
      fileData = s3.get_object(Bucket=bucket, Key=key, Range="bytes={}-{}".format(0, max_mem_size))["Body"].read()
    elif provider == "IBM":
      fileData = s3.Object(bucket, key).get(Range="bytes={}-{}".format(0, max_mem_size))["Body"].read()
    end = time.time()
    print(end - start, f"FINISHED downloading: {max_mem_size}")
    return fileData
  except Exception as e:
      print(e)
      error = f"Error getting object {key} from bucket {bucket}. Make sure they exist and your bucket is in the same region as this function."
      export_error(error)

def write_file(name, fileData):
  f = open(name, "wb")
  f.write(fileData)
  f.close()
  print(f"Wrote file '{name}' to disk")

def read_yaml(file):
  with open(file, "r") as stream:
    try:
      return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
      print(exc)
      error = f"Couldn't read yml file {file}"
      export_error(error)

def download_file_to_disk(object_name):
  try: 
    start = time.time()
    s3.meta.client.download_file(bucket, key, object_name) if provider == "IBM" else s3.download_file(bucket, key, object_name)
    end = time.time()
    print(end - start, "FINISHED DOWNLOADING TO DISK")
  except Exception as e:
    print(e)
    error = f"Error getting object {key} from bucket {bucket}. Make sure they exist and your bucket is in the same region as this function."
    export_error(error)

def export_error(error):
  data = {
    "file": f"{key}",
    "timestamp": datetime.datetime.now().isoformat(),
    "method": "local disk" if is_downloaded else "pipe",
    "error": f"{error}"
  }
  output_file = "/tmp/error.json"

  with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
  upload_file(output_file, f"previews/{uuid_str}.asp-preview/error.json")
  raise Exception(error)

def set_tags(provider, s3, new_tag):
  try:
    if provider == "IBM":
      s3 = s3.meta.client
    tags = s3.get_object_tagging(
      Bucket=bucket,
      Key=key
    )["TagSet"]
    tag_list = []

    # used to avoid getting an error with repeated tags, useful in testing
    for tag in tags:
      if tag["Key"] == new_tag["Key"]:
        continue
      tag_list.append(tag)
    tag_list.append(new_tag)
    s3.put_object_tagging(
      Bucket=bucket,
      Key=key,
      Tagging={
        "TagSet": tag_list
      }
    )
    print(f"Added tag {new_tag} to {key}")
  except Exception as e:
    print(e)
    error = f"Unable to set tag to file: {key}. Try again later or add it manually."
    export_error(e)

def check_output(preview_file_name, lib):
  if os.system(f"test -e {preview_file_name}") != 0:
    error = f"Couldn't generate preview with file '{preview_file_name}', something went wrong with {lib}."
    export_error(error)

def main(event, context=""):
  print("Received event: " + json.dumps(event, indent=2))
  global key
  global is_downloaded
  global s3
  global bucket
  global provider
  global uuid_str
  global cpu_cores

  cpu_cores = int(os.popen("nproc").read())
  script_path = str(pathlib.Path(__file__).parent.resolve())
  config = read_yaml(f"{script_path}/main_thumb.yml")
  overhead = (1 << 20) * 150
  uuid_str = str(uuid.uuid4())

  if os.environ.get("LAMBDA_TASK_ROOT"):
    s3 = boto3.client("s3")
    provider = "AWS"
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")
    max_disk_size = int(os.popen("df /tmp | awk 'NR > 1 {print $4}'").read()) // 1024 # Gets available disk size in MB from /tmp partition
    max_mem_size = int(os.environ["AWS_LAMBDA_FUNCTION_MEMORY_SIZE"])
    content_length = event["Records"][0]["s3"]["object"]["size"]
    url = create_presigned_url_aws()

  else: # Later on need to check for specific ENV variable in IBM Cloud Functions
    s3 = ibm_boto3.resource("s3",
      ibm_api_key_id = event["cosApiKey"],
      ibm_service_instance_id = event["cosInstanceId"],
      config = Config(signature_version="oauth"),
      endpoint_url = "https://" + event["endpoint"]
    )
    provider = "IBM"
    bucket = event["bucket"]
    key = event["key"]
    max_disk_size = config["ibm_max_disk"]
    max_mem_size = config["ibm_max_memory"]
    content_length = event["notification"]["object_length"]
  if "previews" in key:
    raise Exception("preview files are ignored")

  file_name = os.path.basename(key)
  formats = read_yaml(f"{script_path}/file_formats.yml")
  is_video = file_name.lower().endswith(tuple(formats["video"]))
  is_pdf = file_name.lower().endswith(tuple(formats["pdf"]))
  is_image = file_name.lower().endswith(tuple(formats["image"]))
  if not is_pdf and not is_image and not is_video:
    error = "File extension not supported"
    export_error(error)
  # gets size in GiB with a slight overhead to avoid reaching limits
  max_mem_size = (max_mem_size << 20) // 2 - overhead
  print("Max_mem_size", max_mem_size)
  max_disk_size = (max_disk_size << 20) - overhead
  print("content_length", content_length)

  tmp_path = f"/tmp/{file_name}"
  shellsafe_file = quote(tmp_path)
  path_file = "/tmp/path.txt"

  path_to_file = os.path.splitext(key)[0]
  if is_video:
    preview_duration = int(config["preview_duration"])
    if preview_duration > 60:
      print("Preview duration can't be longer than a minute, setting value to 60")
      preview_duration = 60
    elif preview_duration < 1:
      print("Previews should be at least 1 second long")
      preview_duration = 1
    preview_file_name = "/tmp/preview.mp4"
    if provider == "IBM":
      # Downloads a portion of the file just to check the moov atom
      fileData = get_item((1<<20) * 20)
      print(fileData.find(b"moov"), "MOOV")
      # The moov atom should be at the very beginning of the file, starting at byte 32~, need more files to test this
      if 0 < int(fileData.find(b"moov")) <= 200:
        is_downloaded = False
      elif int(content_length) <= max_disk_size:
        download_file_to_disk(tmp_path)
        fileData = ""
        is_downloaded = True
      else:
        error = "File size is too big, please change the 'moov atom' of the file to the beginning"
        export_error(error)

      duration = get_video_duration(shellsafe_file, True) if is_downloaded else get_video_duration(fileData, False)
      print("video_duration", duration)
      start_clip = time.time()
      if is_downloaded:
        generate_clip(shellsafe_file, preview_file_name, True, duration, config["preview_duration"])
      else:
        clipped_duration = max_mem_size / int(content_length)
        clipped_duration = 1 if clipped_duration > 1 else clipped_duration
        clipped_duration = math.floor(clipped_duration * duration)
        print("Clipped_duration", clipped_duration)
        generate_clip(key, preview_file_name, False, clipped_duration, config["preview_duration"],  max_mem_size)
      end_clip = time.time()
      print(end_clip- start_clip, "FINISHED CREATING A CLIP")
    elif provider == "AWS":
      generate_clipv2(url, preview_file_name, preview_duration, config["preview_audio"])

    check_output(f"{preview_file_name}", "ffmpeg")
    check_output(f"/tmp/thumb.jpg", "ffmpeg")
    upload_file(preview_file_name, f"previews/{uuid_str}.asp-preview/preview.mp4")
    upload_file("/tmp/thumb.jpg", f"previews/{uuid_str}.asp-preview/preview.png")
    # upload_file(s3, preview_file_name, bucket, provider, f"{path_to_file}-previews-{timestamp}-{rnumber}.mp4")
  else:
    preview_file_name = "/tmp/thumbnail.png"
    if provider == "IBM":
      if int(content_length) <= max_mem_size:
        fileData = get_item(max_mem_size)
        is_downloaded = False
      elif int(content_length) <= max_disk_size:
        download_file_to_disk(tmp_path)
        is_downloaded = True
      else:
        error = "File size is too big, please consider increasing memory/disk limits"
        export_error(error)

      if is_pdf:
        pdf_thumb(shellsafe_file, preview_file_name) if is_downloaded else pdf_thumb(fileData, file_name)
      elif is_image:
        image_thumb(shellsafe_file, preview_file_name) if is_downloaded else image_thumb(fileData, file_name)
    elif provider == "AWS":
      if is_pdf:
        pdf_thumbv2(url, preview_file_name)
      elif is_image:
        image_thumbv2(url, preview_file_name)
    check_output(f"{preview_file_name}", "ImageMagick")
    upload_file(preview_file_name, f"previews/{uuid_str}.asp-preview/preview.png")

  write_file(path_file, key.encode())
  set_tags(provider, s3, {"Key": "previews", "Value": "true"}) # Used as a flag in previews-checker
  set_tags(provider, s3, {"Key": "previews-location", "Value": f"previews/{uuid_str}.asp-preview/"}) # Defines the location of the preview
  upload_file(path_file, f"previews/{uuid_str}.asp-preview/preview-path.txt")
  s3.put_object(Bucket=bucket, Key=f"previews/{uuid_str}.asp-preview/{key}.asp-location") # Useful to know the name of original file

  if is_downloaded:
    start = time.time()
    os.remove(f"{tmp_path}")
    print(f"Deleted file: {key} from storage")
    end = time.time()
    print(end - start, "DELETED FILE")

  return {
      "statusCode": 200,
      "body": json.dumps("Hello from Lambda!"),
      "provider": f"{provider}",
      "method": "local disk" if is_downloaded else "pipe"
  }
