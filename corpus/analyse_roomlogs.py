from collections import Counter
import os

import numpy as np
import pandas as pd


# Previously included rooms which are actually waiting room files: chatlog_room_1.csv chatlog_room_2.csv
# chatlog_room_3.csv chatlog_room_6.csv chatlog_room_7.csv chatlog_room_8.csv chatlog_room_9.csv chatlog_room_10.csv
# chatlog_room_11.csv chatlog_room_12.csv chatlog_room_13.csv chatlog_room_14.csv chatlog_room_15.csv
# chatlog_room_16.csv chatlog_room_17.csv chatlog_room_18.csv chatlog_room_19.csv chatlog_room_20.csv
# chatlog_room_21.csv chatlog_room_24.csv chatlog_room_26.csv chatlog_room_27.csv chatlog_room_28.csv
# chatlog_room_29.csv chatlog_room_32.csv chatlog_room_33.csv chatlog_room_35.csv chatlog_room_36.csv
# chatlog_room_128.csv chatlog_room_148.csv chatlog_room_175.csv

def summary_stats(turns_list, indent="") -> None:
    num_words = 0
    num_messages = 0
    message_lengths = []
    tokens = Counter()
    bigrams = Counter()
    unique_messages = set()
    for turn in turns_list:
        if isinstance(turn, float):
            continue
        msg_tokens = turn.split()
        unique_messages.add(turn)
        num_words += len(msg_tokens)
        message_lengths.append(len(msg_tokens))
        num_messages += 1
        tokens.update(msg_tokens)
        bigrams.update(list(zip(turn.split(), turn.split()[1:])))

    print(f"{indent}Num. unique messages: {len(unique_messages)}")
    print(f"{indent}Num. messages: {num_messages}")
    print(f"{indent}Num. unique words: {len(tokens)}")
    print(f"{indent}Num. words: {num_words}")
    print(f"{indent}Num. unique bigrams: {len(bigrams)}")
    print(f"{indent}Mean message length in words (s.d.): {np.mean(message_lengths)} ({np.std(message_lengths)})")


