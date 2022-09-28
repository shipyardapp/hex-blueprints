import requests
import shipyard_utils as shipyard
import argparse
from dataclasses import dataclass
import sys

## error codes 
EXIT_CODE_BAD_REQUEST = 206
EXIT_CODE_INVALID_PROJECT_ID = 201
EXIT_CODE_INVALID_RUN_ID = 202
EXIT_CODE_EXCESSIVE_REQUESTS = 203
EXIT_CODE_HEX_SERVER_ERROR = 204
EXIT_CODE_AUTHENTICATION_ERROR = 205
EXIT_CODE_UNKNOWN_ERROR = 3

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
    
def has_reason(response):
    """
    Helper function to see if (in the event of an error) an http response contains a valid json response with 'reason' as a valid key
    """
    if len(response) > 0:
        if 'reason' in response.keys():
            return True
    return False

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

def run_project(project_id,api_token):
    """
    Runs a specific project specified by the project_id.
    Upon a successful response (201), the returning value will be the the json of the response which is in the following format:
    Taken from Hex's api documentation found here: https://learn.hex.tech/docs/develop-logic/hex-api/api-reference#operation/RunProject
    {
        "projectId": "5a8591dd-4039-49df-9202-96385ba3eff8",
        "runId": "78c33d18-170c-44d3-a227-b3194f134f73",
        "runUrl": "string",
        "runStatusUrl": "string",
        "traceId": "string"
    }

    For an unsuccessful action (404, 422) the response will be the following json:
    {
        "traceId" : "string",
        "reason" : "string"
    }
    """
    base_url = 'https://app.hex.tech/api/v1'
    url = f"{base_url}/project/{project_id}/run"
    headers = {"Authorization" : f"Bearer {api_token}"}
    try:
        response = requests.post(url = url,headers=headers)
        status_code = response.status_code
        response_json = response.json()
        ## go through known error cases

        ## 404 not found error
        if status_code == 404:
            print("Request was not found. Please ensure that you have the proper project id and run id")
            print("Review the steps in the authorization page to ensure the token and project id are correct")
            if has_reason(response_json):
                hex_response = HexResponse(status_code,response_json)
            else:
                hex_response = HexResponse(EXIT_CODE_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 
        ## 401 Unauthorized error
        elif status_code == 401:
            print("Request was unable to be authenticated, please ensure that your API token is entered correctly and that it is not expired.")
            print("Review the steps in the authorization page to ensure the token and project id are correct")
            if has_reason(response_json):
                hex_response = HexResponse(status_code,response_json)
            else:
                hex_response = HexResponse(EXIT_CODE_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 
        ## 422 unprocessable error
        elif status_code == 422:
            print("The request could not be processed by the server")
            print("Review the steps in the authorization page to ensure the token and project id are correct")
            if has_reason(response_json):
                hex_response = HexResponse(status_code,response_json)
            else:
                hex_response = HexResponse(EXIT_CODE_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 

        ## successful post request
        elif status_code == 201:
            print("Request was successful")
            hex_response = HexResponse(status_code,response.json())
    ## in all other cases not outlined by the api docs, produce an unknown error 
        else:
            hex_response = HexResponse(EXIT_CODE_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 
        return hex_response
    ## handle the exception and exit
    except Exception as e:
        print(f"Exception occurred: {e}")
        sys.exit(EXIT_CODE_UNKNOWN_ERROR)

def main():
    args = get_args()
    project_id = args.project_id
    project_id = str(project_id).strip() ## remove whitespace
    api_token = args.api_token
    api_token = str(api_token).strip() ## remove whitespace

    ## run the project
    trigger_run = run_project(project_id,api_token)
    status_code = trigger_run.status_code
    response_json = trigger_run.response_json

    ## create artifacts folder to save runId on success and reason if not successful
    base_folder_name = shipyard.logs.determine_base_artifact_folder('hex')
    artifact_subfolder_paths = shipyard.logs.determine_artifact_subfolders(base_folder_name)
    shipyard.logs.create_artifacts_folders(artifact_subfolder_paths)

    if status_code == 201:
        run_id = response_json['runId'] ## need this to verify the status in the other blue print
        shipyard.logs.create_pickle_file(artifact_subfolder_paths,'runId',run_id) ## save the run id 

    ## in all other failing cases
    else: 
        reason = response_json['reason']
        shipyard.logs.create_pickle_file(artifact_subfolder_paths,'reason',reason)

if __name__ == "__main__":
    main()


