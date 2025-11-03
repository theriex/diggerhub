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


runinfo = {"mode": "logonly",  # send mail only if "summary" or "all"
           "usums": []}        # user summaries
dfltact = {"lastsend": "1970-01-01T00:00:00Z", "sendon": "Wednesday"}


def daily_activity_totals():
    dat = {"yts": dbacc.dt2ISO(runinfo["sod"] - datetime.timedelta(days=1))}
    sql = ("SELECT COUNT(DISTINCT aid) AS ttlusers, COUNT(*) AS ttlsongs" +
           " FROM Song" +
           " WHERE modified >= \"" + dat["yts"] + "\"" +
           " AND modified < \"" + runinfo["wkets"] + "\"")
    qres = dbacc.custom_query(sql, ["ttlusers", "ttlsongs"])
    for rec in qres:
        dat["ttlusers"] = rec["ttlusers"]
        dat["ttlsongs"] = rec["ttlsongs"]
    sql = ("SELECT COUNT(DISTINCT aid) AS ttlnuu, COUNT(*) AS ttlnewsgs " +
           "FROM Song" + 
           " WHERE modified >= \"" + dat["yts"] + "\"" +
           " AND modified < \"" + runinfo["wkets"] + "\"" +
           " AND created = SUBSTRING(modified, 1, 20)")
    qres = dbacc.custom_query(sql, ["ttlnuu", "ttlnewsgs"])
    for rec in qres:
        dat["ttlnuu"] = rec["ttlnuu"]
        dat["ttlnewsgs"] = rec["ttlnewsgs"]
    txt = ("Stats for yesterday (" + dat["yts"] + " to " + runinfo["wkets"] +
           ":\n  " + str(dat["ttlsongs"]) + " songs updated by " +
           str(dat["ttlusers"]) + " listeners ")
    return txt


def user_weekly_top20_send_summary():
    txt = ""
    if len(runinfo["usums"]) > 0:
        txt = ("Summarized " + str(runinfo["usersgttl"]) + " songs for " +
               str(runinfo["userttl"]) + " listeners " + runinfo["wksts"] +
               " to " + runinfo["wkets"] + "\n")
    for usersum in runinfo["usums"]:
        txt += ("  " + usersum["acct"]["dsId"] + " " +
                usersum["acct"]["digname"] + " " +
                "(" + usersum["acct"]["firstname"] + ") " +
                usersum["acct"]["email"] + ": " +
                str(usersum["count"]) + "\n")
    return txt


def beta_activity_monitoring():
    txt = ""
    betas = dbacc.query_entity("StInt", "WHERE sitype = \"beta1\"" +
                               " ORDER BY modified DESC")
    if len(betas) > 0:
        txt = "\"beta1\" test activity:\n"
    for bt in betas:
        # logging.info("stdat: " + bt["stdat"])
        stdat = util.load_json_or_default(bt["stdat"], {})
        cdat = {"dsec":24 * 60 * 60, "daysact":0, "daysidle":0,}
        activated = stdat.get("activated")
        if activated:
            dt = dbacc.ISO2dt(activated)
            difft = datetime.datetime.utcnow() - dt
            cdat["daysact"] = difft.total_seconds() // cdat["dsec"]
        cnts = stdat.get("cnts")
        if cnts:
            newest = cnts.get("newest")
            if newest:
                dt = dbacc.ISO2dt(newest[0:20])
                difft = datetime.datetime.utcnow() - dt
                cdat["daysidle"] = difft.total_seconds() // cdat["dsec"]
        txt += ("  " + str(bt["aid"]) + " " + bt["status"] + " " + bt["email"] +
                " days active: " + str(cdat["daysact"]) +
                ", days idle: " + str(cdat["daysidle"]) + "\n")
    return txt


def send_hub_summary():
    subj = "DiggerHub user activity send for " + runinfo["tdow"]
    sta = [daily_activity_totals(),
           user_weekly_top20_send_summary(),
           beta_activity_monitoring()]
    body = "\n".join(sta) + "\n"
    if runinfo["mode"] in ["all", "summary"]:
        util.send_mail(util.supnm() + "@" + util.domnm(), subj, body,
                       domain=util.domnm())
    else:
        logging.info("send_hub_summary mode " + runinfo["mode"] + "\n" + body)


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
             "sumtype":"wt20","start":songsum["sincets"],
             "end":songsum["untilts"], "ttlsongs":songsum["ttlsongs"]}
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


def settings_for_user(user):
    dfltset = {"sumact": dfltact}
    settings = util.load_json_or_default(user["settings"], dfltset)
    if not settings.get("sumact"):
        settings["sumact"] = dfltact
    return settings


# user may have been interim updated by competing cron job
def update_user_settings_sumact_lastsend(user, timestamp, retry=0):
    if retry > 1:
        logging.warning("Unable to update DigAcc" + str(user["dsId"]) +
                        " settings.sumact.lastsend after " + str(retry) +
                        " attempts. Bailing out.")
        return
    settings = settings_for_user(user)
    settings["sumact"]["lastsend"] = timestamp
    user["settings"] = json.dumps(settings)
    try:
        dbacc.write_entity(user, vck=user["modified"])
        logging.info(str(user["dsId"]) + " settings lastsend updated: " +
                         user["settings"])
    except ValueError as ve:
        retrycount = retry + 1
        logging.info("update_user_settings_sumact_lastsend " + str(ve) +
                     " retrying (retry " + str(retrycount) + ")")
        # get the most recent user, not via cfbk since cached probably stale
        where = "WHERE dsId = " + str(user["dsId"]) + " LIMIT 1"
        updus = dbacc.query_entity("DigAcc", where)
        updu = updus[0]
        update_user_settings_sumact_lastsend(updu, timestamp, retry=retrycount)


