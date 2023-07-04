provider "aws" {
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
  token      = var.security_token
  region     = var.region
}

module "s3" {
  source      = "../s3"
  count       = (length(var.bucket_names))
  bucket_name = var.bucket_names[count.index]
}

locals {
  s3_arn       = [for name in var.bucket_names : "arn:aws:s3:::${name}"]
  s3_policies  = [for name in var.bucket_names : "arn:aws:s3:::${name}/*"]
  s3_resources = concat(local.s3_policies, local.s3_arn)
}

resource "aws_iam_role" "lambda_role" {
  name               = var.iam_role_name
  depends_on    = [module.s3]
  assume_role_policy = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "lambda.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}

EOF

}

resource "aws_lambda_function" "terraform_lambda_video" {
  function_name = var.function_name_previews_video
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  memory_size   = var.memory_size_previews_video
  timeout       = var.timeout
  image_uri     = var.image_uri_previews
  depends_on    = [module.s3]

  ephemeral_storage {
    size = var.ephemeral_size_previews # Min 512 MB and the Max 10240 MB
  }
}

resource "aws_lambda_function" "terraform_lambda_image" {
  function_name = var.function_name_previews_image
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  memory_size   = var.memory_size_previews_image
  timeout       = var.timeout
  image_uri     = var.image_uri_previews
  depends_on   = [module.s3]

  ephemeral_storage {
    size = var.ephemeral_size_previews
  }
}

resource "aws_iam_policy" "iam_policy_for_lambda" {
  name        = var.policy_name
  path        = "/"
  description = "AWS IAM Policy for managing aws lambda role"
  depends_on  = [module.s3]
  policy      = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": [
       "logs:CreateLogGroup",
       "logs:CreateLogStream",
       "logs:PutLogEvents"
     ],
     "Resource": "arn:aws:logs:*:*:*",
     "Effect": "Allow"
   },
   {
    "Action": [
       "s3:GetObject",
       "s3:PutObject",
       "s3:ListBucket",
       "s3:GetObjectTagging",
       "s3:PutObjectTagging"
     ],
     "Resource": ${jsonencode(local.s3_resources)},
     "Effect": "Allow"
   },
   {
    "Action": [
        "lambda:InvokeAsync",
        "lambda:InvokeFunction",
        "lambda:GetFunctionConfiguration"
     ],
     "Resource": ["${aws_lambda_function.terraform_lambda_video.arn}", "${aws_lambda_function.terraform_lambda_image.arn}"],
     "Effect": "Allow"
   }
 ]
}

EOF

}

resource "aws_iam_role_policy_attachment" "attach_iam_policy_to_iam_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_lambda.arn
}

resource "aws_lambda_function" "terraform_lambda_filter" {
  function_name = var.function_name_filter
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  memory_size   = var.memory_size_min
  timeout       = var.timeout
  image_uri     = var.image_uri_filter
  depends_on    = [module.s3]

  ephemeral_storage {
    size = var.ephemeral_size_min
  }

  environment {
    variables = {
      high_resource_lambda_name = aws_lambda_function.terraform_lambda_video.function_name
      low_resource_lambda_name  = aws_lambda_function.terraform_lambda_image.function_name
    }
  }
}

resource "aws_lambda_permission" "allow_bucket_filter" {
  count = (length(local.s3_arn))
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.terraform_lambda_filter.arn
  principal     = "s3.amazonaws.com"
  source_arn    = local.s3_arn[count.index]
  depends_on    = [module.s3]
}

resource "aws_s3_bucket_notification" "preview-trigger" {
  count = (length(var.bucket_names))
  bucket = var.bucket_names[count.index]
  lambda_function {
    lambda_function_arn = aws_lambda_function.terraform_lambda_filter.arn
    id = "${var.bucket_names[count.index]}-create-trigger"
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ""
  }
  lambda_function {
    lambda_function_arn = aws_lambda_function.terraform_lambda_filter.arn
    events              = ["s3:ObjectRemoved:*"]
    id = "${var.bucket_names[count.index]}-delete-trigger"
    filter_prefix       = "previews"
    filter_suffix       = ".asp-location"
  }
  depends_on = [aws_lambda_permission.allow_bucket_filter, aws_lambda_function.terraform_lambda_filter]
}

resource "aws_lambda_function" "terraform_lambda_checker" {
  function_name = var.function_name_checker
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  memory_size   = var.memory_size_checker
  timeout       = var.timeout_checker
  image_uri     = var.image_uri_checker
  depends_on    = [module.s3]

  ephemeral_storage {
    size = var.ephemeral_size_min
  }

  environment {
    variables = {
      high_resource_lambda_name = aws_lambda_function.terraform_lambda_video.function_name
      low_resource_lambda_name  = aws_lambda_function.terraform_lambda_image.function_name
    }
  }
}

resource "aws_cloudwatch_log_group" "terraform_log_video" {
  name = "/aws/lambda/${var.function_name_previews_video}"
  depends_on    = [module.s3]
}

resource "aws_cloudwatch_log_group" "terraform_log_image" {
  name = "/aws/lambda/${var.function_name_previews_image}"
  depends_on    = [module.s3]
}

resource "aws_cloudwatch_log_group" "terraform_log_filter" {
  name = "/aws/lambda/${var.function_name_filter}"
  depends_on    = [module.s3]
}

resource "aws_cloudwatch_log_group" "terraform_log_checker" {
  name = "/aws/lambda/${var.function_name_checker}"
  depends_on    = [module.s3]
}
