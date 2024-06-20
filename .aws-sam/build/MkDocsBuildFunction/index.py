import json
import subprocess
import os
import shutil
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    # Get S3 bucket name from environment variable
    bucket_name = os.environ['S3_BUCKET']

    # Determine the directory for building the MkDocs site
    build_dir = "/tmp/build"

    # Install MkDocs if not already present
    try:
        import mkdocs  # Check if mkdocs is installed
    except ImportError:
        subprocess.check_call(["python3.11", "-m", "pip", "install", "-t",  build_dir, "mkdocs"]) # Install to tmp dir
    

    # Update the environment's path to include our new site-packages dir:
    updated_path = os.environ['PATH'] + f":{build_dir}"
    os.environ['PATH'] = updated_path

    # Build the MkDocs site
    subprocess.check_call(["mkdocs", "build", "-d", build_dir])

    # Upload to S3, handling the 'site/' prefix correctly and removing old objects
    s3 = boto3.client('s3', region_name='us-east-1', endpoint_url='http://localhost:4566')
    
    # Remove existing objects
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        for obj in response.get('Contents', []):
            s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
    except ClientError as e:
        print(f"Error deleting objects from S3: {e}")

    # Upload new objects
    for root, dirs, files in os.walk(build_dir):
        for filename in files:
            local_path = os.path.join(root, filename)
            s3_key = local_path.replace(build_dir + "/", "") # Construct the S3 key
            s3.upload_file(local_path, bucket_name, s3_key)
            print(f"Uploaded: {s3_key}")

    # Clean up the build directory
    shutil.rmtree(build_dir)
