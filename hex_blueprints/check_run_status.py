import requests
import shipyard_utils as shipyard
import argparse

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

def main():
    pass

if __name__ == '__main__':
    main()

