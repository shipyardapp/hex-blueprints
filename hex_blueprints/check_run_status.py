from dataclasses import dataclass
import requests
import shipyard_utils as shipyard
import argparse
import sys

## error codes 

EXIT_CODE_BAD_REQUEST = 200
EXIT_CODE_INVALID_PROJECT_ID = 201
EXIT_CODE_INVALID_RUN_ID = 202
EXIT_CODE_EXCESSIVE_REQUESTS = 203
EXIT_CODE_HEX_SERVER_ERROR = 204
EXIT_CODE_AUTHENTICATION_ERROR = 205
EXIT_CODE_UNKNOWN_ERROR = 299

## run status codes
## these are provided here: https://learn.hex.tech/docs/develop-logic/hex-api/api-reference#operation/GetRunStatus
EXIT_CODE_PENDING = 220
EXIT_CODE_RUNNING = 221
EXIT_CODE_ERRORED = 222
EXIT_CODE_COMPLETED = 223
EXIT_CODE_KILLED = 224
EXIT_CODE_UNABLE_TO_ALLOCATE_KERNEL = 225

@dataclass
class HexResponse:
    """
    This is a utility class to maintain the http status code with the json response
    """
    status_code : int
    response_json : dict
    
def get_args():    
    """
    Creates the argument parser for the CLI
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id",dest='project_id',required=True)
    parser.add_argument('--api-token',dest = 'api_token',required=True)
    ## add a flag for input params 
    args = parser.parse_args()
    return args

def get_run_status(project_id, api_token, run_id):
    """
    Returns the json with metadata of the last run of the project
    """
    url = f'https://app.hex.tech/api/v1/project/{project_id}/run/{run_id}'
    headers = {"Authorization" : f"Bearer {api_token}"}
    response = requests.get(url= url, headers = headers)
    status_code = response.status_code
    response_json = response.json()
    ## go through the known response codes documented by the HEX api: https://learn.hex.tech/docs/develop-logic/hex-api/overview#404-not-found
    if status_code == 404:
        print("Request was not found. Please ensure that you have the proper project id and run id")
        sys.exit(EXIT_CODE_BAD_REQUEST)
    elif status_code == 429:
        print("The number of requests has exceeded the limit, HEX allows 60 requests per minute. Please wait 2 minutes for the limit to reset")
        sys.exit(EXIT_CODE_EXCESSIVE_REQUESTS)
    elif status_code == 401:
        print("Request was unable to be authenticated, please ensure that your API token is entered correctly and that it is not expired.")
        sys.exit(EXIT_CODE_AUTHENTICATION_ERROR)
    elif status_code == 500:
        print("There was a server side error when processing the request, please contact HEX Support at support@hex.tech for continued disturbances")
        sys.exit(EXIT_CODE_HEX_SERVER_ERROR)
    elif status_code == 200:
        return response_json
    else:
        print("Unknown error when processing request")
        sys.exit(EXIT_CODE_UNKNOWN_ERROR)

def determine_run_status(run_response):
    """
    Will determine the status of the run and return the appropriate exit code
    """
    status = run_response['status'] ## grab the status
    print(f"Status is {status}")
    if status == 'PENDING':
        return EXIT_CODE_PENDING
    elif status == 'RUNNING':
        return EXIT_CODE_RUNNING
    elif status == 'ERRORED':
        return EXIT_CODE_RUNNING
    elif status == 'COMPLETED':
        return EXIT_CODE_COMPLETED
    elif status == 'KILLED':
        return EXIT_CODE_KILLED
    elif status == 'UNABLE_TO_ALLOCATE_KERNEL':
        return EXIT_CODE_UNABLE_TO_ALLOCATE_KERNEL
    
    print("No status code returned")
    return EXIT_CODE_UNKNOWN_ERROR


        
def main():
    args = get_args()
    project_id = args.project_id
    project_id = str(project_id).strip() ## remove whitespace
    api_token = args.api_token
    api_token = str(api_token).strip() ## remove whitespace

    ## extract the run id from the artifact folder
    base_folder_name = shipyard.logs.determine_base_artifact_folder('hex')
    artifact_subfolder_paths = shipyard.logs.determine_artifact_subfolders(base_folder_name)
    shipyard.logs.create_artifacts_folders(artifact_subfolder_paths)

    run_id = shipyard.logs.read_pickle_file(artifact_subfolder_paths,'runId')

    response = get_run_status(project_id,api_token,run_id)
    status_exit_code = determine_run_status(response)
    print(status_exit_code)
    sys.exit(status_exit_code)

if __name__ == '__main__':
    main()
