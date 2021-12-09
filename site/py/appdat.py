""" Songs and related data access processing. """
#pylint: disable=line-too-long
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy

import logging
import json
import datetime
import re
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
def find_song(spec, ovrs=None):
    """ Lookup by aid/title/artist/album, return song instance or None """
    where = ("WHERE aid = " + spec["aid"] +
             " AND ti = \"" + dqe(spec["ti"]) + "\"" +
             " AND ar = \"" + dqe(spec["ar"]) + "\"" +
             " AND ab = \"" + dqe(spec["ab"]) + "\"" +
             # should never be more than one, but just in case...
             " ORDER BY modified DESC LIMIT 1")
    songs = dbacc.query_entity("Song", where)
    if len(songs) > 0:
        ret = songs[0]
        if ovrs:
            for key, val in ovrs.items():
                ret[key] = val
        return ret
    return None


def normalize_song_fields(updsong, digacc):
    """ Verify needed fields are defined and not padded. """
    updsong["dsType"] = "Song"
    updsong["aid"] = digacc["dsId"]
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


# The default mySQL isolation level of repeatable read means it is possible
# to read an older instance from the database query cache despite the
# instance having been updated and committed.
def max_modified_value(sa, sb):
    sam = sa.get("modified", "")
    sbm = sb.get("modified", "")
    if sam > sbm:
        return sam
    return sbm


# If the song spid was previously mapped successfully, then leave it to
# avoid undoing any manual support effort involved finding the correct
# track.  If a song has the wrong spid, that can be reported through the
# tuning options.
def reset_dead_spid_if_metadata_changed(updsong, dbsong):
    if (dbsong.get("spid", "").startswith("z:") and (
            (updsong.get("ti", "") != dbsong.get("ti", "")) or
            (updsong.get("ar", "") != dbsong.get("ar", "")) or
            (updsong.get("ab", "") != dbsong.get("ab", "")))):
        dbsong["spid"] = ""


def standarized_colloquial_match(txt):
    scm = txt
    scm = re.sub(r"\(.*", "", scm)  # remove trailing parentheticals
    scm = re.sub(r"\[.*", "", scm)  # remove trailing bracket text
    scm = re.sub(r"featuring.*", "", scm, flags=re.IGNORECASE)
    scm = scm.strip()
    return scm


def rebuild_derived_song_fields(song):
    song["smti"] = standarized_colloquial_match(song["ti"])
    song["smar"] = standarized_colloquial_match(song["ar"])
    song["smab"] = standarized_colloquial_match(song["ab"])


def update_song_fields(updsong, dbsong):
    reset_dead_spid_if_metadata_changed(updsong, dbsong)
    flds = {  # do NOT copy general db fields from client data. only these:
        # see dbacc.py for field defs
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
        "nt": {"pt": "string", "un": False, "dv": ""},
        "pc": {"pt": "int", "un": False, "dv": 0},
        "srcid": {"pt": "string", "un": False, "dv": ""},
        "srcrat": {"pt": "string", "un": False, "dv": ""}}
    for field, fdesc in flds.items():
        dbsong[field] = updsong.get(field, fdesc["dv"])
    rebuild_derived_song_fields(dbsong)


def write_song(updsong, digacc, forcenew=False):
    """ Write the given update song. """
    normalize_song_fields(updsong, digacc)
    # logging.info("appdat.write_song " + str(updsong))
    song = None
    if not forcenew:
        song = find_song(updsong)
    if not song:  # create new
        song = {"dsType":"Song", "aid":digacc["dsId"]}
    else: # updating existing song instance
        if is_unrated_song(updsong) and not is_unrated_song(song):
            # should never happen due to hub push before hub receive, but
            # leaving in place as a general protective measure.
            updsong = song  # ignore updsong to avoid information loss
            logging.info("write_song not unrating " + song_string(song))
        song["modified"] = max_modified_value(updsong, song)
    update_song_fields(updsong, song)
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


# undo client top.js txSgFmt
def unescape_song_fields(song):
    for fld in ["ti", "ar", "ab", "path"]:
        song[fld] = song[fld].replace("&#40;", "(")
        song[fld] = song[fld].replace("&#41;", ")")


