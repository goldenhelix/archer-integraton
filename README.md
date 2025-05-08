# Archer Analysis Automation Scripts

This repository contains Golden Helix server tasks and workflow for automating job submission and result downloading from the Archer Analysis server.

## Prerequisites

- Access to Archer Analysis server (https://analysis.archerdx.com or your own instance)
- Valid user credentials and API key

## Setup Instructions

### 1. Create a Protocol

1. Navigate to the Protocols page: https://analysis.archerdx.com/home#protocols_list
2. Click "New Protocol"
3. Set up the protocol:
   - Name the protocol
   - Select appropriate panel
   - Configure pipeline options
   - Adjust any other settings as needed (Hooks are not required)

### 2. Get Protocol ID

1. From your created protocol, click the "New Job" button (+ icon)
2. Note the protocol ID from the URL:
   - Example URL: `https://analysis.archerdx.com/job-submission/protocols/3697/submit-job`
   - In this example, `3697` is the protocol ID
3. Edit `archer_analysis.workflow.yaml` and set the `protocol_id` parameter to the protocol ID you noted in step 2.

### 3. Generate API Key

1. Log into Archer Analysis
2. Go to Help > REST API Documentation
3. In the Swagger UI:
   - Expand the `/application_key/create` endpoint
   - Click "Try it Out"
   - Copy the API key from the Response body (`"key": "<api_key>"`)

### 4. Set Up Credentials File

Edit the `.env.archer_credentials` file in the project root with the following contents:
```
ARCHER_USERNAME=your_username@example.com
ARCHER_API_KEY=your_api_key
ARCHER_SERVER=https://analysis.archerdx.com
```

Replace the placeholder values with your actual credentials:
- `ARCHER_USERNAME`: Your Archer Analysis username/email
- `ARCHER_API_KEY`: The API key generated in step 3
- `ARCHER_SERVER`: The Archer Analysis server URL (default shown above)

## Tasks and Workflow

The repository contains the following tasks and workflow:

- `archer_job_submit.py`: Submit jobs to the Archer server
- `archer_job_download.py`: Download results from completed jobs and generate a sample manifest
- `archer_vspipeline.task.yaml`: Create a vspipeline project from a folder of input files and a sample manifest
- `archer_analysis.workflow.yaml`: Workflow for automating job submission, result downloading, and vspipeline project creation

## Customizing the Project Template

The `archer_vspipeline.task.yaml` task uses a project template to create the vspipeline project. By default it uses the `Archer_Variant_Plex.vsproject-template` template, which is a custom template that has a very basic set of sources.

You can customize the project template by changing `value` in the `project_template` parameter in the workflow `archer_analysis.workflow.yaml` or the task `archer_vspipeline.task.yaml`.

## Scripts

You do not need to run the scripts directly. Instead, use the Golden Helix server tasks and workflow to submit jobs and download results.

### archer_job_submit.py

Uploads FASTQ files and submits analysis jobs to the Archer server.

Arguments:
```
-u, --user        Username for Archer Analysis server
-p, --password    Password for Archer Analysis server (alternative to API key)
-a, --api_key     API key for Archer Analysis server
-s, --server      Archer Analysis server URL (default: https://analysis.archerdx.com)
-f, --folder      Folder containing FASTQ files to upload
-i, --protocol_id Protocol ID to submit jobs to
-j, --job_name    Name of the Archer job
```

Example usage:
```bash
python3 archer_job_submit.py -u user@example.com -a "your_api_key" -s "https://analysis.archerdx.com" -f fastq_folder --protocol_id 3697 -j "Test Run"
```

### archer_job_download.py

Downloads analysis results from completed Archer jobs.

Arguments:
```
-u, --user          Username for Archer Analysis server
-p, --password      Password for Archer Analysis server (alternative to API key)
-a, --api_key       API key for Archer Analysis server
-s, --server        Archer Analysis server URL (default: https://analysis.archerdx.com)
-i, --job_id        Job ID for the Archer job
-f, --folder        Destination folder for the results
-w, --wait          Wait for the job to finish
-t, --wait_interval Wait interval in seconds (default: 10)
-d, --debug         Keep the job details file
```

Example usage:
```bash
python3 archer_job_download.py -u user@example.com -a "your_api_key" -s "https://analysis.archerdx.com" -f results_folder --job_id 8959 -w -d
```

## Downloaded Files

The download script will retrieve the following files for each sample:
- Combined VCF file (`.combined.sorted.vcf.gz`) and index
- BAM file (`.molbar.trimmed.deduped.merged.bam`) and index
- Structural variant VCF (`.StructVar.vcf.gz`) and index
- Log files
- Job configuration
- Sample manifest in `samples.tsv`

## Notes

- Either password or API key authentication can be used, but API key is recommended
- The download script has a hard wait limit of 4 hours for job completion
- Use the `-w` flag with the download script to automatically wait for job completion
- The `-d` (debug) flag preserves job details JSON for troubleshooting
