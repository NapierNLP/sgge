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
docker build --tag "slurk/qasum-bot" -f qasum/Dockerfile .
docker build --tag "slurk/concierge-bot" -f concierge/Dockerfile .

# run slurk
cd ../slurk
docker build --tag="slurk/server" -f Dockerfile .
export SLURK_DOCKER=slurk
export SLURK_PORT=${SLURK_PORT:-8080}
export SLURK_PREFIX=${SLURK_PREFIX:-/chat}
scripts/start_server.sh
sleep 5

# create admin token
export SLURK_TOKEN=$(check_response scripts/read_admin_token.sh)
echo "Admin Token:"
echo "  ${SLURK_TOKEN}"

# create waiting room + layout
WAITING_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/concierge/waiting_room_layout.json | jq .id)
echo "Waiting Room Layout Id:"
echo "  ${WAITING_ROOM_LAYOUT}"
WAITING_ROOM=$(check_response scripts/create_room.sh ${WAITING_ROOM_LAYOUT} | jq .id)
echo "Waiting Room Id:"
echo "  ${WAITING_ROOM}"

# create task room layout
TASK_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/qasum/data/task_room_layout.json | jq .id)
echo "Task Room Layout Id:"
echo "  ${TASK_ROOM_LAYOUT}"

# create qasum task
# args are name, num participants, and layout ID
TASK_ID=$(check_response scripts/create_task.sh  "QASum Task" 2 "$TASK_ROOM_LAYOUT" | jq .id)
echo "Task Id:"
echo "  ${TASK_ID}"

# create concierge bot
CONCIERGE_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/concierge/concierge_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "Concierge Bot Token:"
echo "  ${CONCIERGE_BOT_TOKEN}"
CONCIERGE_BOT=$(check_response scripts/create_user.sh "ConciergeBot" $CONCIERGE_BOT_TOKEN | jq .id)
echo "Concierge Bot Id:"
echo "  ${CONCIERGE_BOT}"
docker run --name="concierge-bot" -e SLURK_TOKEN="$CONCIERGE_BOT_TOKEN" -e SLURK_USER=$CONCIERGE_BOT -e SLURK_PORT=$SLURK_PORT -e SLURK_PREFIX=${SLURK_PREFIX} --net="host" slurk/concierge-bot &
sleep 5

# create cola bot
QASUM_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/qasum/data/qasum_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "QASum Bot Token: "
echo "  ${QASUM_BOT_TOKEN}"
QASUM_BOT=$(check_response scripts/create_user.sh "QASumBot" "$QASUM_BOT_TOKEN" | jq .id)
echo "QASum Bot Id:"
echo "  ${QASUM_BOT}"
docker run --name="qasum-bot" -e SLURK_TOKEN=$QASUM_BOT_TOKEN -e SLURK_USER=$QASUM_BOT -e SLURK_WAITING_ROOM=$WAITING_ROOM -e QASUM_TASK_ID=$TASK_ID -e SLURK_PORT=$SLURK_PORT -e SLURK_PREFIX=${SLURK_PREFIX} --net="host" slurk/qasum-bot &
sleep 5

# create two users
echo "User tokens:"
USER1=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/qasum/data/qasum_user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "  ${USER1}"
USER2=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/qasum/data/qasum_user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "  ${USER2}"

LOCALHOST="http://localhost:${SLURK_PORT}"
NAPIERNLG="https://nlg.napier.ac.uk"
USER1_SLUG="${SLURK_PREFIX}/login/?token=${USER1}&name=(QTesting000)%20R2"
USER2_SLUG="${SLURK_PREFIX}/login/?token=${USER2}&name=(RTesting000)%20D2"

echo "Links for those two users on localhost:"
echo ${LOCALHOST}${USER1_SLUG}
echo ${LOCALHOST}${USER2_SLUG}

cd ../slurk-bots
