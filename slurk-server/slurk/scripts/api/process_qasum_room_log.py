"""
Script for processing a JSON file of logs from a QASum experiment.

What do we want to capture?
- which role names each user had
- relative timestamps to first join
- join events
- leave events
- messages between the users
- messages to individual users
- when content-areas update to display to users
  - what is being displayed
- when conversations end
- when summaries end
- when the task ends
- which messages contain the summaries
- which messages need to be flagged as meta

This output format should work: timestamp, user_id, receiver_id, event_type, event_content, flags
"""

import argparse
import csv
import datetime
import json
import os
import pprint

import query_api_lib as qal

pprinter = pprint.PrettyPrinter(indent=2)


def strip_whitespace(chatlog_df):
    chatlog_df['message'] = chatlog_df['message'].str.strip().str.replace("\n", " ")
    return chatlog_df


def get_user_utterances(chatlog_df):
    return chatlog_df[~chatlog_df['sender_name'].isin(("QASumBot", "ConciergeBot"))]


def sort_logs(json_qasum_log):
    return sorted(json_qasum_log, key=lambda x: x['date_created'])


def extract_conversations(json_qasum_log):
    conversations = []
    curr_convo = []
    for event in json_qasum_log:
        if event.get('data') is not None:
            if event.get('data').get('message') is not None:
                if event.get('data').get('message') == 'Math fhèin! Tòisichidh an còmhradh a-nis.':
                    # Task starting, everything before this is banter or onboarding
                    conversations.append(curr_convo)
                    curr_convo = []
                elif event.get('data').get(
                        'message') == 'Ceart gu leòr, feuch an toir thu geàrr-chunntas **a-mhàin** air an fhiosrachadh mun taisbeanadh **air an do bhruidhinn thu nur còmhradh**.':
                    # Convo over, moving on to summarisation
                    conversations.append(curr_convo)
                    curr_convo = []
                elif event.get('data').get('message') == 'Ceart gu leòr, tha sinn ag ullachadh an ath thaisbeanadh...':
                    # Summaries complete, moving to next exhibit
                    conversations.append(curr_convo)
                    curr_convo = []
            if event.get('data').get('id') == 'content-area':
                event['data']['text'] = event['data']['text'].split("</h1>")[0]
        curr_convo.append(event)
    conversations.append(curr_convo)
    return conversations


def pretty_print_room_log_sections(room_log) -> None:
    """
    List of lists of log events
    """
    for idx, section in enumerate(room_log):
        print(f"Section {idx}")
        for event in section:
            pprinter.pprint(event)
        print("----")
        print()


cached_usernames = {}


def query_usernames_lazy(user_id):
    if user_id not in cached_usernames:
        cached_usernames[user_id] = qal.query_api(f"users/{user_id}")['name']
    return cached_usernames[user_id]


arg_parser = argparse.ArgumentParser(__doc__)
arg_parser.add_argument("args.json_dir", type=str)
arg_parser.add_argument("args.output_dir", type=str)


if __name__ == "__main__":
    args = arg_parser.parse_args()
    files = os.listdir(args.json_dir)
    json_data = {}
    for filename in [fn for fn in files if fn.endswith(".json")]:  # and fn.split("_")[2][:-5] in GOOD_LOGS]:
        with open(os.path.join(args.json_dir, filename), 'r') as json_file:
            json_data[filename] = json.load(json_file)
    # assert len(json_data) == 21

    room_256 = extract_conversations(json_data['chatlog_room_256.json'])
    pretty_print_room_log_sections(room_256)

    for log in json_data:
        json_data[log] = sort_logs(json_data[log])
        curr_entries = []
        start_time = datetime.datetime.fromisoformat(json_data[log][0]['date_created'])
        room_id = json_data[log][0]['room_id']
        for entry in json_data[log]:
            event_time = datetime.datetime.fromisoformat(entry['date_created'])
            rel_time = event_time - start_time
            rel_time = rel_time.total_seconds()
            event_type = entry['event']
            user_id = entry['user_id']
            receiver_id = None
            event_content = None
            flags = None
            if event_type == 'text_message':
                receiver_id = entry['receiver_id']
                event_content = entry['data']['message'].strip()
                if event_content == 'Math fhèin! Tòisichidh an còmhradh a-nis.':
                    # Task starting, everything before this is banter or onboarding
                    flags = 'task_start'
                elif event_content == 'Ceart gu leòr, feuch an toir thu geàrr-chunntas **a-mhàin** air an fhiosrachadh mun taisbeanadh **air an do bhruidhinn thu nur còmhradh**.':
                    # Convo over, moving on to summarisation
                    flags = 'summary_start'
                elif event_content == 'Ceart gu leòr, tha sinn ag ullachadh an ath thaisbeanadh...':
                    # Summaries complete, moving to next exhibit
                    flags = 'task_start'
                elif event_content == 'Tha an sgrùdadh seachad! Tapadh leat airson a dhol an sàs ann!':
                    # Whole study complete! Give out tokens and close
                    flags = 'task_finish'
            elif event_type == 'set_html':
                if entry['data']['id'] == 'content-area':
                    event_content = entry['data']['text'].split("</h1>")[0].split('">')[1]
            elif event_type == 'command':
                event_content = entry['data']['command']
            user_name = "(slurk server)" if user_id is None else query_usernames_lazy(user_id)
            receiver_name = "All" if receiver_id is None else query_usernames_lazy(receiver_id)
            curr_entries.append([rel_time, event_type, user_name, receiver_name, event_content, flags])
        with open(os.path.join(args.output_dir, f"chatlog_room_{room_id}.csv"), 'w') as output_file:
            csv_writer = csv.writer(output_file)
            csv_writer.writerows(curr_entries)
