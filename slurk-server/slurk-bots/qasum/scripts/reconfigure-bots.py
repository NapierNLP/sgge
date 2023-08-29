"""Script for restarting bots and adding them to the same rooms they were originally in."""

from typing import Optional

import argparse
import csv
import json
import requests

import docker
import docker.errors

# - [ ] complete script to re-add chatbots to all rooms w/participants
# 	- [ ] take list of participant tokens
# 	- [ ] figure out which rooms they are assigned to
# 	- [ ] restart the slurk-bots with the original task id for those rooms
# 		- [ ] do we need to check the task id associated with the room first?
# 	- [ ] add the bots to all the rooms

ADMIN_TOKEN = ""
HOSTNAME = "http://localhost"
PORT = "8080"
PREFIX = "/gaelic"
API_SLUG = "/slurk/api"
API_PORT = f":{PORT}" if PORT else ""
API_URL = HOSTNAME + API_PORT + PREFIX + API_SLUG

DEFAULT_HEADERS = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}


def check_response(response_json):
    if 'code' in response_json:
        raise ValueError(f"Unexpected API Response:\n{response_json}")
    else:
        return response_json


def api_call(method, endpoint, params=None, data_json=None) -> dict:
    if params is None:
        params = {}
    if data_json is None:
        data_json = {}
    response = requests.request(method,
                                API_URL + f"/{endpoint}",
                                headers=DEFAULT_HEADERS,
                                params=params,
                                json=data_json)
    try:
        json_response = json.loads(response.content)
        verified_response = check_response(json_response)
        return verified_response
    except ValueError:
        if json_response['code'] == 404:
            raise ValueError(f"404 - endpoint not found: {endpoint}")
        else:
            raise


def query_api(endpoint, params=None, data_json=None):
    return api_call("GET", endpoint, params, data_json)


def submit_api(endpoint, params=None, data_json=None):
    return api_call("POST", endpoint, params, data_json)


def get_token_info():
    return query_api("/tokens")


def get_room_info(room_id):
    return query_api(f"/rooms/{room_id}")


def read_participant_tokens_csv(filename):
    participant_tokens = []
    with open(filename, 'r') as participant_tokens_file:
        reader = csv.reader(participant_tokens_file)
        for line in reader:
            for entry in line:
                participant_tokens.append(entry)
    return participant_tokens


def create_permissions_from_file(permissions_filepath) -> dict:
    with open(permissions_filepath, 'r') as permissions_file:
        data = json.load(permissions_file)
        return submit_api("/permissions", data_json=data)


def create_room_token(room, permissions_filepath, registrations, task):
    permissions_response = create_permissions_from_file(permissions_filepath)
    permissions_id = permissions_response.get('id')
    token_response = submit_api("/tokens",
                                data_json={
                                    "permissions_id": permissions_id,
                                    "room_id": room,
                                    "registrations_left": registrations,
                                    "task_id": task
                                })
    token_id = token_response.get('id')
    return token_id


def create_user(username, token):
    user_response = submit_api("/users", data_json={"name": username, "token_id": token})
    user_id = user_response.get('id')
    return user_id


