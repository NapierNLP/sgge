COMMAND_READY = '/ready'
COMMAND_NEXT = '/next'
COMMAND_DONE = '/done'

MSG_ARE_YOU_READY = f"Are you ready? Please type `{COMMAND_READY}` to begin the game."
MSG_PLEASE_WAIT = "Please wait some more for an answer."
MSG_DONT_UNDERSTAND = "Sorry, but I do not understand this command."
MSG_PARTNER_READY_ARE_YOU = f"Your partner is ready. Please, type `{COMMAND_READY}`!"
MSG_HOORAY_START = "Woo-Hoo! The game will begin now."
MSG_LONG_DISCUSSION = f"Your conversation has lasted a while already. When you're done talking about the exhibit, please type `{COMMAND_DONE}` to start the summary phase."
MSG_NOT_STARTED = "The conversation has not started yet."
MSG_TOO_SHORT = "This conversation doesn't seem long enough yet. Please discuss some more!"
MSG_WRITE_SUMMARY = "Ok, please summarise **only** the information about the exhibit **which you discussed in your conversation**."
MSG_PARTNER_DONE_ARE_YOU = f"Your partner thinks that the conversation is complete now. Type `{COMMAND_DONE}` if you agree."
MSG_NEXT_EXHIBIT_INSTRUCTIONS = f"When you have submitted your summary, please use the `{COMMAND_NEXT}` command to move to the next exhibit. "
MSG_PARTNER_NEXT_ARE_YOU = f"Your partner is done with their summary. Type `{COMMAND_NEXT}` when you are finished with yours."
MSG_EXPERIMENT_OVER = "The experiment is over! Thank you for participating!"
MSG_PREPARING_NEXT = "Ok, now preparing the next exhibit. "
MSG_NOT_DONE = f"Your partner seems to still want to discuss some more. Send `{COMMAND_DONE}` again once you two are really finished."
MSG_NOT_NEXT = f"Your partner is still working on their summary. Send `{COMMAND_NEXT}` again once you two are really finished."
MSG_NO_PARTNER_FOUND = "Unfortunately we could not find a partner for you!"
MSG_MAY_WAIT_MORE = "You may also wait some more :)"
MSG_NO_FURTHER_PAYMENT = "You won't be remunerated for further waiting time."
MSG_CHECK_BACK_LATER = "Please check back at another time of the day."
MSG_CONVO_ENDED_YOU_WERE_AWAY = "The game ended because you were gone for too long!"
MSG_PARTNER_AWAY_A_LONG_TIME = "Your partner seems to be away for a long time!"
MSG_PLEASE_SEND_TOKEN = "Please write down the following token and save it for later. You will need to provide this token when submitting your bank details for reimbursement after the experiment."
MSG_CONTACT_FOR_HELP =  "If you have any problems, please email nlg@napier.ac.uk."
MSG_SAVE_TOKEN = "Make sure to save your token before that."


def msg_rejoined(username: str) -> str:
    return f"{username} has joined the game. "


def msg_left_please_wait(username: str) -> str:
    return f"{username} has left the game. Please wait a bit, your partner may rejoin."


def msg_amt_token(amt_token: str) -> str:
    return f"Here is your token: {amt_token}"


def msg_moved_out(time_left: str) -> str:
    return f"You will be moved out of this room in {time_left}s."


def msg_already_typed_command(command: str) -> str:
    return f"You have already typed `{command}`."


def msg_waiting_for_partner_command(command: str) -> str:
    return f"Now waiting for your partner to type `{command}`."

QUESTIONER_TITLE = "Ask questions about the exhibit."
QUESTIONER_DESCRIPTION = f"""<b>You're at the museum and you see this interesting exhibit.</b> You don't have much background information, 
but you have some idea that the exhibit relates to some of the terms you see below the picture.

(1) <b>Ask your partner questions about the exhibit to learn more about it.</b> Try to learn as much as you can! 
(2) When you feel like the conversation has covered enough information and reached a comfortable stopping point, send the message: <verbatim>{COMMAND_DONE}</verbatim>

Once you and your partner agree your conversation is done, you'll each write a summary of the information you discussed.

<hr>"""
ANSWERER_TITLE = "Answer questions about the exhibit."
ANSWERER_DESCRIPTION = f"""<b>You work at the museum and are presenting this interesting exhibit.</b> You have a mix of 'metadata' (tables of information about the exhibit) and 'text' (paragraphs of text about the exhibit).

(1) <b>Answer your partners' questions about the exhibit.</b> Try to give appropriate answers which share relevant context from the information provided to you.<i>Do not use your own private or personal knowledge for this task.</i>
(2) When you feel like the conversation has covered enough information and reached a comfortable stopping point, send the message: <verbatim>{COMMAND_DONE}</verbatim>

Once you and your partner agree your conversation is done, you'll each write a summary of the information you discussed.

<hr>"""

TASK_GREETING = ["**Welcome to the QASum experiment!**",
                 "In this experiment, you will have a conversation with another person about a museum exhibit and then summarise what you discussed.",
                 f"Please type `{COMMAND_READY}` to begin the experiment."]
