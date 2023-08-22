import re
import sys
import time
import argparse
import requests
import shipyard_utils as shipyard

from dataclasses import dataclass

try:
    import exit_codes as ec
except BaseException:
    from . import exit_codes as ec

BASE_URL = 'https://app.hex.tech/api/v1'
UUID_PATTERN = re.compile("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89ABab][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")


@dataclass
class HexResponse:
    """
    This is a utility class to maintain the http status code with the json response
    """
    status_code: int
    response_json: dict


def is_valid_uuid(uuid_str):
    return bool(UUID_PATTERN.match(uuid_str))


def has_reason(response):
    """
    Helper function to see if (in the event of an error) a http response contains a valid json response with 'reason' as a valid key
    """
    return (
            len(response) > 0
            and response is not None
            and 'reason' in response.keys()
    )


def get_args():
    """
    Creates the argument parser for the CLI
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", dest='project_id', required=True)
    parser.add_argument('--api-token', dest='api_token', required=True)
    parser.add_argument("--wait-for-completion", dest="wait_for_completion", default="FALSE")
    return parser.parse_args()


def handle_api_response(response):
    status_code = response.status_code
    response_json = response.json()

    if status_code == 201:
        return HexResponse(status_code, response_json)
    if status_code in {401, 404, 422}:
        print("Review the steps in the authorization page to ensure the token and project id are correct")
    else:
        return HexResponse(ec.EXIT_CODE_UNKNOWN_ERROR, {"reason": "unknown"})

    if has_reason(response_json):
        return HexResponse(status_code, response_json)
    return HexResponse(ec.EXIT_CODE_UNKNOWN_ERROR, {"reason": "unknown"})


def run_project(project_id, api_token):
    """Runs a specific project specified by the project_id."""
    if not is_valid_uuid(project_id):
        print(f"Project Id {project_id} is in the incorrect format. Please copy the correct value from Hex")
        return ec.EXIT_CODE_INVALID_PROJECT_ID

    url = f"{BASE_URL}/project/{project_id}/run"
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        response = requests.post(url=url, headers=headers)
        hex_response = handle_api_response(response)
        if hex_response.status_code == 201:
            print(f"Project {project_id} was successfully triggered. RunId {hex_response.response_json['runId']} was created")
        return hex_response
    except Exception as e:
        print(
            "Could not connect to Hex with the provided API token and Project Id. Please ensure that you have the correct API token and Project Id from Hex and that the API token is not expired."
        )
        sys.exit(ec.EXIT_CODE_AUTHENTICATION_ERROR)


def get_run_status(project_id, api_token, run_id):
    """Returns the json with metadata of the last run of the project."""
    if not is_valid_uuid(project_id):
        print(f"Project Id {project_id} is in the incorrect format. Please copy the correct value from Hex")
        return ec.EXIT_CODE_INVALID_PROJECT_ID

    url = f'{BASE_URL}/project/{project_id}/run/{run_id}'
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        response = requests.get(url=url, headers=headers)
        status_code = response.status_code
        response_json = response.json()
        ## go through the known response codes documented by the HEX api: https://learn.hex.tech/docs/develop-logic/hex-api/overview#404-not-found
        if status_code == 200:
            return response_json
        messages = {
            401: "Request was unable to be authenticated.",
            404: "Request was not found. Please ensure you have the proper project id and run id.",
            429: "Exceeded request limit. Wait 2 minutes for the limit to reset.",
            500: "Server side error. Please contact HEX Support.",
        }
        print(messages.get(status_code, "Unknown error when processing request"))
        return ec.EXIT_CODE_UNKNOWN_ERROR
    except Exception as e:
        print("Could not connect to Hex with the provided API token and Project Id.")
        return ec.EXIT_CODE_AUTHENTICATION_ERROR


def determine_run_status(run_response):
    """Determine the status of the run and return the appropriate exit code."""
    status = run_response['status']
    end_time = run_response['endTime']
    run_id = run_response['runId']

    status_messages = {
        'COMPLETED': ec.EXIT_CODE_COMPLETED,
        'KILLED': ec.EXIT_CODE_KILLED,
        'PENDING': ec.EXIT_CODE_PENDING,
        'RUNNING': ec.EXIT_CODE_RUNNING,
        'UNABLE_TO_ALLOCATE_KERNEL': ec.EXIT_CODE_UNABLE_TO_ALLOCATE_KERNEL,
        'ERRORED': ec.EXIT_CODE_ERRORED,
    }

    print(f"Hex reports that run {run_id} has a status of {status}.", end=' ')
    if end_time:
        print(f"End time: {end_time}")
    else:
        print()
    return status_messages.get(status, ec.EXIT_CODE_UNKNOWN_ERROR)


def main():
    args = get_args()
    project_id = args.project_id.strip()
    api_token = args.api_token.strip()

    ## run the project
    trigger_run = run_project(project_id, api_token)
    status_code = trigger_run.status_code
    response_json = trigger_run.response_json

    ## create artifacts folder to save runId on success and reason if not successful
    base_folder_name = shipyard.logs.determine_base_artifact_folder('hex')
    artifact_subfolder_paths = shipyard.logs.determine_artifact_subfolders(base_folder_name)
    shipyard.logs.create_artifacts_folders(artifact_subfolder_paths)

    if status_code == 201:
        run_id = response_json['runId']  ## need this to verify the status in the other blueprint
        shipyard.logs.create_pickle_file(artifact_subfolder_paths, 'runId', run_id)  ## save the run id
        ## save the response 
        response_data_file = shipyard.files.combine_folder_and_file_name(artifact_subfolder_paths['responses'],
                                                                         f'project-{project_id}_run_{run_id}_response.json')  ## save the run response
        shipyard.files.write_json_to_file(response_json, response_data_file)
    else:
        reason = response_json['reason']
        shipyard.logs.create_pickle_file(artifact_subfolder_paths, 'reason', reason)
    if args.wait_for_completion.upper() == "TRUE":
        response = get_run_status(project_id, api_token, run_id)
        status_exit_code = determine_run_status(response)

        while status_exit_code in (ec.EXIT_CODE_RUNNING, ec.EXIT_CODE_PENDING):
            print(f"Run {run_id} is still running. Checking again in 60 seconds")
            time.sleep(60)
            response = get_run_status(project_id, api_token, run_id)
            status_exit_code = determine_run_status(response)
        return status_exit_code


if __name__ == "__main__":
    main()
