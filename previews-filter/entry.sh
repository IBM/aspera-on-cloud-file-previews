#!/bin/sh
if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
  exec /bin/proxy $@
else
  exec /usr/local/bin/python -m awslambdaric "main__.main"
fi