def receive_updated_songs(digacc, updacc, songs):
    maxsongs = 200
    if len(songs) > maxsongs:
        raise ValueError("Request exceeded max " + str(maxsongs) + " songs")
    retsongs = []
    for song in songs:
        unescape_song_fields(song)
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
    rebuild_derived_song_fields(song)
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
            where += " AND kws IS NOT NULL"
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
             " AND rv >= 8" +  # 4 stars or better
             " AND spid NOT IN" +
             " (SELECT spid FROM Song WHERE aid=" + digacc["dsId"] + ")")
    where += fvs_match_sql_clauses(fvs)
    where += " ORDER BY rv DESC, modified DESC LIMIT " + str(limit)
    logging.info("fetch_friend_songs " + where)
    songs = dbacc.query_entity("Song", where)
    # mark the dsIds so new song instances can be created on update
    for song in songs:
        song["dsId"] = "fr" + song["dsId"]
    # two or more friends may have recommended the same song. De-dupe
    ddd = {}
    for song in songs:
        ddd[song["spid"]] = song
    return list(ddd.values())


def add_music_friend(digacc, mfacct):
    musfs = json.loads(digacc.get("musfs") or "[]")
    for mf in musfs:  # verify and update existing data
        fstat = mf.get("status")
        if (not fstat) or (fstat not in ["Active", "Inactive", "Removed"]):
            mf["status"] = "Inactive"
    musfs = ([{"dsId": mfacct["dsId"],
               "email": mfacct["email"],
               "firstname": mfacct["firstname"],
               "hashtag": (mfacct.get("hashtag") or ""),
               "status": "Active"}] +
             [mf for mf in musfs if mf["dsId"] != mfacct["dsId"]])
    digacc["musfs"] = json.dumps(musfs)
    digacc = dbacc.write_entity(digacc, digacc["modified"])
    logging.info(digacc["email"] + " added friend: " + mfacct["email"])
    return digacc


# Returns a list of saved songs corresponging to the uploaded songs, or
# raises an error.  The uplds list may contain multiple songs (with
# different paths) that save to the same Song dsId, so avoid writing
# multiple times to keep the "modified" value consistent.  Reset the
# checksince value for all music friends.
def save_uploaded_songs(digacc, uplds, maxret):
    if len(uplds) > maxret:
        raise ValueError("Max song uplds: " + maxret +
                         ", received " + str(len(uplds)))
    prevsaved = {}
    prcsongs = []
    for song in uplds:
        if not song.get("ti"):
            raise ValueError("Missing ti (title) value " + song.get("path"))
        if not song.get("ar"):
            raise ValueError("Missing ar (artist) value " + song.get("ti"))
        if not song.get("path"):
            raise ValueError("Missing path value " + song.get("ti", "") +
                             " - " + song.get("ar", ""))
        normalize_song_fields(song, digacc)
        skey = dbacc.get_song_key(song)
        if not prevsaved.get(skey):
            prevsaved[skey] = find_song(song, ovrs={"path":song["path"]})
        if not prevsaved.get(skey):
            prevsaved[skey] = write_song(song, digacc, forcenew=True)
        prcsongs.append(prevsaved.get(skey))
    if len(prcsongs) > 0:
        musfs = json.loads(digacc.get("musfs") or "[]")
        for mf in musfs:
            mf["checksince"] = "1970-01-01T00:00:00Z"
        digacc["musfs"] = json.dumps(musfs)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
    return [digacc] + prcsongs


def append_default_ratings_from_friend(digacc, mf, prcsongs, maxret):
    if len(prcsongs) >= maxret:
        return False # have enough songs already
    checksince = mf.get("checksince", "1970-01-01T00:00:00Z")
    chkthresh = dbacc.ISO2dt(checksince) + datetime.timedelta(days=1)
    chkthresh = dbacc.dt2ISO(chkthresh)
    if chkthresh > dbacc.nowISO():
        return False # already checked today
    sflim = maxret - len(prcsongs)
    cds = dbacc.collaborate_default_ratings(digacc["dsId"], mf["dsId"],
                                            since=checksince, limit=sflim)
    if len(cds) > 0:
        rfs = ["el", "al", "rv", "kws"]  # rating fields
        for song in cds:
            mf["checksince"] = song["mfcreated"]
            mf["dhcontrib"] = mf.get("dhcontrib", 0) + 1
            song["srcid"] = song["mfid"]
            song["srcrat"] = ":".join([str(song[v]) for v in rfs])
            # cds may contain duplicate songs due to join expansion. 14sep21
            # No need for overhead of querying for version before writing.
            prcsongs.append(dbacc.write_entity(song, vck="override"))
    else:
        mf["checksince"] = dbacc.nowISO()
    logging.info(mf.get("firstname") + " " + mf["dsId"] + " contributed " +
                 str(len(cds)) + " default ratings for " +
                 digacc.get("firstname") + " " + digacc["dsId"])
    return True


