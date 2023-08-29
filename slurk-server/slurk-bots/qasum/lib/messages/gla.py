COMMAND_READY = '/tòiseachadh'
COMMAND_NEXT = '/ath'
COMMAND_DONE = '/deiseil'

MSG_ARE_YOU_READY = f"A bheil thu deiseil? Cuir a-steach `{COMMAND_READY}` gus an còmhradh a thòiseachadh."
MSG_PLEASE_WAIT = "Feuch an fuirich thu diog no dhà nas fhaide airson freagairt."
MSG_DONT_UNDERSTAND = "Duilich, ach chan eil mi a' tuigsinn na dh'iarr thu orm."
MSG_PARTNER_READY_ARE_YOU = f"Tha do chompanach deiseil. Feuch gun sgrìobh thu `{COMMAND_READY}`!"
MSG_HOORAY_START = "Math fhèin! Tòisichidh an còmhradh a-nis."
MSG_LONG_DISCUSSION = f"Tha an còmhradh agad air mairsinn airson greis mu thràth. Nuair a bhios tu deiseil bruidhinn mun taisbeanadh, sgrìobh `{COMMAND_DONE}` gus an geàrr-chunntas a thòiseachadh."
MSG_NOT_STARTED = "Cha do thòisich an còmhradh fhathast."
MSG_TOO_SHORT = "Chan eil coltas gu bheil an còmhradh seo fada gu leòr fhathast. Feuch an bruidhinn thu barrachd!"
MSG_WRITE_SUMMARY = "Ceart gu leòr, feuch an toir thu geàrr-chunntas **a-mhàin** air an fhiosrachadh mun taisbeanadh **air an do bhruidhinn thu nur còmhradh**."
MSG_PARTNER_DONE_ARE_YOU = f"Tha do chompanach dhen bheachd gu bheil an còmhradh deiseil a-nis. Sgrìobh `{COMMAND_DONE}` ma bhios tu ag aontachadh."
MSG_NEXT_EXHIBIT_INSTRUCTIONS = f"Nuair a tha thu air do gheàrr-chunntas a chuir a-steach, sgrìobh `{COMMAND_NEXT}` gus gluasad chun ath thaisbeanadh."
MSG_PARTNER_NEXT_ARE_YOU = f"Tha do chom-pàirtiche deiseil leis a' gheàrr-chunntas aca. Taidhp `{COMMAND_NEXT}` nuair a bhios tu deiseil leis an fhear agad fhèin."
MSG_EXPERIMENT_OVER = "Tha an sgrùdadh seachad! Tapadh leat airson a dhol an sàs ann!"
MSG_PREPARING_NEXT = "Ceart gu leòr, tha sinn ag ullachadh an ath thaisbeanadh..."
MSG_NOT_DONE = f"Tha e coltach gu bheil do chom-pàirtiche fhathast ag iarraidh barrachd còmhraidh. Cuir `{COMMAND_DONE}` a-rithist nuair a bhios an dithis agaibh deiseil."
MSG_NOT_NEXT = f"Tha do chom-pàirtiche fhathast ag obair air a' gheàrr-chunntas aca. Cuir `{COMMAND_NEXT}` a-rithist nuair a bhios an dithis agaibh deiseil."
MSG_NO_PARTNER_FOUND = "Gu mì-fhortanach cha b' urrainn dhuinn com-pàirtiche a lorg dhut!"
MSG_MAY_WAIT_MORE = "Dh'fhaodadh tu feitheamh beagan a bharrachd is dòcha :)"
MSG_NO_FURTHER_PAYMENT = "Cha bhi thu a' faighinn tuarastal airson airson a bhith feitheimh nas fhaide."
MSG_CHECK_BACK_LATER = "Feuch an toir thu sùil air ais aig àm eile dhen latha."
MSG_CONVO_ENDED_YOU_WERE_AWAY = "Thàinig an geama gu crìch oir bha thu air falbh ro fhada!"
MSG_PARTNER_AWAY_A_LONG_TIME = "Tha e coltach gu bheil do chompanach air falbh airson ùine mhòr!"
MSG_PLEASE_SEND_TOKEN = "Sgrìobh sìos an tòcan ('token') a leanas is sàbhail e airson uair eile. Feumaidh tu an tòcan seo a thoirt seachad nuair a chuireas tu a-steach am fiosrachadh-banca agad airson ais-phàigheadh ('reimbursement') an deidh an sgrùdaidh."
MSG_CONTACT_FOR_HELP = "Ma tha duilgheadas sam bith agad, cuir post-d gu nlg@napier.ac.uk."
MSG_SAVE_TOKEN = "Dèan cinnteach gun sàbhail thu an tòcan agad ro làimh."


