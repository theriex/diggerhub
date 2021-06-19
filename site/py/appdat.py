""" Songs and related data access processing. """
#pylint: disable=line-too-long
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy

import logging
import json
import datetime
import py.dbacc as dbacc
import py.util as util


def dqe(text):
    return text.replace("\"", "\\\"")

def dqv(text):
    return "\"" + dqe(text) + "\""

def strl2inexp(strl):
    return "(" + ", ".join([dqv(name) for name in strl]) + ")"


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


# When importing from Spotify, title details like parenthetical expressions
# can reference a different song.  Matching too broadly is unsafe.  Rather
# create a perceived duplicate than create a broken mapping.
def spotmatch(song, spid, title):
    if song["spid"] == spid or song["ti"].lower() == title.lower():
        return True
    return False


# All songs need a path for client album display sorting
def make_song_path(discnum, tracknum, artist, album, title):
    discnum = discnum or 1
    tno = str(discnum).zfill(2) + "_" + str(tracknum).zfill(2)
    return artist + "/" + album + "/" + tno + " " + title


# Seems like all Spotify tracks have an album, but synthesize if not.
def spotify_track_album(track):
    album = "Singles"
    if "album" in track:
        album = track["album"]["name"]
    return album


def path_for_spotify_track(track):
    artist = track["artists"][0]["name"]
    album = spotify_track_album(track)
    title = track["name"]
    dno = track["disc_number"]
    tno = track["track_number"]
    return make_song_path(dno, tno, artist, album, title)


def merge_spotify_track(digacc, track):
    spid = "z:" + track["id"]
    # lookup by aid/spid to check if track already exists
    where = "WHERE aid = " + digacc["dsId"] + " AND spid = " + dqv(spid)
    retsongs = dbacc.query_entity("Song", where)
    if len(retsongs) >= 1:
        return None   # track already exists, no updated data
    # lookup by ti/ar/ab, checking all artists.  Assumption local db
    # contents has already been best effort spidmapper matched.  Dupes handled
    # by dupe detection flagging and playback chaining.
    where = "WHERE aid = " + digacc["dsId"] + " AND ti = " + dqv(track["name"])
    if "album" in track:
        where += " AND ab = " + dqv(track["album"]["name"])
    where += " AND ar IN " + strl2inexp(a["name"] for a in track["artists"])
    logging.info("merge_spotify_track " + where)
    retsongs = dbacc.query_entity("Song", where)
    if len(retsongs) >= 1:
        song = retsongs[0]
        song["spid"] = spid
        song = dbacc.write_entity(song, song["modified"])
        return song
    # no existing song found, add new with sortable path for album view
    song = {"dsType": "Song", "aid": digacc["dsId"], "batchconv": "spidimp",
            "path": path_for_spotify_track(track),
            "ti": track["name"],
            "ar": track["artists"][0]["name"],
            "ab": spotify_track_album(track),
            "el": 49, "al": 49, "kws": "",
            "rv": 7,  # above average since they liked it
            "fq": "P",  # playable rather than newly added since filling in lp
            "lp": dbacc.timestamp(-1 * 60 * 24),  # yesterday, so ok to play now
            "nt": "", "spid": spid}
    song = dbacc.write_entity(song)
    return song



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
                      " OR ab LIKE \"%" + fvs["srchtxt"] + "%\")")
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


