# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import os

# import lib.messages.eng as messages
import lib.messages.gla as messages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to a comma separated (csv) file with two columns.
# Each column containing the url to one image file.
DATA_PATH = os.path.join(ROOT, "data", "exhibit_data.csv")
# This many game rounds will be played per room and player pair.
N = 6
# Set this seed to make the random process reproducible.
SEED = 20210601
# Whether to randomly sample images or present them in linear order.
SHUFFLE = True

# All below *TIME_* variables are in minutes.
# They indicate how long a situation has to persist for something to happen.

# Remind the player to send the /ready command if they have not done so before then.
TIME_READY = 5.0
# Reset the status 'done' to 'ready' of one player if the other does not agree
# that they have found the difference.
TIME_DIFF_STATES = 5.0
# A participant remaining in the waiting room will be remunerated with an AMT Token.
TIME_WAITING = 5.0
# One player did not answer their partner.
# The game will be ended and only the partner receives an AMT Token.
TIME_ANSWER = 5.0
# The participants will be asked to come to an end.
# Counted per game round and not per game.
TIME_GAME = 10.0
# The participants will be moved back to the waiting room after the game finished.
TIME_CLOSE = 5.0