def fill_default_ratings_from_friends(digacc, maxret):
    prcsongs = []
    accmod = False
    musfs = json.loads(digacc.get("musfs") or "[]")
    for mf in (mf for mf in musfs if mf.get("status") == "Active"):
        if append_default_ratings_from_friend(digacc, mf, prcsongs, maxret):
            accmod = True
    if accmod:  # write updated checksince times for musfs
        digacc["musfs"] = json.dumps(musfs)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
    return [digacc] + prcsongs


# For each friend rated song, if the srcrat is the same as the current
# settings, revert the song to unrated.  Clear srcid and srcrat.  Return a
# list of all updated Songs.
# This does not change the dhcontrib count of the music friend.  That's left
# up to the caller who is presumably clearing all their ratings in
# preparation for removing the friend.
def clear_default_ratings_from_friend(digacc, mfid, maxret):
    where = ("WHERE aid=" + digacc["dsId"] + " AND srcid=" + mfid +
             " LIMIT " + str(maxret))
    songs = dbacc.query_entity("Song", where)
    logging.info("clearing " + str(len(songs)) + " default ratings from " +
                 mfid + " for " + digacc["dsId"])
    res = []
    rfs = ["el", "al", "rv", "kws"]  # rating fields
    for song in songs:
        rats = dict(zip(rfs, song["srcrat"].split(":")))
        changed = False
        for fld in rfs:
            if str(song[fld]) != rats[fld]:
                changed = True
        if not changed:  # reset to default unrated (remove mf values)
            song["el"] = 49
            song["al"] = 49
            song["rv"] = 5
            song["kws"] = ""
        song["srcid"] = ""
        song["srcrat"] = ""
        res.append(dbacc.write_entity(song, song["modified"]))
    return res


def fetchcreate_song_from_friend(digacc, updsong):
    dsId = updsong["dsId"]
    logging.info("fetchcreate_song_from_friend updsong " + dsId)
    frsong = dbacc.cfbk("Song", "dsId", dsId[2:], required=True)
    dbsong = find_song({"aid":digacc["dsId"], "ti":updsong["ti"],
                        "ar":updsong["ar"], "ab":updsong["ab"]})
    if not dbsong:  # copy friend song data into new instance
        dbsong = frsong
        dbsong["dsId"] = ""
        dbsong["aid"] = digacc["dsId"]
    update_song_fields(updsong, dbsong)
    if updsong.get("spid"):
        dbsong["spid"] = updsong["spid"]
    return dbsong


def fetchcreate_song_from_spid(digacc, updsong):
    dsId = updsong["dsId"]
    logging.info("fetchcreate_song_from_spid updsong " + dsId)
    spid = dsId[len("spotify"):]
    if not spid.startswith("z:"):  # z:tid indicates successful mapping
        raise ValueError("Invalid spid " + str(spid))
    where = ("WHERE aid = " + digacc["dsId"] +
             " AND spid = \"" + spid + "\"" +
             " ORDER BY MODIFIED DESC LIMIT 1")
    songs = dbacc.query_entity("Song", where)
    if len(songs) > 0:     # song already exists. Do not overwrite existing
        dbsong = songs[0]  # field values with given default values.
        dbsong["lp"] = updsong["lp"]  # Update last played and play count
        dbsong["pc"] = updsong.get("pc", 0) + 1
        return dbsong
    # Spotify disc number and track number must be included in updsong
    updsong["path"] = make_song_path(updsong["spdn"], updsong["sptn"],
                                     updsong["ar"], updsong["ab"],
                                     updsong["ti"])
    dbsong = {"dsType":"Song", "aid":digacc["dsId"], "spid":spid, "modified":""}
    update_song_fields(updsong, dbsong)
    return dbsong


