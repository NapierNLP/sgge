#!/usr/bin/env bash
set -eu

function errcho {
    echo "$@" 1>&2
}

function check_response {
    response=$("$@")
    if [ -z "$response" ]; then
        errcho "Unexpected error for call to: $1"
        exit 1
    fi
    echo "$response"
}

# build docker images for bots
cd ../slurk-bots
docker build --tag "slurk/dito-bot" -f dito/Dockerfile .
docker build --tag "slurk/concierge-bot" -f concierge/Dockerfile .

# run slurk
cd ../slurk
docker build --tag="slurk/server" -f Dockerfile .
export SLURK_DOCKER=slurk
scripts/start_server.sh
sleep 5

# create admin token
SLURK_TOKEN=$(check_response scripts/read_admin_token.sh)
echo "Admin Token:"
echo $SLURK_TOKEN

# create waiting room + layout
WAITING_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/concierge/waiting_room_layout.json | jq .id)
echo "Waiting Room Layout Id:"
echo $WAITING_ROOM_LAYOUT
WAITING_ROOM=$(check_response scripts/create_room.sh 1 | jq .id)
echo "Waiting Room Id:"
echo $WAITING_ROOM

# create task room layout
TASK_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/dito/data/task_room_layout.json | jq .id)
echo "Task Room Layout Id:"
echo $TASK_ROOM_LAYOUT

# create dito task
TASK_ID=$(check_response scripts/create_task.sh  "DiTo Task" 2 "$TASK_ROOM_LAYOUT" | jq .id)
echo "Task Id:"
echo $TASK_ID

# create concierge bot
CONCIERGE_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/concierge/concierge_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "Concierge Bot Token:"
echo $CONCIERGE_BOT_TOKEN
CONCIERGE_BOT=$(check_response scripts/create_user.sh "ConciergeBot" $CONCIERGE_BOT_TOKEN | jq .id)
echo "Concierge Bot Id:"
echo $CONCIERGE_BOT
docker run -e SLURK_TOKEN="$CONCIERGE_BOT_TOKEN" -e SLURK_USER=$CONCIERGE_BOT -e SLURK_PORT=5000 --net="host" slurk/concierge-bot &
sleep 5

# create cola bot
DITO_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/dito/data/dito_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "DiTo Bot Token: "
echo $DITO_BOT_TOKEN
DITO_BOT=$(check_response scripts/create_user.sh "DiToBot" "$DITO_BOT_TOKEN" | jq .id)
echo "DiTo Bot Id:"
echo $DITO_BOT
docker run -e SLURK_TOKEN=$DITO_BOT_TOKEN -e SLURK_USER=$DITO_BOT -e SLURK_WAITING_ROOM=$WAITING_ROOM -e DITO_TASK_ID=$TASK_ID -e SLURK_PORT=5000 --net="host" slurk/dito-bot &
sleep 5

# create two users
USER1=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/dito/data/dito_user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo $USER1
USER2=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/dito/data/dito_user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo $USER2

cd ../slurk-bots
