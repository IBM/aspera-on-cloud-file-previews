import unittest
import pathlib
import os
from unittest import mock
from unittest.mock import patch

file_name = "vid.mpeg"

# Setting the default AWS region environment variable required by the Python SDK boto3
with mock.patch.dict('os.environ', {'AWS_REGION': 'us-west-2', 'LAMBDA_TASK_ROOT': 'true'}, clear=True):
    from main__ import main

def mocked_get_item(max_mem_size):
    script_path = str(pathlib.Path(__file__).parent.parent.parent.parent.resolve())
    with open(f"{script_path}/example-video-files/{file_name}",'rb') as f:
        # f.seek(684684918,1 )
        f.seek(0)
        input_file = f.read()
    f.close()
    return input_file

def mocked_download_file_to_disk(object_name):
    script_path = str(pathlib.Path(__file__).parent.parent.parent.parent.resolve())
    os.system(f"cp {script_path}/example-video-files/{file_name} /tmp/")
    os.system("ls /tmp/")
    return

def mocked_set_tags(provider, s3):
    print("TAGGED")
    return

def mocked_upload_file(file_name, object_name=None):
    return

def generate_clipv2(url, output, clip_duration, size):
    os.system("touch /tmp/preview.webm")
    return

def mocked_check_output(preview_file_name, lib):
    print("Checked file")
    return

def pdf_thumbv2(url, output, height):
    os.system("touch /tmp/preview.png")

def image_thumbv2(url, output, max_size):
    os.system("touch /tmp/preview.png")

def mocked_create_presigned_url_aws(expiration=600):
    return ""