def update_song_by_id(digacc, updsong):
    logging.info("update_song_by_id updsong " + updsong["dsId"])
    if updsong["aid"] != digacc["dsId"]:
        raise ValueError("Song author id mismatch")
    dbsong = dbacc.cfbk("Song", "dsId", updsong["dsId"], required=True)
    update_song_fields(updsong, dbsong)
    if updsong.get("spid"):
        dbsong["spid"] = updsong["spid"]
    return dbsong


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
        # provide context for subsequent log messages
        logging.info("hubsync -> " + digacc["email"] + "prevsync: " + prevsync)
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


# The song is passed in JSON format because string fields like the title can
# trigger modsec rules if unencoded. 30oct21-ep
def songupd():
    try:
        digacc, _ = util.authenticate()
        songdat = dbacc.reqarg("songdat", "json", required=True)
        song = json.loads(songdat)
        dsId = song.get("dsId")
        if not dsId:
            raise ValueError("dsId required")
        if dsId.startswith("fr"):  # song suggested from music friend
            song = fetchcreate_song_from_friend(digacc, song)
        elif dsId.startswith("spotify"):  # song direct play from Spotify
            song = fetchcreate_song_from_spid(digacc, song)
        else: # standard update from web player
            song = update_song_by_id(digacc, song)
        # always write song to reflect the modified time and any mod fields
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


# mfaddr: music friend mail address required for lookup. Stay personal.
# Sorting of friends and changing their status is handled client side.  This
# adds the new music friend at the beginning of the list after verifying
# the account exists.  Existing intances are checked and minimally modified
# to reflect the ordering and status updates implied by adding a new friend.
def addmusf():
    try:
        digacc, _ = util.authenticate()
        mfaddr = dbacc.reqarg("mfaddr", "json", required=True)
        mfaddr = util.normalize_email(mfaddr)
        logging.info("addmusf " + digacc["email"] + " searching for " + mfaddr)
        mfacct = dbacc.cfbk("DigAcc", "email", mfaddr)
        if not mfacct:
            return util.srverr(mfaddr + " not found", code=404)
        digacc = add_music_friend(digacc, mfacct)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([digacc], audience="private")


# emaddr, firstname used to create new account with auth digacc as friend.
def createmusf():
    try:
        digacc, _ = util.authenticate()
        emaddr = dbacc.reqarg("emaddr", "json", required=True)
        emaddr = util.normalize_email(emaddr)
        util.verify_new_email_valid(emaddr)  # not already used
        firstname = dbacc.reqarg("firstname", "string", required=True)
        mfacc = {"dsType":"DigAcc", "created":dbacc.nowISO(),
                 "email":"placeholder", "phash":"whatever",
                 "firstname":firstname}
        util.update_email_and_password(mfacc, emaddr,
                                       util.make_activation_code(),  #temp pwd
                                       friend=digacc)
        mfacc = dbacc.write_entity(mfacc)
        mfacc = add_music_friend(mfacc, digacc)
        digacc = add_music_friend(digacc, mfacc)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([digacc], audience="private")


# If uplds are given, save those and return them.  Otherwise walk the DigAcc
# music friends whose checksince is more than 24hrs ago and update default
# ratings for the DigAcc.  Fill in checksince for the music friend with the
# creation time of the most recent contributed song, or the current time if
# none found.  The dhcontrib count is incremented but not recalculated.
# Songs with contributed default ratings have
def mfcontrib():
    try:
        digacc, _ = util.authenticate()
        maxret = 200
        uplds = dbacc.reqarg("uplds", "jsarr")
        if uplds:
            logging.info("mfcontrib urs: " + uplds[0:512])
            uplds = json.loads(uplds)
            for song in uplds:
                unescape_song_fields(song)
            res = save_uploaded_songs(digacc, uplds, maxret)
        else:
            res = fill_default_ratings_from_friends(digacc, maxret)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(res, audience="private")


def mfclear():
    try:
        digacc, _ = util.authenticate()
        maxret = 200
        mfid = dbacc.reqarg("mfid", "dbid", required=True)
        res = clear_default_ratings_from_friend(digacc, mfid, maxret)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(res, audience="private")


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
        logging.info("impsptracks " + json.dumps(spi))
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
                rebuild_derived_song_fields(song)
                song = dbacc.write_entity(song)
            elif not song["spid"].startswith("z:"):
                song["spid"] = spid
            songs.append(song)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(songs)
