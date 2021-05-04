""" Songs and related data access processing. """
#pylint: disable=line-too-long
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy

import logging
import json
import datetime
import base64
import requests
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


def song_string(song):
    return song["ti"] + " - " + song.get("ar") + " - " + song.get("ab")


def is_unrated_song(song):
    unrated = (not song["kws"]) and (song["el"] == 49) and (song["al"] == 49)
    return unrated


def write_song(updsong, digacc):
    """ Write the given update song. """
    updsong["aid"] = digacc["dsId"]
    normalize_song_fields(updsong)
    # logging.info("appdat.write_song " + str(updsong))
    song = find_song(updsong)
    if not song:  # create new
        song = {"dsType":"Song", "aid":digacc["dsId"]}
    else: #updating existing song instance
        if is_unrated_song(updsong) and not is_unrated_song(song):
            # should never happen due to hub push before hub receive, but
            # leaving in place as a general protective measure.
            updsong = song  # ignore updsong to avoid information loss
            logging.info("write_song not unrating " + song_string(song))
    flds = {  # do NOT copy general db fields from client data. only these:
        # field defs copied from dbacc.py
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
        racc["hubVersion"] = util.version()
        syncdata = [racc] + rsongs
        logging.info(msg + " " + digacc["email"] + " " + str(len(rsongs)) +
                     " songs")
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(syncdata, audience="private")  # include email


def songfetch():
    try:
        digacc, _ = util.authenticate()
        fvs = json.loads(dbacc.reqarg("fvs", "json", required=True))
        where = ("WHERE aid = " + digacc["dsId"] +
                 " AND spid LIKE \"z:%\"" +
                 " AND el >= " + str(fvs["elmin"]) +
                 " AND el <= " + str(fvs["elmax"]) +
                 " AND al >= " + str(fvs["almin"]) +
                 " AND al <= " + str(fvs["almax"]) +
                 " AND rv >= " + str(fvs["minrat"]))
        if fvs["tagfidx"] == 2:  # Untagged only
            where += " AND kws IS NULL"
        elif fvs["tagfidx"] == 1:  # Tagged only
            where += " AND kws NOT NULL"
        if fvs["poskws"]:
            for kw in fvs["poskws"].split(","):
                where += " AND FIND_IN_SET(\"" + kw + "\", kws)"
        if fvs["negkws"]:
            for kw in fvs["negkws"].split(","):
                where += " AND NOT FIND_IN_SET(\"" + kw + "\", kws)"
        if fvs["srchtxt"]:
            where += (" AND (ti LIKE \"%" + fvs["srchtxt"] + "%\"" +
                      " OR ar LIKE \"%" + fvs["srchtxt"] + "%\"" +
                      " OR ab LIKE \"%" + fvs["srchtxt"] + "%\"")
        if fvs["fq"] == "on":  # frequency filtering active
            now = datetime.datetime.utcnow().replace(microsecond=0)
            pst = dbacc.dt2ISO(now - datetime.timedelta(days=1))
            bst = dbacc.dt2ISO(now - datetime.timedelta(days=90))
            zst = dbacc.dt2ISO(now - datetime.timedelta(days=180))
            where += (" AND ((fq IN (\"N\", \"P\") AND lp < \"" + pst + "\")" +
                      " OR (fq = \"B\" AND lp < \"" + bst + "\")" +
                      " OR (fq = \"Z\" AND lp < \"" + zst + "\"))")
        where += " ORDER BY lp LIMIT 400"
        logging.info("songfetch " + where)
        songs = dbacc.query_entity("Song", where)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(songs)


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


# https://developer.spotify.com/documentation/general/guides/authorization-guide
# For now the approach is to use the granted token as long as possible, then
# go back for a full new one rather than using a the returned refresh token.
# Easier to implement, information may be stale if the app was inactive for
# a while, and scopes may change as things develop further.
def spotifytoken():
    try:
        digacc, _ = util.authenticate()
        hubdat = json.loads(digacc["hubdat"])
        svcdef = util.get_connection_service("spotify")
        svckey = svcdef["ckey"] + ":" + svcdef["csec"]
        authkey = base64.b64encode(svckey.encode("UTF-8")).decode("UTF-8")
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": "Basic " + authkey},
            data={"grant_type": "authorization_code",
                  "code": hubdat["spa"]["code"],
                  "redirect_uri": svcdef["data"]})
        if resp.status_code != 200:
            raise ValueError("Code for token exchange failed " +
                             str(resp.status_code) + ": " + resp.text)
        tokinfo = resp.json()
        tokinfo["useby"] = dbacc.timestamp((tokinfo["expires_in"] - 1) // 60)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(tokinfo)
