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
    for ecf in ["kwdefs", "igfolds", "settings", "musfs"]:
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
        return retsongs[0], "existing"
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
        return song, "updated"
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
    return song, "created"



# Convert the given album items to track items so they can be processed by
# standard import.
# Background notes:

#  - The "added_at" field contains a UTC timestamp when the item was added
#    to the library.  Presumably the latest time if they unlike something
#    and then like it again.  If a track item is individually "liked", then
#    "added_at" is at the same level as the item "track" field.  If an album
#    is "liked", then "added_at" is provided at the album level and not for
#    each track.  Presumably if a user also liked a track from the album in
#    addition to liking the album, that will be reflected when retrieving
#    liked tracks but not at the album level.
#  - For an album item, the "tracks" field contains exactly the same
#    information as if you had queried the API for the tracks on the album.
#    Each track object has the same info as for an individual liked track
#    except the "album" field is not included.
#  - Core structure of a track item:
#    {
#        "added_at" : "UTC timestamp",
#        "track" : {
#            "album" : {
#                "name" : "Name of Album",
#            },
#            "artists" : [ {
#                "name" : "Name of Band",
#            } ],
#            "disc_number" : 1,
#            "id" : "2jpDioAB9tlYXMdXDK3BGl",
#            "name" : "Name of Track",
#            "track_number" : 1
#        }
#    }
# Conversion basically consists of unpacking the "tracks" for each item and
# creating an item instance with a "track" field, and inserting the "album"
# info into it.
def convert_albums_to_tracks(items):
    ret = []
    for item in items:
        # logging.info("convert_albums_to_tracks item: " +
        #              json.dumps(item, indent=2, separators=(',', ': ')))
        album = {"name": item["album"]["name"]}
        for track in item["album"]["tracks"]["items"]:
            track["album"] = album
            ret.append({"track":track})
    return ret


def fvs_match_sql_clauses(fvs):
    where = ""
    if fvs["fpst"] == "on":
        where += (" AND el >= " + str(fvs["elmin"]) +
                  " AND el <= " + str(fvs["elmax"]) +
                  " AND al >= " + str(fvs["almin"]) +
                  " AND al <= " + str(fvs["almax"]))
        if fvs["tagfidx"] == 2:  # Untagged only
            where += " AND kws IS NULL"
        elif fvs["tagfidx"] == 1:  # Tagged only
            where += " AND kws NOT NULL"
        if fvs["poskws"]:
            for kw in fvs["poskws"].split(","):
                where += " AND FIND_IN_SET(\"" + kw + "\", kws)"
        if fvs["negkws"]:
            for kw in fvs["negkws"].split(","):
                where += (" AND ((kws IS NULL) OR (NOT FIND_IN_SET(\"" +
                          kw + "\", kws)))")
    if fvs["srchtxt"]:
        where += (" AND (ti LIKE \"%" + fvs["srchtxt"] + "%\"" +
                  " OR ar LIKE \"%" + fvs["srchtxt"] + "%\"" +
                  " OR ab LIKE \"%" + fvs["srchtxt"] + "%\")")
    return where


def fetch_matching_songs(digacc, fvs, limit):
    where = ("WHERE aid = " + digacc["dsId"] +
             " AND spid LIKE \"z:%\"" +
             " AND rv >= " + str(fvs["minrat"]))
    where += fvs_match_sql_clauses(fvs)
    if (fvs["fpst"] == "on") and (fvs["fq"] == "on"):  # freq filtering active
        now = datetime.datetime.utcnow().replace(microsecond=0)
        pst = dbacc.dt2ISO(now - datetime.timedelta(days=1))
        bst = dbacc.dt2ISO(now - datetime.timedelta(days=90))
        zst = dbacc.dt2ISO(now - datetime.timedelta(days=180))
        where += (" AND ((fq IN (\"N\", \"P\") AND lp < \"" + pst + "\")" +
                  " OR (fq = \"B\" AND lp < \"" + bst + "\")" +
                  " OR (fq = \"Z\" AND lp < \"" + zst + "\"))")
    where += " ORDER BY lp LIMIT " + str(limit)
    logging.info("songfetch " + where)
    songs = dbacc.query_entity("Song", where)
    return songs


