#!/usr/bin/env bash

ROOM_ID=$1

while true
do
    ./slurk/scripts/get_logs.sh ${ROOM_ID} | jq '[.[] | select(.event |contains("text_message"))] | sort_by(.date_created) | .[] | .date_created, .user_id, .receiver_id, .data.message' | paste - - - -
    sleep 15
    echo ""
    echo ""
    echo ""
done