class DockerManager(object):
    def __init__(self, docker_host: Optional[str] = None, slurk_bots_path: Optional[str] = None) -> None:
        if docker_host is None or slurk_bots_path is None:
            self.client = docker.from_env()
            self.slurk_bots_path = "."
        else:
            self.client = docker.from_env(environment={'DOCKER_HOST': docker_host}, use_ssh_client=True)
            self.slurk_bots_path = slurk_bots_path

    def check_container(self, container_name_substring, status=None) -> docker.client.ContainerCollection:
        filters = {'name': container_name_substring}
        if status is not None:
            filters['status'] = status
        return self.client.containers.list(all=True, filters=filters)

    def kill_container_if_running(self, container_name_substring: str) -> None:
        matching_containers = self.check_container(container_name_substring, 'running')
        print(f"containers matching {container_name_substring}: {matching_containers}")
        if matching_containers:
            for container in matching_containers:
                container.kill()

    def remove_container_if_exists(self, container_name_substring: str) -> None:
        matching_containers = self.check_container(container_name_substring)
        print(f"containers matching {container_name_substring}: {matching_containers}")
        if matching_containers:
            for container in matching_containers:
                container.remove()

    def build_concierge_bot(self) -> None:
        self.client.images.build(path=self.slurk_bots_path, dockerfile="concierge/Dockerfile",
                                 tag="slurk/concierge-bot", rm=True)

    def run_concierge_bot(self, concierge_token, concierge_id) -> None:
        environment = {"SLURK_TOKEN": concierge_token,
                       "SLURK_USER": concierge_id,
                       "SLURK_PORT": PORT,
                       "SLURK_PREFIX": PREFIX}
        try:
            self.client.containers.run("slurk/concierge-bot",
                                   detach=True,
                                   environment=environment,
                                   name="concierge-bot",
                                   network="host")
        except docker.errors.APIError:
            print(self.client.containers.list())
            raise

    def build_qasum_bot(self) -> None:
        self.client.images.build(path=self.slurk_bots_path, dockerfile="qasum/Dockerfile", tag="slurk/qasum-bot",
                                 rm=True)

    def run_qasum_bot(self, qasum_token, qasum_id, waiting_room_id, qasum_task_id) -> None:
        environment = {"SLURK_TOKEN": qasum_token,
                       "SLURK_USER": qasum_id,
                       "SLURK_WAITING_ROOM": waiting_room_id,
                       "QASUM_TASK_ID": qasum_task_id,
                       "SLURK_PORT": PORT,
                       "SLURK_PREFIX": PREFIX}
        self.client.containers.run("slurk/qasum-bot",
                                   detach=True,
                                   environment=environment,
                                   name="qasum-bot",
                                   network="host")


arg_parser = argparse.ArgumentParser(prog=__file__)
arg_parser.add_argument("participant_tokens", type=str,
                        help="filepath for the participant-tokens.csv file we're reloading the bots for")
arg_parser.add_argument("--waiting_room", type=int, default=1,
                        help="integer ID for the base waiting room for the experiment")
arg_parser.add_argument("--docker_host", type=str, default=None,
                        help="host for the Docker Engine daemon; client required for ssh connection")
arg_parser.add_argument("--slurk_bots_dir", type=str, default=None,
                        help="path to use when running docker build")


if __name__ == "__main__":
    args = arg_parser.parse_args()
    participant_tokens = set(read_participant_tokens_csv(args.participant_tokens))
    # Check if slurk container is running
    print("checking if slurk is running")
    dm = DockerManager(args.docker_host, args.slurk_bots_dir)
    if not dm.check_container('slurk', 'running'):
        raise RuntimeError("slurk server not currently running on the docker host")

    # Get the big list of all the tokens in the slurk DB
    print("fetching currently valid tokens")
    server_tokens = get_token_info()
    # Select only those entries corresponding to participants
    matched_data = [x for x in server_tokens if x.get("id") in participant_tokens]
    # Get room & task assignments
    tasks = set([x.get('task_id') for x in matched_data])
    rooms = set([x.get('room_id') for x in matched_data])
    print(f"tasks found: {tasks}")
    print(f"rooms found: {rooms}")

    if len(tasks) == 1:
        task_id = tasks.pop()

        # restart bots
        print("restarting bots")
        for bot in ('qasum-bot', 'concierge-bot'):
            dm.kill_container_if_running(bot)
            dm.remove_container_if_exists(bot)
        dm.build_concierge_bot()
        dm.build_qasum_bot()
        # Add bots to initial waiting room #1 with unlimited registrations
        # get bot waiting room tokens
        concierge_token = create_room_token(args.waiting_room,
                                            "concierge/concierge_bot_permissions.json",
                                            -1,
                                            None)
        qasum_token = create_room_token(args.waiting_room,
                                        "qasum/data/qasum_bot_permissions.json",
                                        -1,
                                        None)
        # create new bot users
        concierge_id = create_user("ConciergeBot", concierge_token)
        qasum_id = create_user("QASumBot", qasum_token)
        # run docker containers from the new images
        dm.run_concierge_bot(concierge_token, concierge_id)
        dm.run_qasum_bot(qasum_token, qasum_id, args.waiting_room, task_id)

        print("adding bots to rooms")
        # add bots to the rooms
        for room_id in rooms:
            print(f"for room {room_id}")
            print(submit_api(f"/users/{concierge_id}/rooms/{room_id}"))
            print(submit_api(f"/users/{qasum_id}/rooms/{room_id}"))
