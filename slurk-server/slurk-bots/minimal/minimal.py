import argparse
import logging
import os

import requests
import socketio


LOG = logging.getLogger(__name__)


class MinimalBot:
    sio = socketio.Client(logger=True)
    user_id = None

    def __init__(self, token, user, host, port):
        """Designing an experiment in slurk usually involves
        writing one or more bots.
        This bot serves as a minimal example demonstrating
        a subset of the most import functionalities available.

        :param token: A uuid; a string following the same pattern
            as `0c45b30f-d049-43d1-b80d-e3c3a3ca22a0`
        :type token: str
        :param user: ID of a `User` object that was created with
        the token.
        :type user: int
        :param host: Full URL including protocol and hostname.
        :type host: str
        :param port: Port used by the slurk chat server.
            If you use a docker container that publishes an
            internal port to another port on the docker host,
            specify the latter.
        :type port: int
        """
        self.token = token
        self.user = user
        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"
        # register all event handlers
        self.register_callbacks()

    def run(self):
        # establish a connection to the server
        self.sio.connect(
            self.uri,
            headers={"Authorization": self.token, "user": self.user},
            namespaces="/",
        )
        # wait until the connection with the server ends
        self.sio.wait()

    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            # get the id of the room that was entered
            room_id = data["room"]
            # get the id of the user that just joined a room
            user_id = data["user"]
            LOG.debug(f"User {user_id} entered the room {room_id}")

            # based on the id retrieve additional information
            # with a running slurk server all such requests possible can
            # be looked at under http://localhost/rapidoc
            response = requests.get(
                f"{self.uri}/users/{user_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )

            # verify that the request was successful
            if not response.ok:
                LOG.error(
                    f"Could not get user details due to status {response.status_code}."
                )
            else:
                # read out information delivered with the response
                user = response.json()
                self.sio.emit(
                    "text", {"message": f'Hi^o^ I am a {user["name"]}!', "room": room_id}
                )

            # retrieve all log entries for this room and user
            response = requests.get(
                f"{self.uri}/rooms/{room_id}/users/{user_id}/logs",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                LOG.error(f"Could not get logs due to status {response.status_code}.")
            else:
                logs = response.json()
                for log_entry in logs:
                    logging.info(
                        f'- status: {log_entry["event"]}, data: {log_entry["data"]}'
                    )


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = argparse.ArgumentParser(description="Run Minimal Bot.")

    # collect environment variables as defaults
    if "SLURK_TOKEN" in os.environ:
        token = {"default": os.environ["SLURK_TOKEN"]}
    else:
        token = {"required": True}
    if "SLURK_USER" in os.environ:
        user = {"default": os.environ["SLURK_USER"]}
    else:
        user = {"required": True}
    host = {"default": os.environ.get("SLURK_HOST", "http://localhost")}
    port = {"default": os.environ.get("SLURK_PORT")}

    # register commandline arguments
    parser.add_argument(
        "-t", "--token", help="token for logging in as bot (see SERVURL/token)", **token
    )
    parser.add_argument("-u", "--user", help="user id for the bot", **user)
    parser.add_argument(
        "-c", "--host", help="full URL (protocol, hostname) of chat server", **host
    )
    parser.add_argument("-p", "--port", type=int, help="port of chat server", **port)
    args = parser.parse_args()

    # create bot instance
    minimal_bot = MinimalBot(args.token, args.user, args.host, args.port)
    # connect to chat server
    minimal_bot.run()
