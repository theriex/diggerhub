""" Summarize activity to encourage community """
#pylint: disable=wrong-import-order
#pylint: disable=wrong-import-position
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy
#pylint: disable=consider-using-from-import
#pylint: disable=invalid-name
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
    # comment text makes it harder to scan the summary song list, and notes
    # are not included in the wt20 site page.  Comments were originally
    # included on the idea people might forward the received email, but
    # sparse comments don't make things much more compelling, and
    # copyright/songID noise in the comments field are annoying.  Comments
    # should be included when sharing a song, or possibly when sharing an
    # album, but not in an email notice.
    # if song["nt"]:
    #     text += "\n    " + song["nt"]
    return text


def trim_song_fields_for_reporting(song):
    song["path"] = ""
    song["smti"] = ""
    song["smar"] = ""
    song["smab"] = ""
    return song


def write_song_activity_summary(user, songsum):
    digname = user.get("digname")
    if not digname:
        return ""
    sasum = {"dsType":"SASum", "aid":user["dsId"], "digname":digname,
             "sumtype":"wt20","start":songsum["sincets"], "end":dbacc.nowISO(),
             "ttlsongs":songsum["ttlsongs"]}
    for song in songsum["top20"]:
        trim_song_fields_for_reporting(song)
    sasum["songs"] = json.dumps(songsum["top20"])
    flds = ["easiest", "hardest", "chillest", "ampest"]
    for fld in flds:
        sasum[fld] = json.dumps(trim_song_fields_for_reporting(songsum[fld]))
    dbacc.write_entity(sasum)
    ts = sasum["end"][0:10]
    pl = "https://diggerhub.com/plink/wt20/" + digname + "/" + ts
    return pl


def send_activity_summary(user, settings, songsum):
    plink = write_song_activity_summary(user, songsum)
    if not plink:
        plink = "Set a digname for your account to publish weekly summaries"
    subj = "DiggerHub weekly activity summary"
    body = "Your weekly activity summary\n"
    body += plink + "\n"
    body += str(songsum["ttlsongs"]) + " songs synchronized to DiggerHub\n"
    body += "Top Songs:\n\n"
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


# This cron job gets run once a day, typically just after 00:00:00 PDT.  It
# doesn't matter when this summary task runs, but PDT can be unintuitive if
# you are in Europe listening through the the evening/night, then you see
# some of those songs in this weeks summary and others the following week.
# Any timezone other than the server timezone has the potential to be
# unintuitive in this way.  Just how it works.  Shouldn't really matter.
def get_last_played_timestamps(settings):
    lastsendts = settings["sumact"].get("lastsend", dfltact["lastsend"])
    today = dayonly(datetime.datetime.utcnow())
    if lastsendts > dbacc.dt2ISO(today - datetime.timedelta(days=2)):
        return lastsendts, "", ""  # already sent recent summary
    # six days back and including today == one week
    sincets = dbacc.dt2ISO(today - datetime.timedelta(days=7))
    return lastsendts, sincets, dbacc.dt2ISO(today)


def already_listed(song, songsum):
    for t20song in songsum["top20"]:
        if t20song["path"] == song["path"]:
            # This can happen if the song metadata was changed, leading to
            # the song now mapping to a different dsId
            return True
        if t20song["ti"] == song["ti"] and t20song["ar"] == song["ar"]:
            # Too similar to list as separate entries in the top 20
            return True
    return False


def check_user_activity(user, settings):
    ustr = "DigAcc" + str(user["dsId"])
    errpre = "check_user_activity skipping " + ustr
    senddow = send_day_of_week(settings)
    if runinfo["tdow"] != senddow:
        logging.info(errpre +" sendon " + senddow)
        return
    lastsendts, sincets, untilts = get_last_played_timestamps(settings)
    if not sincets:
        logging.info(errpre + " not enough elapsed time since " + lastsendts)
        return
    logging.info("check_user_activity " + ustr + " " +
                 sincets[:10] + " - " + untilts[:10])
    usum = {"acct": user, "count": 0}
    songsum = {"sincets":sincets, "top20":[]}
    # The public Top 20 should not include anything you are not comfortable
    # playing for others, nor should it include anything you think is not
    # very good.  Otherwise it's no fun to see.
    songs = dbacc.query_entity("Song", "WHERE aid = " + user["dsId"] +
                               " AND lp >= \"" + sincets + "\"" +
                               " AND lp < \"" + untilts + "\"" +
                               " AND (pd IS NULL OR pd NOT IN" +
                               " (\"skipped\", \"snoozed\", \"dupe\"))" +
                               " AND kws LIKE \"%Social%\"" +
                               " AND rv >= 5" +
                               " ORDER BY rv DESC, lp DESC")
    for song in songs:
        usum["count"] += 1
        if len(songsum["top20"]) < 20 and not already_listed(song, songsum):
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
    if usum["count"] < 20:  # weekly top 20 looks anemic if less than 20 songs
        logging.info(errpre + " not enough songs (" + str(usum["count"]) + ")")
        return
    songsum["ttlsongs"] = usum["count"]
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
