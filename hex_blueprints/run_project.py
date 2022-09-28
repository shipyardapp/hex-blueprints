import requests
import shipyard_utils as shipyard
import argparse
from dataclasses import dataclass
import sys

EXIT_UNKNOWN_ERROR = 299

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
    response = requests.post(url = url,headers=headers)
    status_code = response.status_code
    response_json = response.json()
    if status_code == 404:
        ## not found
        if len(response_json != 0): ## make sure there is data in the response
            print(response_json['reason'])
        else:
            print("Request not found and there was no data returned from the API. Problem could be due to incorrectly inputting the project id or by not publishing the project correctly. Please review the authorization page and review each step")
            return HexResponse(EXIT_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 
    elif status_code == 422:
        print("A response was not able to be produced")
        print(response_json['reason'])
    elif status_code == 201:
        print("Request was successful and project was run")

    hex_response = HexResponse(status_code,response.json())
    return hex_response

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


    ## create artifacts folder to save 
    base_folder_name = shipyard.logs.determine_base_artifact_folder('hex')
    artifact_subfolder_paths = shipyard.logs.determine_artifact_subfolders(base_folder_name)
    shipyard.logs.create_artifacts_folders(artifact_subfolder_paths)

    if status_code == 201:
        run_id = response_json['runId'] ## need this to verify the status in the other blue print
        # run_status_url = response_json['runStatusUrl']
        # trace_id = response_json['traceId']
        shipyard.logs.create_pickle_file(artifact_subfolder_paths,'runId',run_id) ## save the run id 

    ## in all other failing cases
    else: 
        # trace_id = response_json['traceId']
        reason = response_json['reason']
        shipyard.logs.create_pickle_file(artifact_subfolder_paths,'reason',reason)
        print("Failed:")
        print(response_json)

if __name__ == "__main__":
    main()


