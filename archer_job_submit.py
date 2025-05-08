import json
import os
import argparse
import requests
import base64
import datetime

# This script uploads fastq files to the Archer Analysis server (v7) and submits jobs for analysis

def upload_fastqs(folder, server, headers):

    # used to store aa server paths from uploaded sample files for job submission
    fastq_paths = []

    # first section upload all files in "folder" defined above to the aa server (sequence files there must be paired)
    endpoint = "file-uploads/"
    url = "{}/api/{}".format(server, endpoint)

    # Loop through all files in the folder and upload them to the server
    for filename in os.listdir(folder):
        if filename.endswith('.fastq') or filename.endswith('.fastq.gz'):
            print("Uploading " + filename + "...")
            file_path = os.path.abspath(os.path.join(folder, filename))
            with open(file_path, "rb") as file:
                files = [('file', (filename, file, "application/octet-stream"))]
                response = requests.request("POST", url, files=files, headers=headers)
                respJSON = response.json()
                # If 'data' is not in the response, then raise an error with the response
                if 'data' not in respJSON:
                    raise ValueError(f"Error uploading {filename}: {respJSON}")
                # print(repr(respJSON))
                # take the response from each file uploaded and record its aa server file path. store paths as list for job submission
                allData = respJSON['data']
                paths = allData['path']
                fastq_paths.append(paths)
                if respJSON['success']:
                    print(str(filename) + " was uploaded successfully to " + str(paths))
                else:
                    print(str(filename) + " failed to upload")
    return fastq_paths


def start_protocol_job(fastq_paths, server, protocol_id, job_name, out_file, debug, headers):
    print("Submitting job...")
    # format the paths list into the samples list with the sequence_files key
    samples = [{"sequence_files": fastq_paths}]

    # second section submit the jobs using samples list created at the end of the file upload section
    endpoint = "job-submission/protocols/{}/submit-job".format(protocol_id)
    url = "{}/api/{}".format(server, endpoint)

    payload = {
      "job_name": job_name,
      "samples": samples
    }
    response = requests.request("POST", url, json=payload, headers=headers)
    response.raise_for_status()
    result = response.json()
    if debug:
        with open("submission.json", 'w') as fp:
            json.dump(result, fp, indent=2)

    if not 'data' in result:
        raise ValueError(f"Error submitting job: {result}")

    if not 'job_id' in result['data']:
        raise ValueError(f"Error submitting job: {result}")

    job_id = result['data']['job_id']
    print(f"Job {job_id} submitted successfully")

    if out_file:
        with open(out_file, 'w') as fp:
            #job_id=1234
            fp.write(f"job_id={job_id}\n")
            #job_name=MyJob
            fp.write(f"job_name={job_name}\n")


def main():
    parser = argparse.ArgumentParser(description='Upload fastqs and submit jobs to the Archer Analysis server')
    parser.add_argument('-u', '--user', help='Username for Archer Analysis server')
    parser.add_argument('-p', '--password', help='Password for Archer Analysis server')
    parser.add_argument('-a', '--api_key', help='API key for Archer Analysis server, alternative to password')
    parser.add_argument('-s', '--server', help='Archer Analysis server URL', default='https://analysis.archerdx.com')
    parser.add_argument('-f', '--folder', help='Folder containing FASTQ files to upload')
    parser.add_argument('-i', '--protocol_id', help='Protocol ID to submit jobs to')
    parser.add_argument('-j', '--job_name', help='Name of the Archer job')
    parser.add_argument('-o', '--out_file', help='Output file to write the job_id and job_name in .env file format')
    parser.add_argument('-d', '--debug', help='Keep the job details file', action='store_true')
    args = parser.parse_args()

    headers = {
        'accept': 'application/json'
    }
    if args.user and args.api_key:
        # Do the equivalent of this:
        # echo -n "<args.user>:<args.api_key>" | base64
        # <curl>  -H 'Authorization: API-Key <your_encoded_email_and_key>'
        user_key = f"{args.user}:{args.api_key}"
        # Base64 encode the string
        encoded_auth = base64.b64encode(user_key.encode('utf-8')).decode('utf-8')
        headers['Authorization'] = f"API-Key {encoded_auth}"
    elif args.user and args.password:
        # Construct basic auth header from scratch if no api_key
        user_pass = f"{args.user}:{args.password}"
        encoded_auth = base64.b64encode(user_pass.encode('utf-8')).decode('utf-8')
        headers['Authorization'] = f"Basic {encoded_auth}"
    else:
        raise ValueError("Either user and password or user and user api_key must be provided")

    # upload the fastqs
    fastq_paths = upload_fastqs(args.folder, args.server, headers)

    # submit the jobs
    start_protocol_job(fastq_paths, args.server, args.protocol_id, args.job_name, args.out_file, args.debug, headers)

if __name__ == "__main__":
    main()

