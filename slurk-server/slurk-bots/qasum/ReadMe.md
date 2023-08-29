# QASum Bot: Question Answering Chat with Summary

Two speakers participate in a question-answering conversation, 
with one playing the role of the questioner and another the role of the responder.
The questioner sees a set of named entities and unusual phrases along with a depiction of an artefact (a piece of art or cultural exhibit).
The responder sees the same depiction along with detailed background information, 
such as metadata or natural language descriptions of the artefact.

This task can be divided into the following task phases:
1. Waiting for both players to get ready.
2. Presenting each of the two players their information view.
3. Let both players discuss.
4. Record when the conversation is complete.
5. Ask the participants to summarise the content of their conversation.
6. Repeating 2-5 until they have gone through their shared item list.

For this purpose the following commands are defined to manage the transition between task phases:
+ `/ready` : Both players have to send this command in order to move from phase 1 to phase 2
+ `/done` : Indicates that the players think the conversation has come to an end.
+ `/next`: Both players have to send this command to move from summarising one discussion to the next exhibit.
 
## Run the Bot

### Bare bones operation

To run the bot, you can run the following command:

```bash
docker run -e SLURK_TOKEN=$QASUM_BOT_TOKEN -e SLURK_USER=$QASUM_BOT -e SLURK_WAITING_ROOM=$WAITING_ROOM -e QASUM_TASK_ID=$TASK_ID -e SLURK_PORT=5000 --net="host" slurk/qasum-bot &
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_html_message` and `send_privately`.
Users assigned to this task need at least the rights: `send_message` and `send_command`
Please refer to the slurk documentation for more detailed information.

### Dev configuration with Docker

Note that you may need to remove previous containers/images for slurk, concierge-bot, and qasum-bot to run this command. You can adapt the script `qasum/scripts/reset-docker.sh` for this purpose.

```bash
cd ${SLURK_SERVER}
cd slurk-bots
./qasum/scripts/setup.sh
```

### Using Docker to deploy the bot for an experiment
To launch slurk and the bots for our experiment, we run:

```bash
cd ${SLURK_SERVER}
# Start the server and the database
docker compose up [-d]
# Set production environment variables
for LINE in $(cat slurk_production.env); do export ${LINE}; done
cd slurk-bots
# Launch the ConciergeBot and QASumBot
./qasum/scripts/configure-bots.sh
```

At that point we should be able to check that all 4 containers are running with `docker ps`. For example:

```bash
(slurk-lfXOj6PB-py3.9) [howcroft@enunlg slurk-bots]$ docker ps
CONTAINER ID   IMAGE                 COMMAND                  CREATED          STATUS          PORTS                                       NAMES
488644eb8ee0   slurk/qasum-bot       "python main.py"         7 seconds ago    Up 7 seconds                                                qasum-bot
10ba31e9f3d0   slurk/concierge-bot   "python concierge.py"    12 seconds ago   Up 12 seconds                                               concierge-bot
fd310f6b0841   postgres              "docker-entrypoint.s…"   4 hours ago      Up 4 hours      0.0.0.0:5432->5432/tcp, :::5432->5432/tcp   slurk-server-db-1
4d3be5eade41   slurk/server          "gunicorn -b :80 -k …"   4 hours ago      Up 4 hours      0.0.0.0:8080->80/tcp, :::8080->80/tcp       slurk
```

Now we are able to create rooms and users for the experiment, using values generated when running `configure-bots.sh`. For example,

```bash
./qasum/scripts/create-rooms-and-user-tokens.sh 4 4 7 8 120 participant-tokens.csv
```

**Note**: You need to make sure that the admin token is set before running this script. Aside from that, you can copy the `create-rooms-and-user-tokens.sh` command from the output of `configure-bots.sh`

Where

```bash
export SLURK_TOKEN=$SLURK_TOKEN # sets the admin token
./qasum/scripts/create-rooms-and-user-tokens.sh ${WAITING_ROOM} ${TASK_ID} ${CONCIERGE_BOT} ${QASUM_BOT} 120 participant-tokens.csv
# and 120 is the number of participants
# participant-tokens.csv is an output file for the list of pairs of tokens
```

We can now generate the lists each user token is assigned to with:

```bash
python qasum/lib/experiment_data.py --protocol https --hostname nlg.napier.ac.uk qasum/data/exhibit_data.csv 6 participant-tokens.csv
```

where 6 is the number of items each pair of participants is discussing. This will set us up with a new CSV file containing the URLs for questioners and responders to use as well as the item lists for each experiment session.

## Modifications

Under `lib/config.py` you find a number of global variables that define experiment settings as well as short descriptions of their effect on the experiment.

**NB**: the following applies to the original DiTo task

Image pairs for the task should be specified one pair per line
in the `image_data.csv`. The components of a pair are separated by
a comma followed by no whitespace.

## Metadata

Forked from dito Feb 2022 by dmhowcroft.
Last edited Aug 2022 by dmhowcroft.
