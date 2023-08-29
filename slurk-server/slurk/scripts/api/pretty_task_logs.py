import csv
import json
import logging

import argparse
import sys

import requests

from openpyxl import Workbook

import query_api_lib as qal


def read_participant_tokens_csv(filename):
    participant_tokens = []
    with open(filename, 'r') as participant_tokens_file:
        reader = csv.reader(participant_tokens_file)
        for line in reader:
            for entry in line:
                participant_tokens.append(entry)
    return participant_tokens


def get_participant_tasks(participant_tokens):
    server_tokens = qal.query_api('tokens')
    # Select only those entries corresponding to participants
    matched_data = [x for x in server_tokens if x.get("id") in participant_tokens]
    # Check room assignments
    return set([x.get('task_id') for x in matched_data])


def extract_message_data_from_log_event(log_event):
    user_name = qal.query_api(f"users/{log_event['user_id']}")['name']
    receiver_id = log_event['receiver_id']
    receiver_name = qal.query_api(f"users/{receiver_id}")['name'] if receiver_id is not None else "All"
    return log_event['date_created'], user_name, receiver_name, log_event['data']['message'], ''


def get_room_message_events(room_id):
    log_events = qal.query_api(f"logs", params={'room_id': room_id})
    return sorted([event for event in log_events if 'message' in event['event']],
                  key=lambda x: x['date_created'])


def save_logs_for_room(room_id, filepath):
    logging.debug(f"Writing log for Room ID: {room_id}")
    wb = Workbook()
    ws = wb.active
    ws.append(["date_created", "sender_name", "receiver_name", "message", "editor_comments"])
    message_events = get_room_message_events(room_id)
    for message_event in message_events:
        ws.append(extract_message_data_from_log_event(message_event))
    wb.save(filepath)


def get_user_ids_by_token(token):
    users = qal.query_api(f"users", params={"token_id": token})
    user_ids = set([user['id'] for user in users])
    for user_id in user_ids:
        logging.info(f"Token {token} matched user id {user_id}")
    return user_ids


def get_rooms_by_user_id(user_id):
    rooms_a = []
    rooms_a.extend(qal.query_api(f"users/{user_id}/rooms"))
    try:
        return set([room['id'] for room in rooms_a])
    except:
        print(rooms_a)
        raise


def get_userpair_rooms_by_user_tokens(token_a, token_b, only_both=True):
    user_ids_a = get_user_ids_by_token(token_a)
    room_ids_a = set()
    for user_id in user_ids_a:
        room_ids_a.update(get_rooms_by_user_id(user_id))
    user_ids_b = get_user_ids_by_token(token_b)
    room_ids_b = set()
    for user_id in user_ids_b:
        room_ids_b.update(get_rooms_by_user_id(user_id))
    if only_both:
        return room_ids_a.intersection(room_ids_b)
    else:
        return room_ids_a.union(room_ids_b)



argument_parser = argparse.ArgumentParser(description=__doc__)
argument_parser.add_argument("--logfile", type=str, default=None,
                                               help="a logfile to use instead of sending a fresh query to the server")
argument_parser.add_argument("--output", type=str, default=None,
                             help="pattern for filenames incl. dirs; default, print logs to stdout")
argument_parser.add_argument("--debug_level", type=str, default=logging.CRITICAL,
                             help="python logging level to use")
argument_parser.add_argument("--nochat_ids", type=str, default="",
                             help="comma separated list of room_ids which we already know do not contain chat info")
subparsers = argument_parser.add_subparsers()
parsers_pair = subparsers.add_parser("pair")
parsers_pair.add_argument("token_a", type=str)
parsers_pair.add_argument("token_b", type=str)
parsers_file = subparsers.add_parser("file")
parsers_file.add_argument("tokens_file", type=str)


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    args = argument_parser.parse_args()
    print(args)
    if args.logfile is None:
        logs = qal.query_api('logs')
    elif args.logfile == "-":
        logs = json.loads(sys.stdin)
    else:
        logs = json.load(args.logfile)
    if logs is None:
        raise ValueError("`logs` are None for some reason???")

    if 'token_a' in args:
        token_pairs = [{args.token_a, args.token_b}]
    elif 'tokens_file' in args:
        token_pairs = []
        with open(args.tokens_file, 'r') as tokens_file:
            csv_reader = csv.reader(tokens_file)
            for line in csv_reader:
                token_pairs.append(line)
    else:
        raise ValueError("No tokens specified!")

    if args.nochat_ids:
        nochat_ids = set([int(x) for x in args.nochat_ids.split(",")])
    else:
        nochat_ids = set()

    for token_pair in token_pairs:
        logging.debug(token_pair)
        token_ids = get_user_ids_by_token(token_pair.pop()).union(get_user_ids_by_token(token_pair.pop()))
        logging.debug(token_ids)
        room_ids = set()
        for log_event in logs:
            if log_event['user_id'] in token_ids:
                room_ids.add(log_event['room_id'])
        logging.debug(room_ids)
        if None in room_ids:
            room_ids.discard(None)
        room_ids.difference_update(nochat_ids)
        if args.output is None:
            print('here')
            for room_id in room_ids:
                print(f"Message logs for {room_id}")
                for event in get_room_message_events(room_id):
                    print("\t".join(extract_message_data_from_log_event(event)))
        else:
            for room_id in room_ids:
                filepath = args.output.replace("ROOM_ID", str(room_id))
                save_logs_for_room(room_id, filepath)
