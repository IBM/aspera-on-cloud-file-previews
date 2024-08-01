variable "aws_access_key" {
  default = ""
}

variable "aws_secret_key" {
  default = ""
}

variable "security_token"{
  default = ""
}

variable "region" {
  default = "us-west-2"
}

variable "timeout" {
  default = 600
}

variable "preview_duration" {
  default = 15
}

variable "preview_audio" {
  default = false
}

variable "timeout_checker" {
  default = 600
}

variable "memory_size_previews_video" {
  default = 7169
}

variable "memory_size_previews_image" {
  default = 2049
}

variable "ephemeral_size_previews" {
  default = 10240
}

variable "memory_size_checker" {
  default = 1024
}

variable "memory_size_min" {
  default = 128
}

variable "ephemeral_size_min" {
  default = 512
}

variable "bucket_names" {
  type = list
  default = ["terraform-preview-maker"]
}

variable "iam_role_name" {
  default = "Preview_Maker_Lambda_Function_Role"
}

variable "policy_name" {
  default = "Preview_Maker_Policy"
}

variable "function_name_previews_video" {
  default = "File_Preview_Video_Processing"
}

variable "function_name_previews_image" {
  default = "File_Preview_Image_Processing"
}

variable "function_name_checker" {
  default = "Previews_Checker_Lambda_Function"
}

variable "function_name_filter" {
  default = "Previews_Filter_Lambda_Function"
}

variable "image_uri_previews" {
  default = "{account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:previews"
}

variable "image_uri_checker" {
  default = "{account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:checker"
}

variable "image_uri_filter"{
  default = "{account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:filter"
}