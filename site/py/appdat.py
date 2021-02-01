""" Songs and related data access processing. """
#pylint: disable=line-too-long
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy

import logging
import json
import py.dbacc as dbacc
import py.util as util


def dqe(text):
    return text.replace("\"", "\\\"")


# It is NOT ok to look up the song by dsId.  An uploaded song can have a
# dsId that should not be trusted.  Doing so could overwrite someone else's
# data or create duplicate entries.  This is not even malicious, it can
# happen with multiple users on the same data file, copying data, running a
# local dev server etc.  The metadata rules.  It's acceptable to end up with
# a new db entry if you change the song metadata.  While it might be
# possible to avoid that by tracking the aid and path, in reality paths
# change more frequently than metadata and are not reliable. Not worth the
# overhead and complexity from trying.  Always look up by logical key.
def find_song(spec):
    """ Lookup by aid/title/artist/album, return song instance or None """
    where = ("WHERE aid = " + spec["aid"] +
             " AND ti = \"" + dqe(spec["ti"]) + "\"" +
             " AND ar = \"" + dqe(spec["ar"]) + "\"" +
             " AND ab = \"" + dqe(spec["ab"]) + "\"" +
             # should never be more than one, but just in case...
             " ORDER BY modified DESC LIMIT 1")
    songs = dbacc.query_entity("Song", where)
    if len(songs) > 0:
        return songs[0]
    return None


def normalize_song_fields(updsong):
    """ Verify needed fields are defined and not padded. """
    updsong["dsType"] = "Song"
    for matchfield in ["ti", "ar", "ab"]:
        updsong[matchfield] = updsong.get(matchfield, "")
        updsong[matchfield] = updsong[matchfield].strip()
    if not updsong["ti"] and updsong.get("path"):
        # better to save with synthetic metadata than to ignore, even if
        # ti != path due to truncation
        updsong["ti"] = updsong.get("path")


def write_song(updsong, digacc):
    """ Write the given update song. """
    updsong["aid"] = digacc["dsId"]
    normalize_song_fields(updsong)
    logging.info("appdat.write_song " + str(updsong))
    song = find_song(updsong)
    if song:
        for field, fdesc in dbacc.entdefs["Song"].items():
            song[field] = updsong.get(field, fdesc["dv"])
    else:
        song = updsong
    updsong = dbacc.write_entity(song, song.get("modified", ""))
    return updsong


def note_sync_account_changes(srvacc, synacc, upldsongs):
    if srvacc["modified"] > synacc["modified"]:
        # If srvacc is newer, then the account was last updated from a
        # different datastore than the synacc source.  Return srvacc so the
        # synacc datastore can update to the latest.  Ignore any sent music
        # files since they may be older than what is currently in the db.
        srvacc["syncstat"] = "Changed"  # tell client their account is old
        return srvacc
    # write all given songs so they will be older than updacc.modified
    for song in upldsongs:  # write all given songs so older than updacc
        write_song(song, srvacc)
    # synacc may contain updates to client fields.  It may not contain
    # updates to hub server fields like email.
    for ecf in ["kwdefs", "igfolds", "settings", "guides"]:
        if synacc[ecf] and srvacc[ecf] != synacc[ecf]:
            srvacc[ecf] = synacc[ecf]
    # always update the account so modified reflects latest sync
    updacc = dbacc.write_entity(srvacc, srvacc["modified"])
    updacc["syncstat"] = "Unchanged"  # tell client their account is up to date
    return updacc


# When a sync call is received, find all the songs that have been previously
# written that are newer than the given sync time.  After this call,
# digacc.modified will be updated, and the song.modified will no longer be
# newer, so all the newer songs need to be retrieved in one shot.  Normally
# that should not be excessive, but it is possible that reactivating a long
# dormant digger app install could trigger a massive number of song
# downloads.  Song data is not large, but some kind of limit needs to be in
# place.  Anything beyond this limit will essentially not be synced.
def find_sync_push_songs(aid, prevsync):
    # Find any previously updated song data that needs to be downloaded
    where = ("WHERE aid = " + aid +
             " AND modified > \"" + prevsync + "\""
             " ORDER BY modified DESC LIMIT 3000")
    pushsongs = dbacc.query_entity("Song", where)
    return pushsongs


############################################################
## API endpoints:

# Received syncdata is the DigAcc followed by zero or more updated Songs.
def hubsync():
    try:
        digacc, _ = util.authenticate()
        syncdata = json.loads(dbacc.reqarg("syncdata", "json", required=True))
        updacc = syncdata[0]
        prevsync = updacc.get("syncsince") or updacc["modified"]
        upldsongs = syncdata[1:]
        maxsongs = 200  # keep low enough to not exceed worker thread max time
        if len(upldsongs) > maxsongs:
            return util.serve_value_error("Request exceeded max " + maxsongs +
                                          " songs per sync.")
        # get the songs to return before making any changes, so state is known
        pushsongs = find_sync_push_songs(digacc["dsId"], prevsync)
        updacc = note_sync_account_changes(digacc, updacc, upldsongs)
        logging.info("hubsync " + updacc["email"] + " since " + prevsync +
                     " (" + updacc["syncstat"] + ") songs up: " +
                     str(len(upldsongs)) + " down: " + str(len(pushsongs)))
        syncdat = [updacc] + pushsongs
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(syncdat, audience="private")  # include email


# gmaddr: guide mail address required for lookup. Stay personal.
def addguide():
    try:
        digacc, _ = util.authenticate()
        gmaddr = dbacc.reqarg("gmaddr", "json", required=True)
        gacct = dbacc.cfbk("DigAcc", "email", gmaddr, required=True)
        guides = json.loads(digacc.get("guides") or "[]")
        guides = ([{"dsId": gacct["dsId"],
                    "email": gacct["email"],
                    "firstname": gacct["firstname"],
                    "hashtag": (gacct.get("hashtag") or "")}] +
                  [g for g in guides if g["dsId"] != gacct["dsId"]])
        digacc["guides"] = json.dumps(guides)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
        logging.info(digacc["email"] + " added guide: " + gacct["email"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([digacc], audience="private")


# gid, since (timestamp). Auth required, need to know who is asking.
def guidedat():
    try:
        digacc, _ = util.authenticate()
        gid = dbacc.reqarg("gid", "dbid", required=True)
        since = dbacc.reqarg("since", "string") or "1970-01-01T00:00:00Z"
        logging.info(digacc["email"] + " requesting guide data from guide " +
                     gid + " since " + since)
        where = ("WHERE aid = " + gid +
                 " AND modified > \"" + since + "\""
                 " ORDER BY modified LIMIT 1000")
        gdat = dbacc.query_entity("Song", where)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(gdat)
