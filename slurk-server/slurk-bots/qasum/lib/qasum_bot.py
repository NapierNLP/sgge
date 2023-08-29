# -*- coding: utf-8 -*-

# (c) 2022, David M. Howcroft
# (c) 2022, University of Potsdam
"""QASum bot logic including dialog and summarisation phases."""

import logging
import random
import string
from threading import Timer
from time import sleep
from typing import Optional

import requests
import socketio
from thefuzz import fuzz


import lib.config as qasum_config
from lib.experiment_data import ExperimentSessionInfo

LOG = logging.getLogger(__name__)


class RoomTimers:
    def __init__(self):
        """A number of timed events during the experiment session.

        :param ready_timer: Reminds both players that they have to send
            /ready to begin the game if none of them did so, yet.
            If one player already sent /ready then the other player
            is reminded 30s later that they should do so, too.
        :param game_timer: Reminds both players that they should come
            to an end and close their discussion by sending /difference.
        :param done_timer: Resets a sent /difference command for one
            player if their partner did not also sent /difference.
        :param last_answer_timer: Used to end the game if one player
            did not answer for a prolonged time.
        """
        self.ready_timer: Timer = None
        self.game_timer: Timer = None
        self.done_timer: Timer = None
        self.last_answer_timer: Timer = None


class QASumBot:
    sio = socketio.Client(logger=True)
    """The ID of the task the bot is involved in."""
    task_id = None
    """The ID of the room where users for this task are waiting."""
    waiting_room = None

    def __init__(self, token: str, user: int, host: str, port: str, prefix: str = ""):
        """This bot allows two players that are shown two different
        or equal pictures to discuss about what they see and decide
        whether there are differences.

        :param token: A uuid; a string following the same pattern
            as `0c45b30f-d049-43d1-b80d-e3c3a3ca22a0`
        :param user: ID of a `User` object that was created with
        the token.
        :param host: Full URL including protocol and hostname,
            followed.
        :param port: port for the slurk server
        :param images_per_room: Each room is mapped to a list
            of pairs with two image urls. Each participant
            is presented exactly one image per pair and round.
        :param timers_per_room: Each room is mapped to
            an instance of RoomTimers.
        :param players_per_room: Each room is mapped to a list of
            users. Each user is represented as a dict with the
            keys 'name', 'id', 'msg_n' and 'status'.
        :param last_message_from: Each room is mapped to the user
            that has answered last. A user is represented as a
            dict with the keys 'name' and 'id'.
        :param waiting_timer: Only one user can be in the waiting
            room at a time because the concierge bot would move
            them once there are two. If this single user waits for
            a prolonged time their receive an AMT token for waiting.
        """
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.prefix = prefix
        self.uri += f"{self.prefix}/slurk/api"

        self.exhibits_per_room = ExperimentSessionInfo(qasum_config.DATA_PATH, 
                                                       qasum_config.N, 
                                                       qasum_config.SHUFFLE, 
                                                       qasum_config.SEED)
        self.timers_per_room = dict()
        self.players_per_room = dict()
        self.last_message_from = dict()

        self.waiting_timer = None
        self.received_waiting_token = set()

        LOG.info(f"Running qasum bot on {self.uri} with token {self.token}")
        # register all event handlers
        self.register_callbacks()

    def run(self):
        # establish a connection to the server
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": self.user},
            namespaces="/",
            socketio_path=f"{self.prefix}/socket.io" if self.prefix else 'socket.io',
        )
        # wait until the connection with the server ends
        self.sio.wait()

    def register_callbacks(self):
        @self.sio.event
        def new_task_room(data):
            """Triggered after a new task room is created.

            An example scenario would be that the concierge
            bot emitted a room_created event once enough
            users for a task have entered the waiting room.
            """
            room_id = data["room"]
            task_id = data["task"]

            LOG.debug(f"A new task room was created with id: {data['task']}")
            LOG.debug(f"This bot is looking for task id: {self.task_id}")

            if task_id is not None and task_id == self.task_id:
                for usr in data['users']:
                    self.received_waiting_token.discard(usr['id'])

                # create image items for this room
                LOG.debug("Create data for the new task room...")

                self.exhibits_per_room.get_item_pairs(room_id, tuple(usr['name'] for usr in data['users']))
                self.players_per_room[room_id] = []
                for usr in data["users"]:
                    self.players_per_room[room_id].append(
                        {**usr, "msg_n": 0, "status": "joined"}
                    )
                self.last_message_from[room_id] = None


                # register ready timer for this room
                self.timers_per_room[room_id] = RoomTimers()
                self.timers_per_room[room_id].ready_timer = Timer(
                    qasum_config.TIME_READY * 60,
                    self._send_message,
                    args=[qasum_config.messages.MSG_ARE_YOU_READY, room_id, None, True]
                )
                self.timers_per_room[room_id].ready_timer.start()

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if not response.ok:
                    LOG.error(f"Could not let QASumBot join room: {response.status_code}")
                    response.raise_for_status()
                LOG.debug("Sending QASumBot to new room was successful.")

                self._set_instructions_for_participant_pair(data["users"], room_id)

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            if room_id in self.exhibits_per_room:
                # read out task greeting
                for line in qasum_config.messages.TASK_GREETING:
                    self._send_message(line, room_id, html_content=True)
                    sleep(.5)
                # ask players to send \ready
                # response = requests.patch(
                #     f"{self.uri}/rooms/{room_id}/text/instr_title",
                #     json={"text": line},
                #     headers={"Authorization": f"Bearer {self.token}"}
                # )
                # if not response.ok:
                #     LOG.error(f"Could not set task instruction title: {response.status_code}")
                #     response.raise_for_status()

        @self.sio.event
        def status(data):
            """Triggered if a user enters or leaves a room."""
            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{data['user']['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if not task.ok:
                LOG.error(f"Could not set task instruction title: {task.status_code}")
                task.raise_for_status()
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

            room_id = data["room"]
            # someone joined waiting room
            if room_id == self.waiting_room:
                if self.waiting_timer is not None:
                    LOG.debug("Waiting Timer stopped.")
                    self.waiting_timer.cancel()
                if data["type"] == "join":
                    LOG.debug("Waiting Timer restarted.")
                    self.waiting_timer = Timer(
                        qasum_config.TIME_WAITING*60,
                        self._no_partner,
                        args=[
                            room_id,
                            data["user"]["id"]
                        ]
                    )
                    self.waiting_timer.start()
            # some joined a task room
            elif room_id in self.exhibits_per_room:
                curr_usr, other_usr = self.players_per_room[room_id]
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr

                if data["type"] == "join":
                    # inform game partner about the rejoin event
                    self._send_message(qasum_config.messages.msg_rejoined(curr_usr['name']),
                                       room_id, other_usr["id"])
                    # make sure both users' instructions are set and the right exhibit is showing
                    self.show_item(room_id)
                elif data["type"] == "leave":
                    # send a message to the user that was left alone
                    self._send_message(qasum_config.messages.msg_left_please_wait(curr_usr['name']),
                                       room_id, other_usr["id"])

        @self.sio.event
        def text_message(data):
            """Triggered once a text message is sent (no leading /).

            Count user text messages.
            If encountering something that looks like a command
            then pass it on to be parsed as such.
            """
            LOG.debug(f"Received a message from {data['user']['name']}.")

            room_id = data["room"]
            user_id = data["user"]["id"]

            # filter irrelevant messages
            if room_id not in self.exhibits_per_room or user_id == self.user:
                return

            # if the message is part of the main discussion count it
            for usr in self.players_per_room[room_id]:
                if usr["id"] == user_id and usr["status"] == "ready":
                    usr["msg_n"] += 1

            # reset the answer timer if the message was an answer
            if user_id != self.last_message_from[room_id]:
                LOG.debug(f"{data['user']['name']} awaits an answer.")
                if self.last_message_from[room_id] is not None:
                    self.timers_per_room[room_id].last_answer_timer.cancel()
                self.timers_per_room[room_id].last_answer_timer = Timer(
                    qasum_config.TIME_ANSWER * 60,
                    self._noreply,
                    args=[room_id, user_id]
                )
                self.timers_per_room[room_id].last_answer_timer.start()
                # save the person that last left a message
                self.last_message_from[room_id] = user_id

        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(f"Received a command from {data['user']['name']}: {data['command']}")

            room_id = data["room"]
            user_id = data["user"]["id"]

            if room_id in self.exhibits_per_room:
                # when we get a \done command we should ask for a summary from each user once both say it is done
                # after the summary, they should type \next and then we can move to the next exhibit
                # note: we need to accept gaelic forms of these commands as well!
                LOG.info(f"Match ratio for COMMAND_READY: {fuzz.partial_ratio(data['command'], qasum_config.messages.COMMAND_READY)}")
                LOG.info(f"Match ratio for COMMAND_DONE: {fuzz.partial_ratio(data['command'], qasum_config.messages.COMMAND_DONE)}")
                LOG.info(f"Match ratio for COMMAND_NEXT: {fuzz.partial_ratio(data['command'], qasum_config.messages.COMMAND_NEXT)}")
                if fuzz.partial_ratio(data["command"], qasum_config.messages.COMMAND_DONE) > 80:
                    self._command_done(room_id, user_id)
                elif fuzz.partial_ratio(data["command"], qasum_config.messages.COMMAND_NEXT) > 80:
                    self._command_next(room_id, user_id)
                elif fuzz.partial_ratio(data["command"], qasum_config.messages.COMMAND_READY) > 80:
                    self._command_ready(room_id, user_id)
                elif data["command"] in {"noreply", "no reply"}:
                    self._send_message(qasum_config.messages.MSG_PLEASE_WAIT,
                                       room_id, user_id)
                else:
                    self._send_message(qasum_config.messages.MSG_DONT_UNDERSTAND,
                                       room_id, user_id)

    def _send_message(self, message: str, room_id: str,
                      receiver_id: Optional[str] = None,
                      html_content: bool = False) -> None:
        """
        Send `message` to all users in `room` unless `recipient` is specified; then send only to that user in that room.

        :param message: the text to send from QASumBot
        :param room_id: the id for the room where we want to send the message
        :param receiver_id: (optional) the particular user in that room who we want to see the message
        :param html_content: True iff we want to enable HTML in the message
        """
        message_dict = {"message": message, "room": room_id}

        if receiver_id is not None:
            message_dict["receiver_id"] = receiver_id
        if html_content:
            message_dict["html"] = True
        self.sio.emit("text", message_dict)

    def _set_instructions_for_participant_pair(self, users, room_id) -> None:
        for user, role in zip(sorted(users, key=lambda x: x["name"]), ('questioner', 'answerer')):
            # fetch different info depending on user role
            if role == 'questioner':
                task_title = qasum_config.messages.QUESTIONER_TITLE
                task_description = qasum_config.messages.QUESTIONER_DESCRIPTION
            elif role == 'answerer':
                task_title = qasum_config.messages.ANSWERER_TITLE
                task_description = qasum_config.messages.ANSWERER_DESCRIPTION
            else:
                raise ValueError("Only known user roles for QASum are 'questioner' and 'answerer'")
            self._patch_instructions(user, room_id, task_title, task_description)

    def _patch_instructions(self, user, room_id, title, content) -> None:
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr_title",
            json={"text": title, "receiver_id": user["id"]},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction title: {response.status_code}")
            response.raise_for_status()

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/html/instr",
            json={"text": content, "receiver_id": user["id"]},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction: {response.status_code}")
            response.raise_for_status()

    def _patch_content_area(self, user, room_id, html_data) -> None:
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/html/content-area",
            json={"text": html_data, "receiver_id": user["id"]},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(f"Could not set image: {response.status_code}")
            response.raise_for_status()

    def _command_ready(self, room_id, user_id):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.players_per_room[room_id]
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            sleep(.5)
            self._send_message(qasum_config.messages.msg_already_typed_command(qasum_config.messages.COMMAND_READY),
                               room_id, curr_usr["id"])
            return
        curr_usr["status"] = "ready"

        self.timers_per_room[room_id].ready_timer.cancel()
        # a first ready command was sent
        if other_usr["status"] == "joined":
            sleep(.5)
            # give the user feedback that his command arrived
            self._send_message(qasum_config.messages.msg_waiting_for_partner_command(qasum_config.messages.COMMAND_READY),
                               room_id, curr_usr["id"])
            # give the other user time before reminding him
            self.timers_per_room[room_id].ready_timer = Timer(
                (qasum_config.TIME_READY/2)*60,
                self._send_message,
                args=[qasum_config.messages.MSG_PARTNER_READY_ARE_YOU, room_id, other_usr["id"]]
            )
            self.timers_per_room[room_id].ready_timer.start()
        # the other player was already ready
        else:
            # both users are ready and the game begins
            self._send_message(qasum_config.messages.MSG_HOORAY_START, room_id)
            self.show_item(room_id)
            # kindly ask the users to come to an end after a certain time
            self.timers_per_room[room_id].game_timer = Timer(
                qasum_config.TIME_GAME*60,
                self._send_message,
                args=[qasum_config.messages.MSG_LONG_DISCUSSION, room_id]
            )
            self.timers_per_room[room_id].game_timer.start()

    def _command_done(self, room_id, user_id):
        """Must be sent to end a round of discussion."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.players_per_room[room_id]
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # one can't be done before both were ready
        if "joined" in {curr_usr["status"], other_usr["status"]}:
            self._send_message(qasum_config.messages.MSG_NOT_STARTED, room_id, curr_usr["id"])
        # we expect at least 3 messages of each player
        elif curr_usr["msg_n"] < 3 or other_usr["msg_n"] < 3:
            self._send_message(qasum_config.messages.MSG_TOO_SHORT, room_id, curr_usr["id"])
        # this user has already recently typed /done
        elif curr_usr["status"] == "done":
            sleep(.5)
            self._send_message(qasum_config.messages.msg_already_typed_command(qasum_config.messages.COMMAND_DONE),
                               room_id, curr_usr["id"], html_content=True)
        else:
            curr_usr["status"] = "done"

            # only one user thinks they are done
            if other_usr["status"] != "done":
                # wait for the other user to agree
                self.timers_per_room[room_id].done_timer = Timer(
                    qasum_config.TIME_DIFF_STATES * 60,
                    self._not_done,
                    args=[room_id, user_id]
                )
                self.timers_per_room[room_id].done_timer.start()
                self._send_message(qasum_config.messages.msg_waiting_for_partner_command(qasum_config.messages.COMMAND_DONE),
                                   room_id, curr_usr["id"], html_content=True)
                self._send_message(qasum_config.messages.MSG_PARTNER_DONE_ARE_YOU,
                                   room_id, other_usr["id"], html_content=True)
            # both users think they are done with the game
            else:
                self.timers_per_room[room_id].done_timer.cancel()
                self._send_message(qasum_config.messages.MSG_WRITE_SUMMARY, room_id)
                self._send_message(qasum_config.messages.MSG_NEXT_EXHIBIT_INSTRUCTIONS, room_id)

    def _command_next(self, room_id, user_id):
        """Must be sent to start the next round of discussion."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.players_per_room[room_id]
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # one can't be done before both were ready
        if "joined" in {curr_usr["status"], other_usr["status"]}:
            self._send_message(qasum_config.messages.MSG_NOT_STARTED, room_id, curr_usr["id"])
        # this user has already recently typed /next
        elif curr_usr["status"] == "next":
            sleep(.5)
            self._send_message(qasum_config.messages.msg_already_typed_command(qasum_config.messages.COMMAND_NEXT),
                               room_id, curr_usr["id"], html_content=True)
        else:
            curr_usr["status"] = "next"

            # only one user thinks they are done
            if other_usr["status"] != "next":
                # wait for the other user to agree
                self.timers_per_room[room_id].done_timer = Timer(
                    qasum_config.TIME_DIFF_STATES * 60,
                    self._not_next,
                    args=[room_id, user_id]
                )
                self.timers_per_room[room_id].done_timer.start()
                self._send_message(qasum_config.messages.msg_waiting_for_partner_command(qasum_config.messages.COMMAND_NEXT),
                                   room_id, curr_usr["id"], html_content=True)
                self._send_message(qasum_config.messages.MSG_PARTNER_NEXT_ARE_YOU,
                                   room_id, other_usr["id"], html_content=True)
            # both users think they are ready for the next round
            else:
                self.timers_per_room[room_id].done_timer.cancel()
                self.exhibits_per_room[room_id].pop(0)
                # was this the last game round?
                if not self.exhibits_per_room[room_id]:
                    self._send_message(qasum_config.messages.MSG_EXPERIMENT_OVER, room_id)
                    sleep(1)
                    self.confirmation_code(room_id, "success")
                    sleep(1)
                    self.close_game(room_id)
                else:
                    self._send_message(qasum_config.messages.MSG_PREPARING_NEXT, room_id)

                    # reset attributes for the new round
                    for usr in self.players_per_room[room_id]:
                        usr["status"] = "ready"
                        usr["msg_n"] = 0
                    self.timers_per_room[room_id].game_timer.cancel()
                    self.timers_per_room[room_id].game_timer = Timer(
                        qasum_config.TIME_GAME * 60,
                        self._send_message,
                        args=[qasum_config.messages.MSG_LONG_DISCUSSION, room_id]
                    )
                    self.timers_per_room[room_id].game_timer.start()
                    self.show_item(room_id)

    def _not_done(self, room_id, user_id):
        """One of the two players was not done."""
        for usr in self.players_per_room[room_id]:
            if usr["id"] == user_id:
                usr["status"] = "ready"
        self._send_message(qasum_config.messages.MSG_NOT_DONE, room_id, user_id)

    def _not_next(self, room_id, user_id):
        """One of the two players was not ready to move on."""
        for usr in self.players_per_room[room_id]:
            if usr["id"] == user_id:
                # TODO check if this is the right status setting/comparison/whatever
                usr["status"] = "done"
        self._send_message(qasum_config.messages.MSG_NOT_NEXT, room_id, user_id)

    def show_item(self, room_id):
        """Update the image and task description of the players."""
        LOG.debug("Update the image and task description of the players.")
        # guarantee fixed user order - necessary for update due to rejoin
        users = sorted(self.players_per_room[room_id], key=lambda x: x["name"])

        if self.exhibits_per_room[room_id]:
            exhibits = self.exhibits_per_room[room_id][0]
            # show a different image to each user
            for usr, exhibit in zip(users, exhibits):
                self._patch_content_area(usr, room_id, exhibit)
            self._set_instructions_for_participant_pair(users, room_id)
        else:
            # TODO what do we want to happen when users finish all the items?
            pass

    def _no_partner(self, room_id, user_id):
        """Handle the situation that a participant waits in vain."""
        if user_id not in self.received_waiting_token:
            self._send_message(qasum_config.messages.MSG_NO_PARTNER_FOUND, room_id, user_id)
            # create token and send it to user
            self.confirmation_code(room_id, "no_partner", receiver_id=user_id)
            sleep(5)
            self._send_message(qasum_config.messages.MSG_MAY_WAIT_MORE, room_id, user_id)
            # no need to cancel
            # the running out of this timer triggered this event
            self.waiting_timer = Timer(
                qasum_config.TIME_WAITING * 60,
                self._no_partner,
                args=[room_id, user_id]
            )
            self.waiting_timer.start()
            self.received_waiting_token.add(user_id)
        else:
            self._send_message(qasum_config.messages.MSG_NO_FURTHER_PAYMENT, room_id, user_id)
            sleep(2)
            self._send_message(qasum_config.messages.MSG_CHECK_BACK_LATER, room_id, user_id)

    def _noreply(self, room_id, user_id):
        """One participant did not receive an answer for a while."""
        curr_usr, other_usr = self.players_per_room[room_id]
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        self._send_message(qasum_config.messages.MSG_CONVO_ENDED_YOU_WERE_AWAY, room_id, other_usr["id"])
        self._send_message(qasum_config.messages.MSG_PARTNER_AWAY_A_LONG_TIME, room_id, curr_usr["id"])
        # create token and send it to user
        self.confirmation_code(room_id, "no_reply", receiver_id=curr_usr["id"])
        self.close_game(room_id)

    def confirmation_code(self, room_id, status, receiver_id=None):
        """Generate AMT token that will be sent to each player."""
        kwargs = dict()
        # either only for one user or for both
        if receiver_id is not None:
            kwargs["receiver_id"] = receiver_id

        amt_token = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=6
        ))
        # post AMT token to logs
        response = requests.post(
            f"{self.uri}/logs",
            json={"event": "confirmation_log",
                  "room_id": room_id,
                  "data": {"status_txt": status, "amt_token": amt_token},
                  **kwargs},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(
                f"Could not post AMT token to logs: {response.status_code}"
            )
            response.raise_for_status()

        self._send_message(qasum_config.messages.MSG_PLEASE_SEND_TOKEN, room_id, **kwargs)
        self._send_message(qasum_config.messages.msg_amt_token(amt_token), room_id, **kwargs)

        return amt_token

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        self._send_message(qasum_config.messages.msg_moved_out(str(qasum_config.TIME_CLOSE * 2 * 60 - qasum_config.TIME_CLOSE * 3 * 60)),
                           room_id)
        sleep(2)
        self._send_message(qasum_config.messages.MSG_SAVE_TOKEN, room_id)
        self.room_to_read_only(room_id)

        # disable all timers
        for timer_id in {"ready_timer",
                         "game_timer",
                         "done_timer",
                         "last_answer_timer"}:
            timer = getattr(self.timers_per_room[room_id], timer_id)
            if timer is not None:
                timer.cancel()

        # send users back to the waiting room
        sleep(qasum_config.TIME_CLOSE*60)
        for usr in self.players_per_room[room_id]:
            sleep(qasum_config.TIME_CLOSE*60)

            # DMH: I don't think we actually need to rename the users since we're giving them role-based names!
            # self.rename_users(usr["id"])

            response = requests.post(
                f"{self.uri}/users/{usr['id']}/rooms/{self.waiting_room}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if not response.ok:
                LOG.error(
                    f"Could not let user join waiting room: {response.status_code}"
                )
                response.raise_for_status()
            LOG.debug("Sending user to waiting room was successful.")

            response = requests.delete(
                f"{self.uri}/users/{usr['id']}/rooms/{room_id}",
                headers={"If-Match": response.headers["ETag"],
                         "Authorization": f"Bearer {self.token}"}
            )
            if not response.ok:
                LOG.error(
                    f"Could not remove user from task room: {response.status_code}"
                )
                response.raise_for_status()
            LOG.debug("Removing user from task room was successful.")

        # remove any task room specific objects
        self.exhibits_per_room.pop(room_id)
        self.timers_per_room.pop(room_id)
        self.players_per_room.pop(room_id)
        self.last_message_from.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()