def send_activity_summary(user, songsum):
    plink = write_song_activity_summary(user, songsum)
    if not plink:
        plink = "Set a digname for your account to publish weekly summaries"
    subj = "DiggerHub weekly activity summary"
    body = "Account weekly summary set for " + runinfo["tdow"] + "\n"
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
        logging.info("wt20 mail sent to " + user["email"])
        update_user_settings_sumact_lastsend(user, dbacc.nowISO())
    else:
        logging.info("Summary for " + str(user["dsId"]) + "\n" + body)


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
    if lastsendts > dbacc.dt2ISO(runinfo["sod"] - datetime.timedelta(days=2)):
        return lastsendts, "", ""  # already sent recent summary
    return lastsendts, runinfo["wksts"], runinfo["wkets"]


def cieq(s1, s2, field):
    f1 = s1.get(field)
    f2 = s2.get(field)
    return f1 and f2 and f1.casefold() == f2.casefold()


def already_listed(song, songsum):
    for t20song in songsum["top20"]:
        if cieq(t20song, song, "smti") and cieq(t20song, song, "smar"):
            # smti/smar updated when song is written to db, so safe to use
            # and most intuitive match for avoiding dupes
            return True
    return False


def check_user_activity(user, settings):
    ustr = "DigAcc" + str(user["dsId"])
    errpre = "check_user_activity skipping " + ustr
    senddow = send_day_of_week(settings)
    if runinfo["tdow"] != senddow:
        logging.info(errpre + " sendon " + senddow)
        return
    lastsendts, sincets, untilts = get_last_played_timestamps(settings)
    if not sincets:
        logging.info(errpre + " not enough elapsed time since " + lastsendts)
        return
    logging.info("check_user_activity " + ustr + " " +
                 sincets[:10] + " - " + untilts[:10])
    usum = {"acct": user, "count": 0}
    songsum = {"sincets":sincets, "untilts":untilts, "top20":[]}
    # The public Top 20 should not include anything you are not comfortable
    # playing for others, nor should it include anything you think is not
    # very good.  Otherwise it's no fun to see.
    songs = dbacc.query_entity("Song", "WHERE aid = " + user["dsId"] +
                               " AND lp >= \"" + sincets + "\"" +
                               " AND lp < \"" + untilts + "\"" +
                               " AND (pd IS NULL OR pd IN (\"played\"" +
                               ", \"iosqueue\", \"digaudpl\"))" +
                               " AND kws LIKE \"%Social%\"" +
                               " AND rv >= 5" +
                               " ORDER BY rv DESC, lp DESC")
    for song in songs:
        runinfo["usersgttl"] += 1
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
    send_activity_summary(user, songsum)


def check_users():
    runinfo["userttl"] = 0     # number of active listeners
    runinfo["usersgttl"] = 0   # songs updated
    where = ("WHERE settings LIKE \"%sendon%:%" + runinfo["tdow"] + "%\"" +
             " AND EXISTS (SELECT dsId FROM Song WHERE Song.aid = DigAcc.dsId" +
             " AND lp >= \"" + runinfo["wksts"] + "\"" +
             " AND lp < \"" + runinfo["wkets"] + "\")")
    users = dbacc.query_entity("DigAcc", where)
    for user in users:
        runinfo["userttl"] += 1
        logging.info("Checking " + str(user["dsId"]) + " " + user["firstname"])
        settings = settings_for_user(user)
        check_user_activity(user, settings)
    send_hub_summary()


# Write an SASum snapshot for any user whose listening week ended today,
# using the latest song playback data.  If processing fails for any reason,
# the snapshot can be remedially constructed, but only songs that have not
# been played again more recently will be included.  Example usage:
#   python sumact.py           # write SASum, log to console
#   python sumact.py batch     # write SASum, email and update users
#   python sumact.py remed 2025-08-27T00:00:00Z
def run_with_params():
    now = datetime.datetime.utcnow()
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        runinfo["mode"] = "all"  # send mail and update digaccs
    if len(sys.argv) > 2:    # have specified ISO timestamp
        now = dbacc.ISO2dt(sys.argv[2])
    sdnvs = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday", "Never"]
    runinfo["tdow"] = sdnvs[now.weekday()]
    runinfo["sod"] = now.replace(hour=0, minute=0, second=0, microsecond=0)
    runinfo["wkets"] = dbacc.dt2ISO(runinfo["sod"])
    runinfo["wksts"] = dbacc.dt2ISO(runinfo["sod"] - datetime.timedelta(days=7))
    logging.info("Weekly activity summary " + runinfo["tdow"] +
                 " " + runinfo["wksts"] + " to " + runinfo["wkets"])
    check_users()

# run it
run_with_params()