def fetch_friend_songs(digacc, fvs, limit):
    where = ("WHERE aid IN (" + fvs["friendidcsv"] + ")" +
             " AND spid LIKE \"z:%\"" +
             " AND rv >= 8")  # 4 stars or better
    where += (" AND spid NOT IN" +
              " (SELECT spid FROM Song WHERE aid=" + digacc["dsId"] + ")")
    where += fvs_match_sql_clauses(fvs)
    where += " ORDER BY rv DESC modified DESC LIMIT " + str(limit)
    songs = dbacc.query_entity("Song", where)
    # mark the dsIds so new song instances can be created on update
    for song in songs:
        song["dsId"] = "fr" + song["dsId"]
    # two or more friends may have recommended the same song. De-dupe
    ddd = {}
    for song in songs:
        ddd[song["spid"]] = song
    return ddd.values()



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
        songs = fetch_matching_songs(digacc, fvs, 400)
        friendsongs = []
        if fvs.get("friendidcsv"):
            friendsongs = fetch_friend_songs(digacc, fvs, 100)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(songs + friendsongs)


def songupd():
    try:
        digacc, _ = util.authenticate()
        dsId = dbacc.reqarg("dsId", "dbid", required=True)
        if dsId.startswith("fr"):  # copy song suggested from music friend
            song = dbacc.cfbk("Song", "dsId", dsId[2:], required=True)
            song.dsId = ""
            song.aid = digacc["dsId"]
        else:
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


# gmaddr: musical friend mail address required for lookup. Stay personal.
def addmusf():
    try:
        digacc, _ = util.authenticate()
        gmaddr = dbacc.reqarg("gmaddr", "json", required=True)
        gacct = dbacc.cfbk("DigAcc", "email", gmaddr, required=True)
        musfs = json.loads(digacc.get("musfs") or "[]")
        # A subsequent invite after musf status was set to "Removed" is
        # more likely helpful than spam, so always recreate with latest info
        musfs = ([{"dsId": gacct["dsId"],
                   "email": gacct["email"],
                   "firstname": gacct["firstname"],
                   "hashtag": (gacct.get("hashtag") or ""),
                   "status": "New"}] +
                 [mf for mf in musfs if mf["dsId"] != gacct["dsId"]])
        digacc["musfs"] = json.dumps(musfs)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
        logging.info(digacc["email"] + " added music friend: " + gacct["email"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([digacc], audience="private")


# gid, since (timestamp). Auth required, need to know who is asking.
def musfdat():
    try:
        digacc, _ = util.authenticate()
        mfid = dbacc.reqarg("mfid", "dbid", required=True)
        since = dbacc.reqarg("since", "string") or "1970-01-01T00:00:00Z"
        logging.info(digacc["email"] + " requesting musf data from DigAcc " +
                     mfid + " since " + since)
        where = ("WHERE aid = " + mfid +
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


# Read the given items in the given dataformat (albums or tracks), and
# create or update corresponding Songs.  Update DigAcc.settings.spimport
# after successful import of all tracks to record progress.
# Notes:
#   - Because traversal of a Spotify library is done using offsets, it is
#     possible that a subsequent import may miss new additions if the user
#     first unlikes something and then likes something else.  Recovering
#     would require re-traversing the library at a later time, comparing
#     "added_at" values to when the last import was completed.  Assuming
#     that most people just add to their libraries.  If necessary, an option
#     to force a full re-import sweep could be provided.
def impsptracks():
    try:
        digacc, _ = util.authenticate()
        settings = json.loads(digacc.get("settings") or "{}")
        spi = settings.get("spimport")
        if (not spi) or ((spi["lastcheck"] > "2020" and
                          spi["lastcheck"] < "2021-07-10")):  # version check
            spi = {"lastcheck":"1970-01-01T00:00:00Z",
                   "offsets":{"albums":0, "tracks":0},
                   "imported":0}
        dataformat = dbacc.reqarg("dataformat", "string", required=True)
        items = dbacc.reqarg("items", "string", required=True)
        items = json.loads(items)
        # update offset before any data conv.  Save after all items processed.
        spi["offsets"][dataformat] += len(items)
        if dataformat == "albums":
            items = convert_albums_to_tracks(items)
        songs = []
        for item in items:
            song, updt = merge_spotify_track(digacc, item["track"])
            if updt in ["updated", "created"]:
                spi["imported"] += 1
            songs.append(song)
        settings["spimport"] = spi
        digacc["settings"] = json.dumps(settings)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([digacc] + songs, audience="private")


# Import the given spotify album/artists/tracks.  Not converting the album
# into separate tracks because it is important the resulting songs all have
# the same album/artist in order to display the complete album.
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