if __name__ == "__main__":
    roomlogs_dir = "roomlogs"
    # Make output log directories if they don't exist
    os.makedirs("convo_logs", exist_ok=True)
    os.makedirs("summary_logs", exist_ok=True)


    roomlogs_dfs = {}
    room_stats = pd.DataFrame(columns=["task_started", "task_complete", "num_convos", "num_summaries"])

    waiting_room_files = []
    for file in [fn for fn in os.listdir(roomlogs_dir) if fn.endswith("csv")]:
        roomlogs_dfs[file] = pd.read_csv(os.path.join(roomlogs_dir, file))
        roomlogs_dfs[file].columns = ["timestamp", "event_type", "user_id", "receiver_id", "event_content", "flags"]
        started = any(roomlogs_dfs[file]['flags'] == "task_start")
        finished = any(roomlogs_dfs[file]['flags'] == "task_finish")
        participants = set(roomlogs_dfs[file]['user_id']) - set(("(slurk server)", "QASumBot"))
        if "ConciergeBot" in participants:
            print(f"Remove {file} because it is from the Waiting Room, not the Task Room")
            waiting_room_files.append(file)
            del roomlogs_dfs[file]
            continue

        # Exclude shoptalk / meta conversation about the experiment (manually flagged)
        roomlogs_dfs[file] = roomlogs_dfs[file][roomlogs_dfs[file]['flags'] != "meta"]
        roomlogs_dfs[file]['convo_idx'] = (roomlogs_dfs[file]['flags'] == 'task_start').cumsum()
        roomlogs_dfs[file]['summary_idx'] = (roomlogs_dfs[file]['flags'] == 'summary_start').cumsum()
        flag_counts = roomlogs_dfs[file]['flags'].value_counts()
        # Conversations are complete if the summaries begin
        convo_count = flag_counts.loc['task_start'] if "task_start" in flag_counts else 0
        # print(f"{file}\t{started}\t{finished}\t{participants}")
        room_stats.loc[file] = (started, finished, convo_count, None)
    # Let the user know if we found any waiting room files
    if waiting_room_files:
        print("The following files are from the waiting room logs, not task logs.")
        for x in waiting_room_files:
            print(x)
        print("--------------------------------")

    print("Room statistics (dataframe dump)")
    print(room_stats)
    print("--------------------------------")

    complete_enough = room_stats[room_stats['num_convos'] > 0]
    print(f"We found {len(complete_enough)} rooms with at least one conversation")
    print(f"Across all rooms there are {sum(complete_enough['num_convos'])} conversations")
    print("--------------------------------")

    convo_stats = pd.DataFrame(
        columns=["room_id", "convo_idx", "questioner_turns", "responder_turns", "total_turns", "total_duration",
                 "mean_turn_length"])
    summaries_stats = pd.DataFrame(
        columns=["room_id", "convo_idx", "questioner_turns", "responder_turns", "total_turns", "questioner_wordcount",
                 "responder_wordcount", "total_wordcount"])

    convo_texts = pd.DataFrame(columns=["timestamp", "event_type", "user_id", "receiver_id", "event_content", "flags"])
    summary_texts = pd.DataFrame(
        columns=["timestamp", "event_type", "user_id", "receiver_id", "event_content", "flags"])
    for file in complete_enough.index:
        curr_df = roomlogs_dfs[file]
        room_id = file.split("_")[2][:-4]
        for idx, df in curr_df.groupby('convo_idx'):
            if idx != 0:
                df = df[df['event_type'].isin(set(['join', 'set_html', 'text_message']))]
                df = df[df['user_id'] != 'QASumBot']
                df['event_content'] = df['event_content'].fillna("")
                df['flags'] = df['flags'].fillna("")
                df['lowercased'] = df['event_content'].str.lower().str.replace(",", " , ", regex=False).str.replace(".", " . ", regex=False)
                df['message_length'] = df['lowercased'].str.split().apply(len)
                df['ath'] = df['lowercased'].str.match('[ /]*ath')
                df['deiseil'] = df['lowercased'].str.match('[ /]*deiseil')
                df['toiseachadh'] = df['lowercased'].str.match('[ /]*toiseachadh')
                df['command'] = (df['message_length'] == 1) & (df['ath'] | df['deiseil'] | df['toiseachadh'])

                conversation = df[df['convo_idx'] != df['summary_idx']]
                summary = df[df['convo_idx'] == df['summary_idx']]
                summary = summary[summary['command'] == False]

                convo_filename = f"{file[:-4]}_convo-{idx}.csv"
                if len(conversation) > 0:
                    conversation.to_csv(os.path.join('convo_logs', convo_filename))
                summary_filename = f"{file[:-4]}_summary-{idx}.csv"
                if len(summary) > 0:
                    summary.to_csv(os.path.join('summary_logs', summary_filename))

                questioner_turns = conversation[conversation['user_id'].str.contains("Neach-tadhail") & (conversation['command'] == False)]
                responder_turns = conversation[conversation['user_id'].str.contains("Neach-freagairt") & (conversation['command'] == False)]
                participant_turns = conversation[conversation['user_id'].str.contains("Neach") & (conversation['command'] == False)]
                convo_texts = pd.concat((convo_texts, participant_turns[(participant_turns['event_type'] == 'text_message') & (participant_turns['command'] == False)]))

                turn_count = len(participant_turns[participant_turns['event_type'] == 'text_message'])
                convo_start = min(participant_turns['timestamp'])
                convo_finish = max(participant_turns['timestamp'])
                convo_duration = convo_finish - convo_start

                convo_stats.loc[convo_filename] = (room_id, idx, len(questioner_turns), len(responder_turns), len(questioner_turns) + len(responder_turns), convo_finish - convo_start, convo_duration / turn_count)

                questioner_summaries = summary[summary['user_id'].str.contains("Neach-tadhail") & (summary['command'] == False)]
                questioner_summaries = questioner_summaries[questioner_summaries['event_type'] == 'text_message']
                responder_summaries = summary[summary['user_id'].str.contains("Neach-freagairt") & (summary['command'] == False)]
                responder_summaries = responder_summaries[responder_summaries['event_type'] == 'text_message']
                participant_summaries = summary[summary['user_id'].str.contains("Neach") & (summary['command'] == False)]
                summary_texts = pd.concat((summary_texts, participant_summaries[participant_summaries['event_type'] == 'text_message']))

                qs_turns = len(participant_summaries[participant_summaries['user_id'].str.contains("Neach-tadhail")])
                rs_turns = len(participant_summaries[participant_summaries['user_id'].str.contains("Neach-freagairt")])
                qs_length = 0
                for turn in participant_summaries[participant_summaries['user_id'].str.contains("Neach-tadhail")]['lowercased']:
                    qs_length += len(turn.strip().split())
                rs_length = 0
                for turn in participant_summaries[participant_summaries['user_id'].str.contains("Neach-freagairt")]['lowercased']:
                    rs_length += len(turn.strip().split())
                summaries_stats.loc[summary_filename] = (room_id, idx, qs_turns, rs_turns, qs_turns + rs_turns, qs_length, rs_length, qs_length + rs_length)
    convo_stats.to_csv('convo_stats.csv')
    summaries_stats.to_csv('summary_stats.csv')

    print("__________________")
    print(f"Total turns (incl. bots): {sum(convo_stats['total_turns'])}")
    print(f"Mean # of turns (s.d.): {np.mean(convo_stats['total_turns'])} ({np.std(convo_stats['total_turns'])})")
    print(f"Total conversation duration (seconds): {sum(convo_stats['total_duration'])}")
    print(f"Mean conversation duration in seconds (s.d.): {np.mean(convo_stats['total_duration'])} ({np.std(convo_stats['total_duration'])})")
    print(f"Mean turn length in seconds (s.d.): {np.mean(convo_stats['mean_turn_length'])} ({np.std(convo_stats['mean_turn_length'])})")
    print(f"Total turns (participants only): {len(convo_texts)}")
    print("__________________")

    convo_texts['lowercased'] = convo_texts['event_content'].str.lower().str.replace(",", " , ").str.replace(".", " . ")
    turns_list = [turn for turn in convo_texts['lowercased']]

    print("Overall stats for conversations")
    summary_stats(turns_list, "  ")
    print("Questioner stats for conversations")
    summary_stats([turn for turn in convo_texts.loc[convo_texts['user_id'].str.contains("Neach-tadhail"), 'lowercased']], "  ")
    print("Responder stats for conversations")
    summary_stats([turn for turn in convo_texts.loc[convo_texts['user_id'].str.contains("Neach-freagairt"), 'lowercased']], "  ")
    print("__________________")

    summary_texts = summary_texts[summary_texts['user_id'].str.contains("Neach-tadhail") | summary_texts['user_id'].str.contains("Neach-freagairt")]
    print(f"We have {len(summary_texts)} messages sent in summaries in our summary_texts dataframe.")

    questioner_summaries = summary_texts[summary_texts['user_id'].str.contains("Neach-tadhail")]
    responder_summaries = summary_texts[summary_texts['user_id'].str.contains("Neach-freagairt")]
    qs_list = [turn for turn in questioner_summaries['lowercased']]
    rs_list = [turn for turn in responder_summaries['lowercased']]

    print("Overall stats for summaries")
    summary_stats([turn for turn in summary_texts['lowercased']], "  ")
    print("Questioner stats for summaries")
    summary_stats(qs_list, "  ")
    print("Responder stats for summaries")
    summary_stats(rs_list, "  ")

    questioner_summaries = len(summaries_stats[summaries_stats['questioner_turns'] > 0])
    responder_summaries = len(summaries_stats[summaries_stats['responder_turns'] > 0])
    print(f"Num. Questioner Summaries: {questioner_summaries}")
    print(f"Num. Responder Summaries: {responder_summaries}")
