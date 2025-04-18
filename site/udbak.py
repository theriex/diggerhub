""" User Data Backup File Writer """
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
        mconf.logsdir + "plg_udbak.log", when='D', backupCount=10)])
import py.util as util
import py.dbacc as dbacc
import json
import os
import zipfile
import random
import string
import urllib.parse

SITE_API_BASE_DIR = "bax"
CRON_WRITE_DIR = "diggerhub.com/" + SITE_API_BASE_DIR

def base_backup_file_name_for_user(user):
    # use the same filename each run to overwrite any previous run files
    return "bd" + str(user["dsId"])


def path_for_file_type(user, ctype, rel="cron"):
    basedir = CRON_WRITE_DIR
    if rel == "api":
        basedir = SITE_API_BASE_DIR
    return basedir + "/" + base_backup_file_name_for_user(user) + "." + ctype


def escquot(txt):
    txt = urllib.parse.quote(txt)
    return "\"" + txt + "\""


def dbsong_to_file_line_text(song, ctype):
    lnstr = "unknown ctype " + ctype
    if ctype == "json":
        lnstr = json.dumps(dbacc.db2app_Song(song))
    elif ctype == "csv":
        # aid is inferred from the file and the request
        # path is not useful for restore on a new device
        # smti/smar/smab can be recomputed
        # mddn/mdtn are read from local file metadata
        # srcid/srcrat/spid are not useful for data restore on new device
        lnstr = ",".join([str(song["dsId"]),
                          escquot(song["ti"]),
                          escquot(song["ar"]),
                          escquot(song["ab"]),
                          str(song["el"]),
                          str(song["al"]),
                          escquot(song["kws"]),
                          str(song["rv"]),
                          escquot(song["fq"]),
                          escquot(song["nt"]),
                          escquot(song["lp"]),
                          escquot(song["pd"]),
                          str(song["pc"])])
    return lnstr


def write_song_data_file(user, ctype):
    path = path_for_file_type(user, ctype)
    with open(path, "w", encoding="utf-8") as fout:
        where = ("WHERE aid=" + str(user["dsId"]) +
                 " AND ti IS NOT NULL AND ar IS NOT NULL" +
                 " AND (al != 49 OR el != 49 OR rv != 5" +
                 "      OR (kws IS NOT NULL AND kws != \"\"))" +
                 " ORDER BY modified DESC")
        songs = dbacc.query_entity("Song", where)
        linesep = "\n"
        if ctype == "json":
            fout.write("[")
            linesep = linesep + ","
        sep = ""
        for idx, song in enumerate(songs):
            if idx > 0:
                sep = linesep
            linestr = dbsong_to_file_line_text(song, ctype)
            fout.write(sep + linestr)
        if ctype == "json":
            fout.write("]\n")


def zip_song_data_file(user, ctype):
    spath = path_for_file_type(user, ctype)
    zpath = path_for_file_type(user, ctype + ".zip")
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as bfz:
        bfz.write(spath)


def write_backup_info_to_settings(user, settings):
    bakset = settings["backup"]
    bakset["writ"] = dbacc.nowISO()
    bakset["file"] = path_for_file_type(user, "csv", rel="api")
    num3 = "".join(str(random.randint(0, 9)) for _ in range(3))
    let3 = "".join(random.choice(string.ascii_lowercase) for _ in range(3))
    bakset["url"] = "bd" + num3 + let3


def write_backup(user, settings):
    # write_song_data_file(user, "json")
    # zip_song_data_file(user, "json")
    write_song_data_file(user, "csv")
    # zip_song_data_file(user, "csv")
    write_backup_info_to_settings(user, settings)
    user["settings"] = json.dumps(settings)
    try:
        dbacc.write_entity(user, user["modified"])
    except ValueError:  # version check may fail due to competing cron job
        # refetch DigAcc and redo write_entity with the updated modified
        where = "WHERE dsId = " + str(user["dsId"]) + " LIMIT 1"
        updus = dbacc.query_entity("DigAcc", where)
        updu = updus[0]
        updu["settings"] = user["settings"]
        dbacc.write_entity(updu, updu["modified"])
        user = updu
    logging.info("write_backup DigAcc" + str(user["dsId"]) + ": " +
                 json.dumps(settings["backup"]))


def find_users_and_write_backup_files():
    if not os.path.isdir(CRON_WRITE_DIR):
        os.mkdir(CRON_WRITE_DIR)
    # look back a little more than 24hrs in case the cron job is running late
    modts = dbacc.timestamp(-1 * 60 * 26)
    # only check for modified songs. The DigAcc is modified here and other
    # places which should not trigger a new backup file to be written.
    users = dbacc.query_entity("DigAcc", "WHERE dsId IN" +
                               " (SELECT DISTINCT(aid) FROM Song" +
                               " WHERE modified >= \"" + modts + "\")")
    logging.info(str(len(users)) + " users active since " + modts)
    for user in users:
        logging.info("Processing DigAcc" + str(user["dsId"]) + " " +
                     user["firstname"])
        dfltset = {}
        settings = util.load_json_or_default(user["settings"], dfltset)
        if not settings.get("backup"):
            settings["backup"] = {"writ": "1970-01-01T00:00:00Z"}
        write_backup(user, settings)


# run it
find_users_and_write_backup_files()
