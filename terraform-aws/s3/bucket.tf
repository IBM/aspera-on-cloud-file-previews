resource "aws_s3_bucket" "previews" {
  bucket = "${var.bucket_name}" 
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "private" {
  bucket = aws_s3_bucket.previews.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_arn"{
  value = aws_s3_bucket.previews.arn
}

output "bucket_name"{
  value = "${var.bucket_name}"
}