def remove_file(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

def delete_files():
    remove_file("/tmp/preview.webm")
    remove_file("/tmp/path.txt")
    remove_file("/tmp/error.json")



@patch('main__.get_item', side_effect=mocked_get_item)
@patch('main__.download_file_to_disk', side_effect=mocked_download_file_to_disk)
@patch('main__.set_tags', side_effect=mocked_set_tags)
@patch('main__.upload_file', side_effect=mocked_upload_file)
@patch('main__.check_output', side_effect=mocked_check_output)
@patch('main__.create_presigned_url_aws', side_effect=mocked_create_presigned_url_aws)
@patch('main__.generate_clipv2', side_effect=generate_clipv2)
@patch.dict('os.environ', {'AWS_REGION': 'us-west-2', 
                                        'LAMBDA_TASK_ROOT': 'true', 
                                        'AWS_LAMBDA_FUNCTION_MEMORY_SIZE': '2048'}, clear=True)
class GeneratePreviewTest(unittest.TestCase):

    # Test for valid file type (.mpeg)
    def test_valid_file(self, get_item_mock, download_file_to_disk_mock,
     set_tags_mock, upload_file_mock, create_presigned_url_aws_mock, generate_clipv2_mock, check_output_mock):
        global file_name
        file_name = "vid.mpeg"
        response = main(self.s3_upload_event(file_name, 18735828), "")
        expected_response = {
            'statusCode': 200,
            'body': '"Hello from Lambda!"',
            'provider': 'AWS',
            'method': 'pipe'
        }

        self.assertEqual(get_item_mock.call_count, 1)
        self.assertEqual(download_file_to_disk_mock.call_count, 1)
        self.assertEqual(set_tags_mock.call_count, 2)
        self.assertEqual(upload_file_mock.call_count, 3)
        self.assertEqual(response, expected_response)
        self.assertTrue(os.path.isfile("/tmp/preview.webm"))
        self.assertTrue(os.path.isfile("/tmp/path.txt"))
        self.assertTrue(os.path.getsize("/tmp/path.txt") > 0)
        self.assertFalse(os.path.isfile(f"/tmp/{file_name}"))
        print(response)
        delete_files()

    # Test for invalid file type (.asd)
    def test_invalid_file(self, get_item_mock, download_file_to_disk_mock,
     set_tags_mock, upload_file_mock, create_presigned_url_aws_mock, generate_clipv2_mock, check_output_mock):
        global file_name
        file_name = "vid.asd"
        with self.assertRaises(Exception) as context:
            main(self.s3_upload_event(file_name, 0), "")

        self.assertTrue('File extension not supported' in str(context.exception))
        self.assertTrue(os.path.isfile("/tmp/error.json"))
        self.assertTrue(os.path.getsize("/tmp/error.json") > 0)

        self.assertEqual(get_item_mock.call_count, 0)
        self.assertEqual(upload_file_mock.call_count, 1)
        delete_files()

    # test for pipe (unable to do so)

    # # Test for m2v exception with ffprobe
    # def test_ffprobe_exception(self, get_item_mock, download_file_to_disk_mock, set_tags_mock, upload_file_mock):
    #     global file_name
    #     file_name = "vid.m2v"
    #     with self.assertRaises(Exception) as context:
    #         main(self.s3_upload_event(file_name, 0), "")

    #     self.assertTrue('Unable to get video duration, please check file extension' in str(context.exception))
    #     self.assertTrue(os.path.isfile("/tmp/error.json"))
    #     self.assertTrue(os.path.getsize("/tmp/error.json") > 0)

    #     self.assertEqual(get_item_mock.call_count, 1)
    #     self.assertEqual(download_file_to_disk_mock.call_count, 0)
    #     self.assertEqual(upload_file_mock.call_count, 1)
    #     delete_files()

    # Test for previews skip
    def test_name(self, get_item_mock, download_file_to_disk_mock,
     set_tags_mock, upload_file_mock, create_presigned_url_aws_mock, generate_clipv2_mock, check_output_mock):
        global file_name
        file_name = "previews/03a1cc02-0f06-434c-b06b-0587b329f5ec.asp-previews/preview.webm"
        with self.assertRaises(Exception) as context:
            main(self.s3_upload_event(file_name, 0), "")
        self.assertTrue('preview files are ignored' in str(context.exception))

    # def test_generated_files(self, get_item_mock, download_file_to_disk_mock, set_tags_mock, upload_file_mock):
    #     global file_name
    #     file_name = "vid.mpeg"
    #     response = main(self.s3_upload_event(file_name, 18735828), "")
    #     self.assertTrue(os.path.isfile("/tmp/preview.webm"))
    #     self.assertTrue(os.path.isfile("/tmp/path.txt"))
    #     self.assertTrue(os.path.getsize("/tmp/preview.webm") > 0)
    #     self.assertTrue(os.path.getsize("/tmp/path.txt") > 0)
    #     print(response)
    #     delete_files()

    # Mock S3 new file uploaded event
    def s3_upload_event(self, file_name, size):

        return {
            "Records":[
            {
                "eventVersion":"2.1",
                "eventSource":"aws:s3",
                "awsRegion":"us-west-2",
                "eventTime":"2021-06-18T16:03:17.567Z",
                "eventName":"ObjectCreated:Put",
                "userIdentity":{
                    "principalId":"AWS:AIDAI7123123XY"
                },
                "requestParameters":{
                    "sourceIPAddress":"12.21.123.69"
                },
                "responseElements":{
                    "x-amz-request-id":"D104123123BXXE",
                    "x-amz-id-2":"DJH/123123/123/76dtHg7yYQ+LHws0xBUmqUrM5bdW"
                },
                "s3":{
                    "s3SchemaVersion":"1.0",
                    "configurationId":"677496ca-4ead-123-123-123",
                    "bucket":{
                    "name":"my-bucket-name",
                    "ownerIdentity":{
                        "principalId":"A3123123AR5"
                    },
                    "arn":"arn:aws:s3:::my-bucket-name"
                    },
                    "object":{
                    "key":file_name,
                    "size":size,
                    "eTag":"06a83081d2bb215",
                    "sequencer":"0060CCC3C"
                    }
                }
            }
        ]
    }
