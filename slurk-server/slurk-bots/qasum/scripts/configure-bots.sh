#/usr/bin/env bash
set -euo pipefail

# Expects that the slurk and database docker containers are already running.
# Expected environment variables
# SLURK_DOCKER
# SLURK_PORT
# SLURK_PREFIX


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

# These assume we are in the slurk-bots root directory
docker build --tag "slurk/qasum-bot" -f qasum/Dockerfile .
docker build --tag "slurk/concierge-bot" -f concierge/Dockerfile .

# All the commands below assume we are in the slurk root directory
PREV_WD=${PWD}
cd ../slurk

echo "Reading the SLURK_TOKEN from the docker logs..."
export SLURK_TOKEN=$(check_response scripts/read_admin_token.sh)
echo "Admin Token:"
echo "  ${SLURK_TOKEN}"

echo "Creating the waiting room layout..."
# TODO see if we can avoid recreating identical layouts?
WAITING_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/concierge/waiting_room_layout.json | jq .id)
echo "Waiting Room Layout Id:"
echo "  ${WAITING_ROOM_LAYOUT}"
echo "Creating the first waiting room to initialise bots..."
WAITING_ROOM=$(check_response scripts/create_room.sh "${WAITING_ROOM_LAYOUT}" | jq .id)
echo "Waiting Room Id:"
echo "  ${WAITING_ROOM}"

echo "Creating the task room layout for QASumBot"
TASK_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/qasum/data/task_room_layout.json | jq .id)
echo "Task Room Layout Id:"
echo "  ${TASK_ROOM_LAYOUT}"

echo "Creating the QASum task (2 participants per room)"
# args are name, num participants, and layout ID
TASK_ID=$(check_response scripts/create_task.sh  "QASum Task" 2 "${TASK_ROOM_LAYOUT}" | jq .id)
echo "Task Id:"
echo "  ${TASK_ID}"

echo "Creating tokens for the ConciergeBot"
CONCIERGE_BOT_TOKEN=$(check_response scripts/create_room_token.sh "${WAITING_ROOM}" ../slurk-bots/concierge/concierge_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "Concierge Bot Token:"
echo "  ${CONCIERGE_BOT_TOKEN}"
CONCIERGE_BOT=$(check_response scripts/create_user.sh "ConciergeBot" "${CONCIERGE_BOT_TOKEN}" | jq .id)
echo "Concierge Bot Id:"
echo "  ${CONCIERGE_BOT}"
echo "Launching the ConciergeBot docker container..."
docker run --name="concierge-bot" -e SLURK_TOKEN="${CONCIERGE_BOT_TOKEN}" -e SLURK_USER="${CONCIERGE_BOT}" -e SLURK_PORT="${SLURK_PORT}" -e SLURK_PREFIX="${SLURK_PREFIX}" --net="host" slurk/concierge-bot &
sleep 5

echo "Creating tokens for the QASumBot..."
QASUM_BOT_TOKEN=$(check_response scripts/create_room_token.sh "${WAITING_ROOM}" ../slurk-bots/qasum/data/qasum_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "QASum Bot Token: "
echo "  ${QASUM_BOT_TOKEN}"
QASUM_BOT=$(check_response scripts/create_user.sh "QASumBot" "${QASUM_BOT_TOKEN}" | jq .id)
echo "QASum Bot Id:"
echo "  ${QASUM_BOT}"
docker run --name="qasum-bot" -e SLURK_TOKEN="${QASUM_BOT_TOKEN}" -e SLURK_USER="${QASUM_BOT}" -e SLURK_WAITING_ROOM="${WAITING_ROOM}" -e QASUM_TASK_ID="${TASK_ID}" -e SLURK_PORT="${SLURK_PORT}" -e SLURK_PREFIX="${SLURK_PREFIX}" --net="host" slurk/qasum-bot &
sleep 5

cd "${PREV_WD}"


echo "To create rooms and user tokens for an experiment using these bots, run:"
echo "./qasum/scripts/create-rooms-and-user-tokens.sh ${WAITING_ROOM_LAYOUT} ${TASK_ID} ${CONCIERGE_BOT} ${QASUM_BOT} 120 participant-tokens.csv"
echo ""
echo "120 is the number of participants, participant-tokens.csv is the output file for the pairs of participants' tokens"
echo "You will need to `export SLURK_TOKEN=${SLURK_TOKEN}` before running the above script"