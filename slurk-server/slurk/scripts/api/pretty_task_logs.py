from collections import defaultdict
from typing import Dict, Optional

import argparse
import csv
import json
import logging
import sys

from openpyxl import Workbook

import query_api_lib as qal


class CachingLogProcessor(object):
    def __init__(self):
        self.tokens_tasks: Dict[str, str] = {}
        self.tokens_user_ids = defaultdict(set)
        # Keys are user_ids
        # Values are dicts with keys: rooms, name
        self.participants: Dict[str, Dict[str, str]] = defaultdict(dict)

    def get_username(self, user_id):
        if user_id in self.participants:
            user_name = self.participants[user_id]['name']
        else:
            user_name = qal.query_api(f"users/{user_id}")['name']
            self.participants[user_id]['name'] = user_name
        return user_name

    def get_user_ids(self, token):
        if token not in self.tokens_user_ids:
            users = qal.query_api(f"users", params={"token_id": token})
            self.tokens_user_ids[token] = set([user['id'] for user in users])
        return self.tokens_user_ids[token]

    def get_participant_tasks(self, participant_tokens):
        server_tokens = qal.query_api('tokens')
        # Select only those entries corresponding to participants
        matched_data = []
        for x in server_tokens:
            if x.get("id") in participant_tokens:
                self.tokens_tasks[x['id']] = x.get('task_id')
                matched_data.append(x)
        # Check room assignments
        return set([x.get('task_id') for x in matched_data])

    def extract_message_data_from_log_event(self, log_event):
        user_name = self.get_username(log_event['user_id'])
        receiver_id = log_event['receiver_id']
        receiver_name = self.get_username(receiver_id) if receiver_id is not None else "All"
        return log_event['date_created'], user_name, receiver_name, log_event['data']['message'], ''

    def get_user_ids_by_token(self, token) -> set[str]:
        user_ids = self.get_user_ids(token)
        for user_id in user_ids:
            logging.info(f"Token {token} matched user id {user_id}")
        return user_ids

    def get_userpair_rooms_by_user_tokens(self, token_a, token_b, only_both=True):
        user_ids_a = self.get_user_ids_by_token(token_a)
        room_ids_a = set()
        for user_id in user_ids_a:
            room_ids_a.update(self.get_rooms_by_user_id(user_id))
        user_ids_b = self.get_user_ids_by_token(token_b)
        room_ids_b = set()
        for user_id in user_ids_b:
            room_ids_b.update(self.get_rooms_by_user_id(user_id))
        if only_both:
            return room_ids_a.intersection(room_ids_b)
        else:
            return room_ids_a.union(room_ids_b)

    def save_logs_for_room(self, room_id, filepath):
        logging.debug(f"Writing log for Room ID: {room_id}")
        wb = Workbook()
        ws = wb.active
        ws.append(["date_created", "sender_name", "receiver_name", "message", "editor_comments"])
        message_events = get_room_message_events(room_id)
        for message_event in message_events:
            ws.append(self.extract_message_data_from_log_event(message_event))
        wb.save(filepath)

    def get_rooms_by_user_id(self, user_id):
        if user_id not in self.participants:
            rooms_a = []
            rooms_a.extend(qal.query_api(f"users/{user_id}/rooms"))
            self.participants[user_id]['rooms'] = set([room['id'] for room in rooms_a])
        return self.participants[user_id]['rooms']


def read_participant_tokens_csv(filename):
    participant_tokens = []
    with open(filename, 'r') as participant_tokens_file:
        reader = csv.reader(participant_tokens_file)
        for line in reader:
            for entry in line:
                participant_tokens.append(entry)
    return participant_tokens


def get_room_message_events(room_id):
    log_events = qal.query_api(f"logs", params={'room_id': room_id})
    return sorted([event for event in log_events if 'message' in event['event']],
                  key=lambda x: x['date_created'])


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


def logs_from_logfile(logfile: Optional[str]):
    if args.logfile is None:
        logs = qal.query_api('logs')
    elif args.logfile == "-":
        logs = json.loads(sys.stdin)
    else:
        logs = json.load(args.logfile)
    return logs


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    args = argument_parser.parse_args()
    logging.info(args)

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

    log_processor = CachingLogProcessor()

    for token_pair in token_pairs:
        logging.debug(token_pair)
        token_ids = log_processor.get_user_ids_by_token(token_pair.pop()).union(log_processor.get_user_ids_by_token(token_pair.pop()))
        logging.debug(token_ids)

        room_ids = set()
        for token_id in token_ids:
            logs = qal.query_api('logs', params={"user_id": token_id})

            for log_event in logs:
                if log_event['user_id'] in token_ids:
                    room_ids.add(log_event['room_id'])

        logging.debug(room_ids)

        if None in room_ids:
            room_ids.discard(None)

        room_ids.difference_update(nochat_ids)

        if args.output is None:
            for room_id in room_ids:
                print(f"Message logs for {room_id}")
                for event in get_room_message_events(room_id):
                    print("\t".join(log_processor.extract_message_data_from_log_event(event)))
        else:
            for room_id in room_ids:
                filepath = args.output.replace("ROOM_ID", str(room_id))
                log_processor.save_logs_for_room(room_id, filepath)
