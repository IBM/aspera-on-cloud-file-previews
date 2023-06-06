# File Preview

Generates a preview on the user files (videos, images, and PDFs) triggered by s3 upload. You can find a list of supported extensions in `./previews/file_formats.yml`. This repository contains instructions and configurations to create AWS Lambda Functions deployed using Docker Images.

## Disclaimer

To enable the use of the IBM Aspera File Preview, you must build a container image with FFmpeg packaged inside. FFmpeg is a free open-source utility, that is not provided or managed by IBM and is subject to third party’s terms and conditions. FFmpeg contains codecs for encoding and decoding various video coding formats. Certain codecs contained within FFmpeg may be covered by patents and require a license to use. The Dockerfile provided by IBM will enable all codecs in FFMPEG by default; however, you must assess your licensing needs in connection with your use of FFmpeg and adjust which codecs to enable accordingly. IBM makes no warranties or conditions, express or implied, and IBM will have no liability to Client, regarding the FFmpeg utility when used with the Cloud Service.

## Prerequisites

1. [Docker](https://docs.docker.com/engine/install/)
2. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html#getting-started-install-instructions)
    -	An AWS account with permission to create an ECR private repository and push docker images into it.
    - AWS CLI installed and configured with [credentials](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html).
    - In the later steps, you will need to define `aws_access_key`, `aws_secret_key` and `security_token` in the `variables.tf` file under the directory `./terraform-aws/previews`, and which will be used in the `terraform` script.
3. [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
4. `git clone` the repository:
    ```
    $ git clone https://github.com/IBM/aspera-on-cloud-file-previews.git
    ```

## Configuration

The following settings can be adjusted before the installation depending on your use cases:
- Change the value of `preview_duration` inside of `./previews/main_thumb.yml` to increase the duration of a preview for video files.
  * Default value is set to *15* seconds
  * You can extend previews up to *60* seconds (max).
- To add the audio of preview videos set the value of `preview_audio` in the `./previews/main_thumb.yml` directory to `true`.
- There will be 2 instances of File Preview in AWS Lambda, one with high resources that will be used for the `video` preview processing and another with low resources for the `image` thumbnail processing. Depending on the file extension, it will invoke either of them to reduce `costs` of the running AWS Lambda Instances.  In the `./previews-checker/config.yml` and `./previews-filter/config.yml`, you **must** define the name of the two Lambda functions. They must match with the values defined in `./terraform-aws/previews/variables.tf`, and the correlations are
  * `high_resource_lambda_name` -> `function_name_previews_video`
  * `low_resource_lambda_name` -> `function_name_previews_image`

## Installation

Create an AWS ECR private repository (if one does not exist already).
```
$ aws ecr create-repository \
  --repository-name {repo_name} \
  --image-scanning-configuration scanOnPush=true \
  --region {region}
```
Note: `{repo_name}` can be anything, for example. `"previews-terraform"`. Also in later Terraform steps, you will need to modify the `{account_id}`, `{repo_name}` and `{region}` values in the `./terraform-aws/previews/variables.tf` file.

Provide Docker access to push docker images in AWS ECR private repositories.
```
$ aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com
```
The `{account_id}` can be fetched with:
```
$ aws sts get-caller-identity | grep Account
```

###  Build docker images

### - *Previews*

The main core function to generate the previews for the uploaded files.

There are 4 different building arguments for the container to define the *codec* that is going to be used to generate previews for the uploaded videos:
- [X264](https://x264.org/en/) **Under GPL License**
- [Openh264](https://www.openh264.org/) **Under Simplified BSD License**
- [AV1](https://en.wikipedia.org/wiki/AV1) **Open source**
- [VP9](https://en.wikipedia.org/wiki/VP9) **Open source**

These four options are available since the user **has to** make a choice between them, depending if they are willing to pay license fees (x264), comply with some conditions to avoid paying royalty fees (openh264) or just use open source codecs such as vp9 and av1 to be used within File Preview.

The `encoder` can be changed to one of the values in this list: `['vp9', 'av1', 'x264', 'openh264']`. An example command to build the docker image and install vp9 in it would be:
```
$ cd previews && docker build --build-arg encoder=vp9 -t {account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:previews .
```
**Note**: `{repo_name}` has to match the AWS ECR private repository you created previously.

### - *Previews-checker*

Checks existing items in the bucket on a particular path and calls File Preview on each file that does not have a preview.

```
$ cd ../previews-checker && docker build -t {account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:checker .
```

### - *Previews-filter*

This is only used to filter out S3 upload triggers using a low resource lambda by file extensions to reduce the costs in the long run.

```
$ cd ../previews-filter && docker build -t {account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:filter .
```

Push **all** the docker images to your ECR repository
```
$ docker push {account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:previews
$ docker push {account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:checker
$ docker push {account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:filter
```

Next step is using the *terraform* script to install those AWS Lambda functions automatically.

### Terraform

- Update both `aws_secret_key` and `aws_access_key` in `./terraform-aws/previews/variables.tf`. Make sure to use a `security_token` when using [short-term credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-short-term.html). Your account must be able to install the following resources:
  - Bucket
  - IAM roles and policies
  - Lambda functions
- Change variable values as needed in `terraform-aws/previews/variables.tf`
  * Note: `image_uri_previews`, `image_uri_checker` and `image_uri_filter` should match the docker images pushed to your ECR repository in the previous step.
- Initialize a working directory containing Terraform configuration files:
  ```
  $ cd terraform-aws/previews
  $ terraform init
  ```
- The Terraform script will create a new bucket. To import an existing bucket **make sure** the `bucket_names` value in `variables.tf` is properly changed and run (*optional*):
  ```
  ./import.sh
  ```
  Find the `{bucket_names}` for your existing AWS S3 bucket:
  * Sign in to your AWS account, and in the search bar, search for keyword `S3`.
  * In the Buckets list, choose the names of the buckets that you want to select, and use those names as the list for `{bucket_names}`

- Create an execution plan that lets you preview the changes that Terraform plans to make to your infrastructure
  ```
  $ terraform plan
  ```
- Validate the configuration files
  ```
  terraform validate
  ```
- Execute the actions proposed in the Terraform plan
  ```
  terraform apply
  ```

### - *Terraform Script Outcome*

After running ``terraform apply``, it will create the following resources:

- S3 bucket with private access. (If no existing one was provided)
- New IAM Role.
- 4 different Lambda functions:
  - 2 of them will be using the same container for File Preview, the difference between them is the resources allocated, to reduce costs.
  - A filtering function with minimum resources to invoke File Preview on S3 trigger. Again, used to reduce costs.
  - A previews checker that will navigate through a specific path (could be root) on a S3 bucket to generate previews on existing files.
- IAM policies for the new role:
  - `logs:CreateLogGroup`,
    `logs:CreateLogStream`,
    `logs:PutLogEvents` to generate logs.
  - `s3:GetObject`,
    `s3:PutObject`,
    `s3:ListBucket`,
    `s3:GetObjectTagging`,
    `s3:PutObjectTagging`. Necessary to upload, fetch and list files, while also tagging them to know that they're already been processed. Only assigned to the new S3 bucket.
  - `lambda:InvokeAsync`,
    `lambda:InvokeFunction`,
    `lambda:GetFunctionConfiguration`. Needed to invoke a Lambda function. Assigned to both File Preview lambdas.
- AWS S3 trigger for each file uploaded and assigned to the filtering function.

## Usage

Once the installation of everything is completed, please wait for a couple of minutes before uploading or transferring new files.

### - *Previews-checker*

To generate previews for those exisiting files in your s3 bucket use *previews-checker*.

You need to define the following parameters to invoke the AWS Lambda function for `preview-checker`:

- `path`: Location in the bucket where you want to check for previews, and which can also be empty to invoked Lambda function from the bucket root level.

- `bucket`: Bucket name. The associated role should have access to it.

Run the following command to invoke `previews-checker` lambda function with the previously defined parameters:

```
$ aws lambda invoke \
    --function-name {checker_function_name} \
    --invocation-type Event \
    --payload '{ "path": {my_path}, "bucket": {bucket_name} }' \
    --region {region} \
    response.json
```

If for whatever reason the whole previews folder structure or one of its subfolders are deleted, then previews-checker can be used to re-generate previews for those files.

**Optional**: You can delete previews-checker lambda since we will only use it once to generate previews for those existing files. Here is the command to delete the Lambda Function and the Log Group of the preview-check:

```
$ terraform destroy --target aws_cloudwatch_log_group.terraform_log_checker  --target aws_lambda_function.terraform_lambda_checker
```

Delete the docker image from your ECR private repository:

```
$ aws ecr batch-delete-image \
     --repository-name {repo_name} \
     --region {region} \
     --image-ids imageTag=checker
```

## Uninstall

Delete every resource created by Terraform:
```
$ terraform destroy
```
**Note**: In some cases `terraform destroy` will not be able to remove the s3 bucket due to an existing file. If you want to delete your bucket you will need to empty it first.

In order to empty the bucket without deleting it, use `--recursive` on the `rm` command.
```
$ aws s3 rm s3://my_bucket --recursive
```

Then, run ``terraform destroy`` again to delete the bucket.

Remove docker images from the ECR Repository:
```
$ aws ecr batch-delete-image \
     --repository-name {repo_name} \
     --region {region} \
     --image-ids imageTag=[preview|checker|filter]
```

Delete the ECR Repository (*Optional*)
```
$ aws ecr delete-repository \
    --repository-name {repo_name} \
    --force
```

## Known issues

- Extensions: `.mxf` and `.divx` will only be displayed its preview as an image.
- There's something else besides moov atom when piping file bytes.
  - Both .flv and .mpeg extensions don't have moov atom, yet only .flv is able to pipe into ffmpeg.   