def msg_rejoined(username: str) -> str:
    return f"Tha {username} air a dhol a-steach dhan t-seòmar."


def msg_left_please_wait(username: str) -> str:
    return f"Tha {username} air an còmhradh fhàgail. Feuch an fuirich thu beagan, air eagal ‘s gun till do chompanach."


def msg_amt_token(amt_token: str) -> str:
    return f"Seo an tòcan agad: {amt_token}"


def msg_moved_out(time_left: str) -> str:
    return f"Thèid do ghluasad a-mach às an t-seòmar seo ann an {time_left} diogan. Dèan cinnteach gun sàbhail thu do thòcan ro làimh."


def msg_already_typed_command(command: str) -> str:
    return f"Thaidhp thu`{command}` mar thà."


def msg_waiting_for_partner_command(command: str) -> str:
    return f"A-nis a' feitheamh ris a' chompanach agad `{command}` a thaipeadh."


QUESTIONER_TITLE = "Faighnich ceistean mun taisbeanadh."
QUESTIONER_DESCRIPTION = f"""<b>Tha thu aig an taigh-tasgaidh agus chì thu an taisbeanadh inntinneach seo.</b> Chan eil mòran cùl-fhiosrachaidh agad, ach tha beachd agad gu bheil an taisbeanadh a' buntainn ri cuid de na teirmean a chì thu fon dealbh.

(1) <b>Faighnich ceistean do chom-pàirtiche mun taisbeanadh gus barrachd ionnsachadh mu dheidhinn.</b> Feuch ri ionnsachadh cho mòr 's as urrainn dhut!
(2) Nuair a tha thu a' faireachdainn gu bheil an còmhradh air fiosrachadh gu leòr a chòmhdach agus air àite-stad comhfhurtail a ruighinn, cuir am brath: <verbatim>{COMMAND_NEXT}</verbatim>

Aon uair 's gu bheil thu fhèin agus an com-pàirtiche ag aontachadh gu bheil an còmhradh agad deiseil, sgrìobhaidh gach fear agaibh geàrr-chunntas den fhiosrachadh air an do bhruidhinn thu.
<hr />"""

ANSWERER_TITLE = "Freagairtean do na ceistean air an taisbeanadh."
ANSWERER_DESCRIPTION = f"""<b>Tha thu ag obair aig an taigh-tasgaidh agus a' taisbeanadh na h-ulaidh (exhibit item) inntinnich seo.</b> Tha an teacsa gu h-ìosal a' riochdachadh an fhiosrachaidh air fad a th' agad mun ulaidh.

(1) <b>Freagair ceistean do chom-pàirtichean mun taisbeanadh.</b> Feuch ri freagairtean iomchaidh a thoirt seachad a tha a' riochdachadh co-theacs an fhiosrachaidh a chaidh a thoirt dhut.<i>Na cleachd an t-eòlas prìobhaideach no pearsanta agad fhèin na do fhreagairtean. .</i>
(2) Nuair a tha thu a' faireachdainn gu bheil an còmhradh air fiosrachadh gu leòr a thoir seachad agus air àite-stad comhfhurtail a ruighinn, cuir am brath: <verbatim>{COMMAND_NEXT}</verbatim>

Aon uair 's gu bheil thu fhèin agus an com-pàirtiche ag aontachadh gu bheil an còmhradh agaibh deiseil, sgrìobhaidh gach neach agaibh geàrr-chunntas air an fhiosrachadh mun an do bhruidhinn thu.
<hr />"""


TASK_GREETING = ["**Fàilte don sgrùdadh QASum!**",
                "Airson an sgrùdaidh seo, nì thu còmhradh ri neach eile mu thaisbeanadh aig taigh-tasgaidh. An uairsin, bheir thu geàrr-chunntas air na bhruidhinn thu seachad",
                f"Cuir a-steach `{COMMAND_READY}` gus an deuchainn a thòiseachadh."]
