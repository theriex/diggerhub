""" Summarize activity to encourage community """
#pylint: disable=wrong-import-order
#pylint: disable=wrong-import-position
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy
import py.mconf as mconf
import logging
import logging.handlers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(module)s %(asctime)s %(message)s',
    handlers=[logging.handlers.TimedRotatingFileHandler(
        mconf.logsdir + "plg_sumact.log", when='D', backupCount=10)])
import py.util as util
import py.dbacc as dbacc
import datetime
import json
import sys


sdnvs = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
         "Saturday", "Sunday", "Never"]
runinfo = {"mode": "logonly",  # send mail only if "summary" or "all"
           "usums": [],        # user summaries
           "tdow": sdnvs[datetime.datetime.today().weekday()]}
dfltact = {"lastsend": "1970-01-01T00:00:00Z", "sendon": "Wednesday"}


def send_user_summary():
    subj = "DiggerHub user activity summary for " + runinfo["tdow"]
    body = "No user summaries sent"
    if len(runinfo["usums"]) > 0:
        body = "User summaries sent to:\n"
    for usersum in runinfo["usums"]:
        body += (usersum["acct"]["dsId"] + " " +
                 usersum["acct"]["digname"] + " " +
                 "(" + usersum["acct"]["firstname"] + ") " +
                 usersum["acct"]["email"] + ": " +
                 str(usersum["count"]) + "\n")
    if runinfo["mode"] in ["all", "summary"]:
        util.send_mail("support@diggerhub.com", subj, body,
                       domain="diggerhub.com")
    else:
        logging.info("User summary:\n" + body)


def song_ident_text(song):
    text = song["ti"] + " - " + song["ar"] + " (" + song["ab"] + ")"
    if song["nt"]:
        text += "\n    " + song["nt"]
    return text


def send_activity_summary(user, settings, songsum):
    subj = "DiggerHub weekly activity summary"
    body = "Top Songs:\n\n"
    for idx, song in enumerate(songsum["top20"]):
        body += str(idx + 1) + ": " + song_ident_text(song) + "\n"
    body += "\n"
    body += "Easiest Song: " + song_ident_text(songsum["easiest"]) + "\n"
    body += "Hardest Song: " + song_ident_text(songsum["hardest"]) + "\n"
    body += "Most Chill: " + song_ident_text(songsum["chillest"]) + "\n"
    body += "Most Amped: " + song_ident_text(songsum["ampest"]) + "\n"
    body += "\n"
    body += "Let your friends know what they're missing.\n\n"
    if runinfo["mode"] == "all":
        util.send_mail(user["email"], subj, body, domain="diggerhub.com")
        settings["sumact"]["lastsend"] = dbacc.nowISO()
        user["settings"] = json.dumps(settings)
        dbacc.write_entity(user, vck=user["modified"])
    else:
        logging.info("Summary for " + str(user["dsId"]) + "\n" + body)


def dayonly(dtinst):
    return dtinst.replace(hour=0, minute=0, second=0, microsecond=0)


def send_day_of_week(settings):
    senddow = "Never"
    try:
        senddow = settings["sumact"]["sendon"]
    except ValueError:
        pass
    return senddow


def get_modified_since_timestamp(settings):
    lastsendts = settings["sumact"].get("lastsend", dfltact["lastsend"])
    today = dayonly(datetime.datetime.utcnow())
    if lastsendts > dbacc.dt2ISO(today - datetime.timedelta(days=2)):
        return lastsendts, ""  # already sent recent summary
    return lastsendts, dbacc.dt2ISO(today - datetime.timedelta(days=7))


def check_user_activity(user, settings):
    errpre = "check_user_activity skipping DigAcc" + str(user["dsId"])
    senddow = send_day_of_week(settings)
    if runinfo["tdow"] != senddow:
        logging.info(errpre +" sendon " + senddow)
        return
    lastsendts, sincets = get_modified_since_timestamp(settings)
    if not sincets:
        logging.info(errpre + " not enough elapsed time since " + lastsendts)
        return
    usum = {"acct": user, "count": 0}
    songsum = {"top20":[]}
    songs = dbacc.query_entity("Song", "WHERE aid = " + user["dsId"] +
                               " AND modified > \"" + sincets + "\"" +
                               " ORDER BY rv DESC, modified DESC")
    for song in songs:
        usum["count"] += 1
        if len(songsum["top20"]) < 20:
            songsum["top20"].append(song)
        if not songsum.get("easiest") or song["al"] < songsum["easiest"]["al"]:
            songsum["easiest"] = song
        if not songsum.get("hardest") or song["al"] > songsum["hardest"]["al"]:
            songsum["hardest"] = song
        if (not songsum.get("chillest") or
                song["el"] < songsum["chillest"]["el"]):
            songsum["chillest"] = song
        if not songsum.get("ampest") or song["el"] > songsum["ampest"]["el"]:
            songsum["ampest"] = song
    runinfo["usums"].append(usum)
    if usum["count"] < 3:
        logging.info(errpre + " not enough songs (" + str(usum["count"]) + ")")
        return
    send_activity_summary(user, settings, songsum)


def check_users():
    now = datetime.datetime.utcnow()
    lastweek = dbacc.dt2ISO(now - datetime.timedelta(weeks=1))
    users = dbacc.query_entity("DigAcc",
                               "WHERE modified > \"" + lastweek + "\"")
    for user in users:
        logging.info("Checking " + str(user["dsId"]) + " " + user["firstname"])
        dfltset = {"sumact": dfltact}
        settings = util.load_json_or_default(user["settings"], dfltset)
        if not settings.get("sumact"):
            settings["sumact"] = dfltact
        check_user_activity(user, settings)
    send_user_summary()


def run_with_params():
    logging.info("Checking weekly activity summary for " + runinfo["tdow"])
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        runinfo["mode"] = "all"
    check_users()

# run it
run_with_params()