def songupd():
    try:
        digacc, _ = util.authenticate()
        dsId = dbacc.reqarg("dsId", "dbid", required=True)
        song = dbacc.cfbk("Song", "dsId", dsId, required=True)
        if song["aid"] != digacc["dsId"]:
            raise ValueError("Song author id mismatch")
        util.set_fields_from_reqargs(["ti", "ar", "ab", "kws", "fq", "lp",
                                      "nt", "spid"], song)
        util.set_fields_from_reqargs(["el", "al", "rv"], song, "int")
        song = dbacc.write_entity(song, song["modified"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([song])


def multiupd():
    try:
        digacc, _ = util.authenticate()
        songs = json.loads(dbacc.reqarg("songs", "json", required=True))
        flds = ["lp"]  # can expand as needed, support known needs only
        for idx, song in enumerate(songs):
            if song["aid"] != digacc["dsId"]:
                raise ValueError("Song author id mismatch")
            dbsong = dbacc.cfbk("Song", "dsId", song["dsId"], required=True)
            for fld in flds:
                dbsong[fld] = song[fld]
            songs[idx] = dbacc.write_entity(dbsong, dbsong["modified"])
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
        # A subsequent invite after a guide status was set to "Deleted" is
        # more likely helpful than spam.  So always recreate with latest info
        guides = ([{"dsId": gacct["dsId"],
                    "email": gacct["email"],
                    "firstname": gacct["firstname"],
                    "hashtag": (gacct.get("hashtag") or ""),
                    "status": "New"}] +
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


# Auth required.  Updates DigAcc.settings.songcounts
def songttls():
    try:
        digacc, _ = util.authenticate()
        settings = json.loads(digacc.get("settings") or "{}")
        scs = settings.get("songcounts") or {"posschg": ""}
        totals = dbacc.fetch_song_counts(digacc["dsId"])[0]
        scs["fetched"] = dbacc.nowISO()
        scs["hubdb"] = totals["hubdb"]
        scs["spotify"] = totals["spotify"]
        settings["songcounts"] = scs
        digacc["settings"] = json.dumps(settings)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([digacc], audience="private")


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


# Walk all the given tracks and create or update Songs.  Update DigAcc
# settings spimport to reflect work done.
#  - lastcheck: ISO timestamp when Spotify last checked.  On app startup, if
#    this value was more than 24 hours ago, then import processing reads
#    songs until the "added_at" value of a song is older than this value.
#  - initsync: ISO timestamp filled after all spotify library tracks imported.
#  - processed: Count of how many spotify library songs have been checked.
#    Equivalent to the paging offset while import is ongoing.
#  - imported: Count of how many DiggerHub songs created.
def impsptracks():
    try:
        digacc, _ = util.authenticate()
        settings = json.loads(digacc.get("settings") or "{}")
        spi = settings.get("spimport", {"lastcheck":"1970-01-01T00:00:00Z",
                                        "initsync":"",
                                        "processed":0,
                                        "imported":0})
        songs = []
        items = dbacc.reqarg("items", "string", required=True)
        items = json.loads(items)
        if len(items) > 0:
            for item in items:
                song = merge_spotify_track(digacc, item["track"])
                if song:
                    songs.append(song)
                    spi["imported"] += 1
                spi["processed"] += 1
            settings["spimport"] = spi
        else:  # no more items to import, note completed
            ts = dbacc.nowISO()
            spi["initsync"] = spi.get("initsync") or ts
            spi["lastcheck"] = ts
        digacc["settings"] = json.dumps(settings)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([digacc] + songs, audience="private")


# Import the given spotify album/artists/tracks
def spabimp():
    try:
        digacc, _ = util.authenticate()
        abinf = dbacc.reqarg("abinf", "string", required=True)
        abinf = json.loads(abinf)
        album = abinf["album"]
        # Fetch known existing songs from album and choose listing artist
        where = ("WHERE aid = " + digacc["dsId"] +
                 " AND ab = \"" + album + "\"" +
                 " AND ar IN " + strl2inexp(abinf["artists"]) +
                 " ORDER BY modified DESC LIMIT 100")
        kns = dbacc.query_entity("Song", where)
        if len(kns) > 0:
            artist = kns[0]["ar"]
        else:
            artist = abinf["artists"][0]
        # convert tracks into song instances
        songs = []
        for track in abinf["tracks"]:
            title = track["name"]
            spid = "z:" + track["tid"]
            song = next((s for s in kns if spotmatch(s, spid, title)), None)
            if not song:
                song = {"dsType": "Song", "aid": digacc["dsId"],
                        "batchconv": "spalbimp",
                        "path": make_song_path(track["dn"], track["tn"],
                                               artist, abinf["album"], title),
                        "ti": title,
                        "ar": artist,
                        "ab": album,
                        "el": 49, "al": 49, "kws": "",
                        "rv": 5,  # standard import value
                        "fq": "N",  # Newly added
                        "lp": "",
                        "nt": "", "spid": spid}
                logging.info("spabimp adding " + song["path"])
                song = dbacc.write_entity(song)
            elif not song["spid"].startswith("z:"):
                song["spid"] = spid
            songs.append(song)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(songs)
