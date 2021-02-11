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
    # logging.info("appdat.write_song " + str(updsong))
    song = find_song(updsong)
    if not song:  # create new
        song = {"dsType":"Song"}
    flds = {  # do not copy core db fields from client data. only these:
        "path": {"pt": "string", "un": False, "dv": ""},
        "ti": {"pt": "string", "un": False, "dv": ""},
        "ar": {"pt": "string", "un": False, "dv": ""},
        "ab": {"pt": "string", "un": False, "dv": ""},
        "el": {"pt": "int", "un": False, "dv": 0},
        "al": {"pt": "int", "un": False, "dv": 0},
        "kws": {"pt": "string", "un": False, "dv": ""},
        "rv": {"pt": "int", "un": False, "dv": 0},
        "fq": {"pt": "string", "un": False, "dv": ""},
        "lp": {"pt": "string", "un": False, "dv": ""},
        "nt": {"pt": "string", "un": False, "dv": ""}}
    for field, fdesc in flds.items():
        song[field] = updsong.get(field, fdesc["dv"])
    updsong = dbacc.write_entity(song, song.get("modified") or "")
    return updsong


def find_hub_push_songs(digacc, prevsync):
    maxsongs = 200
    where = ("WHERE aid = " + digacc["dsId"] +
             " AND modified > \"" + prevsync + "\""
             " ORDER BY modified LIMIT " + str(maxsongs))
    retsongs = dbacc.query_entity("Song", where)
    if len(retsongs) >= maxsongs:  # let client know more to download
        digacc["syncsince"] = retsongs[-1]["modified"]
    return digacc, retsongs


def receive_updated_songs(digacc, updacc, songs):
    maxsongs = 200
    if len(songs) > maxsongs:
        raise ValueError("Request exceeded max " + str(maxsongs) + " songs")
    retsongs = []
    for song in songs:
        # if any given song write fails, continue so the client doesn't
        # just retry forever.  Leave for general log monitoring.
        try:
            retsongs.append(write_song(song, digacc))
        except ValueError as e:
            logging.warning("receive_updated_songs write_song " + str(e))
    # updacc may contain updates to client fields.  It may not contain
    # updates to hub server fields like email.
    for ecf in ["kwdefs", "igfolds", "settings", "guides"]:
        if updacc.get(ecf) and updacc[ecf] != digacc[ecf]:
            digacc[ecf] = updacc[ecf]
    # always update the account so modified reflects latest sync
    digacc = dbacc.write_entity(digacc, digacc["modified"])
    return digacc, retsongs


############################################################
## API endpoints:

# Received syncdata is the DigAcc followed by zero or more updated Songs.
# See digger/docroot/docs/hubsyncNotes.txt
def hubsync():
    try:
        digacc, _ = util.authenticate()
        syncdata = json.loads(dbacc.reqarg("syncdata", "json", required=True))
        updacc = syncdata[0]
        prevsync = updacc.get("syncsince") or updacc["modified"]
        if prevsync < digacc["modified"]:  # hub push
            racc, rsongs = find_hub_push_songs(digacc, prevsync)
            msg = "hub push"
        else: # hub receive
            racc, rsongs = receive_updated_songs(digacc, updacc, syncdata[1:])
            msg = "hub receive"
        syncdata = [racc] + rsongs
        logging.info(msg + " " + digacc["email"] + " " + str(len(rsongs)) +
                     " songs")
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(syncdata, audience="private")  # include email


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
                 " ORDER BY modified LIMIT 200")
        gdat = dbacc.query_entity("Song", where)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(gdat)


# Collab actions are logged by the recipient.
def collabs():
    try:
        digacc, _ = util.authenticate()
        cacts = dbacc.reqarg("cacts", "string", required=True)
        cacts = json.loads(cacts)
        for cact in cacts:
            if cact["rec"] != digacc["dsId"]:
                raise ValueError("rec " + cact["rec"] + " != " + digacc["dsId"])
            if cact["ctype"] != "inrat":
                raise ValueError("Unknown ctype: " + cact["ctype"])
            cact["dsType"] = "Collab"
        resacts = []
        for cact in cacts:
            resacts.append(dbacc.write_entity(cact))
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(resacts)
