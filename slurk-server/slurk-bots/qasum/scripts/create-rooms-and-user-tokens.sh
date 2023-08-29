#/usr/bin/env bash
set -euo pipefail

# Parameters:
#   ./qasum/scripts/create-rooms-and-user-tokens.sh waiting-room-layout conciergebot-id qasumbot-id [num_rooms]
# Environment variables:
#   SLURK_TOKEN: Token to pass as authorization, defaults to `00000000-0000-0000-0000-000000000000`
#   SLURK_HOST: Host name to use for the request, defaults to `http://localhost`
#   SLURK_PORT: Port to use for the request, defaults to 5000
#   SLURK_PREFIX: subdirectory/prefix following hostname and port to indicate where slurk is being served

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


# All the commands below assume we are in the slurk root directory
PREV_WD=${PWD}
cd ../slurk

WAITING_ROOM_LAYOUT=${1}
TASK_ID=${2}
CONCIERGE_ID=${3}
QASUM_ID=${4}
PARTICIPANT_FILE=${6}
for NUM in $(seq 1 "${5:-5}")
do
  echo "Creating a new waiting room..."
  WAITING_ROOM_ID=$(check_response scripts/create_room.sh "${WAITING_ROOM_LAYOUT}" | jq .id)
  echo "Waiting Room Id:"
  echo "${WAITING_ROOM_ID}"
  echo "Adding ConciergeBot to the new waiting room..."
  CONCIERGE_RESULT=$(check_response scripts/add_user_to_room.sh "${CONCIERGE_ID}" "${WAITING_ROOM_ID}" | jq .id | sed 's/^"\(.*\)"$/\1/')
  echo ${CONCIERGE_RESULT}
  echo "Adding QASumBot to the new waiting room..."
  QASUM_RESULT=$(check_response scripts/add_user_to_room.sh "${QASUM_ID}" "${WAITING_ROOM_ID}" | jq .id | sed 's/^"\(.*\)"$/\1/')
  echo ${QASUM_RESULT}
  echo "Generating participant tokens..."
  USER1=$(check_response scripts/create_room_token.sh "${WAITING_ROOM_ID}" ../slurk-bots/qasum/data/qasum_user_permissions.json -1 "$TASK_ID" | jq .id | sed 's/^"\(.*\)"$/\1/')
  USER2=$(check_response scripts/create_room_token.sh "${WAITING_ROOM_ID}" ../slurk-bots/qasum/data/qasum_user_permissions.json -1 "$TASK_ID" | jq .id | sed 's/^"\(.*\)"$/\1/')
  echo "${USER1},${USER2}" >> ${PREV_WD}/${PARTICIPANT_FILE}
done

cd "${PREV_WD}"
