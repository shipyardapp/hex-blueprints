import requests
import shipyard_utils as shipyard
import argparse
from dataclasses import dataclass
import sys
import re

try:
    import exit_codes as ec
except BaseException:
    from . import exit_codes as ec

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
    if len(response) > 0 and response is not None:
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
    pattern = re.compile("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89ABab][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$") ## copied from Hex's error message
    matched = pattern.match(project_id)
    if not matched:
        print(f"Project Id {project_id} is in the incorrect format. The expected format is {pattern.pattern}. Please copy the correct value from Hex")
        sys.exit(ec.EXIT_CODE_INVALID_PROJECT_ID)
    base_url = 'https://app.hex.tech/api/v1'
    url = f"{base_url}/project/{project_id}/run"
    headers = {"Authorization" : f"Bearer {api_token}"}
    ## there are 4 types of scenarios:
    # 1. Incorrect API Key and Incorrect ProjectId
    # 2. Incorrect API Key and Correct ProjectId
    # 3. Correct API Key and Incorrect ProjectId
    # 4. Correct API Key and Correct ProjectID
    ## Of those scenarios, #4 is the only correct one while #1 and #2 will not be able to authenticate the api and #3 will return 404
    try:
        response = requests.post(url = url,headers=headers)
        status_code = response.status_code
        response_json = response.json()
        ## go through known error cases

        ## 404 not found error
        if status_code == 404:
            print("Review the steps in the authorization page to ensure the token and project id are correct")
            if has_reason(response_json):
                hex_response = HexResponse(status_code,response_json)
            else:
                hex_response = HexResponse(ec.EXIT_CODE_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 
        ## 401 Unauthorized error
        elif status_code == 401:
            print("Request was unable to be authenticated, please ensure that your API token is entered correctly and that it is not expired.")
            print("Review the steps in the authorization page to ensure the token and project id are correct")
            if has_reason(response_json):
                hex_response = HexResponse(status_code,response_json)
            else:
                hex_response = HexResponse(ec.EXIT_CODE_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 
        ## 422 unprocessable error
        elif status_code == 422:
            # print(f"Project {project_id} could not be processed, ensure this is the project_id")
            print("Review the steps in the authorization page to ensure the token and project id are correct")
            if has_reason(response_json):
                hex_response = HexResponse(status_code,response_json)
            else:
                hex_response = HexResponse(ec.EXIT_CODE_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 

        ## successful post request
        elif status_code == 201:
            print(f"Project {project_id} was successfully triggered. RunId {response_json['runId']} was created")
            hex_response = HexResponse(status_code,response_json)
    ## in all other cases not outlined by the api docs, produce an unknown error 
        else:
            hex_response = HexResponse(ec.EXIT_CODE_UNKNOWN_ERROR,{"reason": "unknown"}) ## will return a matching object 
        return hex_response
    ## the exception would result in a failure of the post request, this will either be due to an invalid api token or invalid project id
    ## handle the exception and exit
    except Exception as e:
        print(f"Could not authenticate with API token {api_token}. ProjectID {project_id} matched expected format. Please ensure that you have the correct API token and Project Id from Hex and that the api token is not expired.")
        sys.exit(ec.EXIT_CODE_AUTHENTICATION_ERROR)

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
        ## save the response 
        response_data_file = shipyard.files.combine_folder_and_file_name(artifact_subfolder_paths['responses'],f'project-{project_id}_run_{run_id}_response.json') ## save the run response
        shipyard.files.write_json_to_file(response_json,response_data_file)

    ## in all other failing cases
    else: 
        reason = response_json['reason']
        shipyard.logs.create_pickle_file(artifact_subfolder_paths,'reason',reason)

if __name__ == "__main__":
    main()


