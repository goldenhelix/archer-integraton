import os
import argparse
import requests
import json
import time
import base64

# This script downloads analysis results from archer

HARD_WAIT_LIMIT = 60*60*4 # 4 hours

TO_DOWNLOAD_PER_SAMPLE = [
    ('VCFs/', '.combined.sorted.vcf.gz'),
    ('VCFs/', '.combined.sorted.vcf.gz.tbi'),
    ('VCFs/', '.StructVar.vcf.gz'),
    ('VCFs/', '.StructVar.vcf.gz.tbi'),
    ('CNV2/', '.CNV2.vcf'),
    ('', '.molbar.trimmed.deduped.merged.bam'),
    ('', '.molbar.trimmed.deduped.merged.bam.bai'),
]

def wait_job(job_id, headers, server, wait_interval, debug):
    # This essentially does
    # curl -s -u "${AUTH}" -X GET "https://analysis.archerdx.com/api/jobs/${JOB_ID}/" -H  "accept: application/json" > job_details.json
    # And then parses the job_details.json file to get the status of the job
    # If the job is still running, it will wait for the job to finish

    # Get the job details
    endpoint = "running-jobs/"
    url = "{}/api/{}".format(server, endpoint)

    start_wait = time.time()
    ever_found = False

    while True:
        response = requests.request("GET", url, headers=headers)
        response.raise_for_status()
        job_json = response.json()
        if debug:
            with open("running_jobs.json", 'w') as fp:
                json.dump(job_json, fp, indent=2)

        if 'data' not in job_json:
            raise ValueError(f"Error getting running-jobs: {job_json}")

        jobs = job_json['data']['jobs']
        # Find the job where job['job_id'] == job_id
        job = None
        for j in jobs:
            if str(j['job_id']) == job_id:
                job = j
                break
        if job is None:
            if ever_found:
                # If we have ever found the job, then we have finished waiting
                print(f"Job {job_id} has finished, proceeding to download...")
                return
            else:
                print(f"Job {job_id} not found in running jobs, proceeding to download...")
            return

        # Print the 'name' and 'job_status_name' of the job, and say we will wait for wait_interval
        ever_found = True
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime())
        print(f"{timestamp} Job {job_id} ({job['name']}) is {job['job_status_name']}. Waiting for {wait_interval} seconds...")
        time.sleep(wait_interval)

        # If we exceed the hard wait limit, raise an error
        if time.time() - start_wait > HARD_WAIT_LIMIT:
            raise TimeoutError(f"Job {job_id} has been running for more than {HARD_WAIT_LIMIT} seconds")

def download_file(job_id, headers, server, folder, to_download):
    # Check if the file already exists
    full_path = f"{folder}/{to_download}"
    # mkdir -p the parent directory in full_path
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    if os.path.exists(full_path):
        print(f"{to_download} already exists, skipping...")
        return True
    try:
        print(f"Downloading {to_download}...")
        response = requests.request("GET", f"{server}/api/jobs/{job_id}/job-directory-files/download/{to_download}", headers=headers)
        response.raise_for_status()
        with open(full_path, 'wb') as fp:
            for chunk in response.iter_content(chunk_size=5242880):
                fp.write(chunk)
        return True
    except Exception as ex:
        print(ex)
        return False

def download_job(job_id, headers, server, folder, debug):
    # This essentially does
    # curl -s -u "${AUTH}" -X GET "https://analysis.archerdx.com/api/jobs/${JOB_ID}/" -H  "accept: application/json" > job_details.json
    # And then parses the job_details.json file to get the status of the job

    # Get the job details
    endpoint = "jobs/{}/".format(job_id)
    url = "{}/api/{}".format(server, endpoint)
    response = requests.request("GET", url, headers=headers)
    response.raise_for_status()
    job_json = response.json()
    if debug:
        with open("job_details.json", 'w') as fp:
            json.dump(job_json, fp, indent=2)

    if not 'data' in job_json:
        raise ValueError(f"Error getting job details: {job_json}")

    # Download all the log files
    download_file(job_id, headers, server, folder, "1.log.stderr.txt")
    download_file(job_id, headers, server, folder, f"{job_id}.job.log")
    download_file(job_id, headers, server, folder, f"{job_id}.err-1")
    download_file(job_id, headers, server, folder, "workflow.config.1")

    name = job_json['data']['name']
    status = job_json['data']['job_status_name']

    # Print the current status
    print(f"Job {job_id} ({name}) is {status}")

    # If status == COMPLETED_ERROR then we don't download the results (throw an exception to ensure non-zero exit code)
    if status == "COMPLETED_ERROR":
        raise ValueError(f"Job {job_id} ({name}) has failed. Review log under {folder}/1.log.stderr.txt for more information")

    sample_tsv = []
    for sample in job_json['data']['samples']:
        # Save out 'name', 'id', 'detail_url'
        name = sample['name']
        id = sample['id']
        bam_path = f"../{name}.molbar.trimmed.deduped.merged.bam" # Save as relative path to project
        detail_url = sample['detail_url']
        sample_tsv.append((name, id, bam_path, detail_url))

        # Print we are downloading the results for the sample
        print(f"Downloading results for sample {name} ({id})...")
        for file_prefix, file_suffix in TO_DOWNLOAD_PER_SAMPLE:
            to_download = f"{file_prefix}{name}{file_suffix}"
            download_file(job_id, headers, server, folder, to_download)

    # Write samples.tsv under folder with the sample_tsv
    with open(f"{folder}/samples.tsv", 'w') as fp:
        fp.write("Name\tID\tBAM Path\tDetail URL\n")
        for name, id, bam_path, detail_url in sample_tsv:
            fp.write(f"{name}\t{id}\t{bam_path}\t{detail_url}\n")

    print(f"Job {job_id} ({name}) has finished downloaded")

def main():
    parser = argparse.ArgumentParser(description='Check on the status of a job, wait if requested and download the results')
    parser.add_argument('-u', '--user', help='Username for Archer Analysis server')
    parser.add_argument('-p', '--password', help='Password for Archer Analysis server')
    parser.add_argument('-a', '--api_key', help='API key for Archer Analysis server, alternative to password')
    parser.add_argument('-s', '--server', help='Archer Analysis server URL', default='https://analysis.archerdx.com')
    parser.add_argument('-i', '--job_id', help='Job ID for the Archer job')
    parser.add_argument('-f', '--folder', help='Destination folder for the results')
    parser.add_argument('-w', '--wait', help='Wait for the job to finish', action='store_true')
    parser.add_argument('-t', '--wait_interval', help='Wait interval in seconds', default=10, type=int)
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

    if args.wait:
        # wait for the job to finish
        wait_job(args.job_id, headers, args.server, args.wait_interval, args.debug)

    # download the results
    download_job(args.job_id, headers, args.server, args.folder, args.debug)

if __name__ == "__main__":
    main()




