""" Songs and related data access processing. """
#pylint: disable=line-too-long
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy
#pylint: disable=too-many-lines
#pylint: disable=consider-using-from-import

import logging
import json
import datetime
import re
import urllib.parse
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
    ret = None
    where = ("WHERE aid = " + str(spec["aid"]) +
             " AND ti = \"" + dqe(spec["ti"]) + "\"" +
             " AND ar = \"" + dqe(spec["ar"]) + "\"" +
             " AND ab = \"" + dqe(spec["ab"]) + "\"" +
             # should never be more than one, but just in case...
             " ORDER BY modified DESC LIMIT 1")
    songs = dbacc.query_entity("Song", where)
    if len(songs) > 0:
        ret = songs[0]
    return ret


def verify_required_song_field_values(updsong, accid):
    """ Fill and strip field values, complain if required data missing. """
    updsong["dsType"] = "Song"
    updsong["aid"] = int(accid)
    for matchfield in ["ti", "ar", "ab"]:
        updsong[matchfield] = updsong.get(matchfield, "")
        updsong[matchfield] = updsong[matchfield].strip()
    for reqfield in ["ti", "ar"]:
        if not updsong.get(reqfield):
            raise ValueError("Missing " + reqfield + " value in update song")


def song_string(song):
    return song["ti"] + " - " + song.get("ar") + " - " + song.get("ab")


def is_unrated_song(song):  # matches deck.js isUnrated
    unrated = (not song["kws"]) and (song["el"] == 49) and (song["al"] == 49)
    return unrated


# Related situational notes:
# - If a client is started up on a new platform where the songs have not
#   been synced to the server yet, then they start playing what appears to
#   be an unrated song and they make changes to it, then hubsync pulls down
#   the previously saved song, their rating info will be replaced or merged
#   with the server info so it is not lost.  No version mismatch.
def choose_modified_value(updsong, dbsong):
    # If the client has changed ti/ar/ab values for a song, it may now be
    # mapped to a different existing database instance.  The modified value
    # for the previous instance is not useful.  updsong may not have dsId
    upid = str(updsong.get("dsId", "NoID"))
    dbid = str(dbsong["dsId"])
    if upid != dbid:
        retmod = dbsong.get("modified", "")
        logging.info("choose_modified_value remap " + upid + "-->" + dbid +
                     " modified: " + retmod)
        return retmod
    # The default mySQL isolation level of repeatable read means it is
    # possible to read an older instance from the database query cache
    # despite the instance having been updated and committed.  Use the
    # maximum available modified value since that is likely correct.
    updmod = updsong.get("modified", "")
    dbmod = dbsong.get("modified", "")
    if updmod > dbmod:
        return updmod
    return dbmod


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


# See related app deck.js simplifiedMatch used for dupe checking.
def standardized_colloquial_match(txt):
    scm = txt
    scm = re.sub(r"\(([^\)]*\d\d?)\)", r"[\1]", scm)
    scm = re.sub(r"\([^)]*\)\s*", "", scm)
    scm = re.sub(r"\[([^\]]*\d\d?)\]", r"(\1)", scm)
    scm = re.sub(r"\[[^\]]*\]", "", scm)
    scm = re.sub(r"\sfeaturing.*", "", scm, flags=re.IGNORECASE)
    scm = scm.strip()
    if not scm:
        logging.info("standardized_colloquial_match reduced to nothing: " + txt)
        scm = txt
    return scm


def rebuild_derived_song_fields(song):
    song["smti"] = standardized_colloquial_match(song["ti"])
    song["smar"] = standardized_colloquial_match(song["ar"])
    song["smab"] = standardized_colloquial_match(song["ab"])


def update_song_fields(updsong, dbsong):
    """ Update dbsong with field values from updsong """
    reset_dead_spid_if_metadata_changed(updsong, dbsong)
    flds = {  # do NOT copy general db fields from client data. only these:
        # see dbacc.py for field defs
        "path": {"pt": "string", "dv": ""},
        "ti": {"pt": "string", "dv": ""},
        "ar": {"pt": "string", "dv": ""},
        "ab": {"pt": "string", "dv": ""},
        "el": {"pt": "int", "dv": 0},
        "al": {"pt": "int", "dv": 0},
        "kws": {"pt": "string", "dv": ""},
        "rv": {"pt": "int", "dv": 0},
        "fq": {"pt": "string", "dv": ""},
        "lp": {"pt": "string", "dv": ""},
        "pd": {"pt": "string", "dv": ""},
        "nt": {"pt": "string", "dv": ""},
        "pc": {"pt": "int", "dv": 0},
        "srcid": {"pt": "string", "dv": ""},
        "srcrat": {"pt": "string", "dv": ""}}
    for field, fdesc in flds.items():
        dbsong[field] = updsong.get(field, fdesc["dv"])
    rebuild_derived_song_fields(dbsong)


# This function requires substantial database work.  There is one call to
# find the song, and another to insert or update it.  Calling this function
# in a loop risks bogging down the server.  Calling from a web API endpoint
# risks exceeding processing time/effort limits.
def write_upd_song(updsong, accid):
    """ Write the given updated song information. """
    verify_required_song_field_values(updsong, accid)
    # logging.info("appdat.write_upd_song " + str(updsong))
    dbsong = find_song(updsong)  # calls dbacc.query_entity
    if not dbsong:  # create new song shell to fill
        dbsong = {"dsType":"Song", "aid":int(accid), "modified":""}
    update_song_fields(updsong, dbsong)
    updsong = dbacc.write_entity(dbsong, dbsong.get("modified") or "")
    return updsong


def hubsync_authenticate(accid):
    hsct = dbacc.reqarg("hsct", "string")
    if not hsct:
        digacc, _ = util.authenticate()
        if not digacc:
            raise ValueError("hubsync_authenticate failure for " + str(accid))
        if str(digacc["dsId"]) != str(accid):
            raise ValueError("accid does not match authenticated digacc")
    xco = {"dsType":"XConvo", "xctype":"hubsync", "aid":int(accid), "xctok":""}
    where = "WHERE xctype=\"hubsync\" AND aid=" + str(accid)
    xcs = dbacc.query_entity("XConvo", where)
    if xcs:
        xco = xcs[0]
    if hsct and hsct != xco["xctok"]:
        raise ValueError("hubsync_authenticate hsct mismatch")
    # authenticated. update hsct and return the new value
    xco["xctok"] = util.make_activation_code()
    updxco = dbacc.write_entity(xco, xco.get("modified") or "")
    return updxco["xctok"]


# Avg size of a song 07jan25 is 630 bytes.  800k is possible to send, but is
# a noticeable transmission hit.  400k (650 songs) seems reasonable but was
# still flagged by PCRE ep15mar25.  If client is substantially outdated, it
# is more efficient for a client to restore from backup data ep22apr25.
HSMAXDOWN = 300
def find_hs_merge_songs(hsd, accid):
    where = ("WHERE aid = " + str(accid) +
             " AND lp > \"" + hsd["syncts"] + "\"" +
             " ORDER BY lp LIMIT " + str(HSMAXDOWN + 1))
    retsongs = dbacc.query_entity("Song", where)
    if retsongs: # have at least one song that needs to be merged
        hsd["provdat"] = "complete"
        if len(retsongs) > HSMAXDOWN:
            hsd["provdat"] = "partial"
            retsongs = retsongs[0:HSMAXDOWN]
        hsd["syncts"] = retsongs[len(retsongs) - 1]["lp"]
    return retsongs


def unWSRW(matchobj):  # Web Safe Reverse Word
    rval = matchobj.group(0)[4:]  # remove "WSRW"
    return rval[::-1]             # unreverse original mixed case value
def unescape_song_fields(song):
    # undo client svc.js txSong modifications
    for fld in ["path", "ti", "ar", "ab", "nt"]:
        if song.get(fld):
            song[fld] = song[fld].replace("ESCOPENPAREN", "(")
            song[fld] = song[fld].replace("ESCCLOSEPAREN", ")")
            song[fld] = song[fld].replace("ESCSINGLEQUOTE", "'")
            song[fld] = song[fld].replace("ESCAMPERSAND", "&")
            for rw in ["having", "select", "union", "within"]:
                song[fld] = re.sub(re.compile("WSRW" + rw[::-1], re.I),
                                   unWSRW, song[fld])
    return song


def strip_surrounding_quotes(txt):
    # Encoded txt will have any embedded double quotes as %22, file input
    # may have surrounding quotes, so protect just in case that happens.
    if txt.startswith("\"") and txt.endswith("\""):
        txt = txt[1:-1]  # remove surrounding quotes
    return txt
def ucsv(txt):  # unescape csv string value
    txt = urllib.parse.unquote(strip_surrounding_quotes(txt))
    return txt
def pciv(txt):
    return int(strip_surrounding_quotes(txt))
def csv2song(csv):
    # Skip first field value (dsId) as the song will be tiarab remapped and
    # the dsId may change if metadata has changed.  Value can be "" if the
    # song has not been saved to the hub before.
    cnvdefs = {"ti":ucsv, "ar":ucsv, "ab":ucsv,
               "el":pciv, "al":pciv, "kws":ucsv, "rv":pciv, "fq":ucsv,
               "nt":ucsv, "lp":ucsv, "pd":ucsv, "pc":pciv}
    vals = csv.split(",")[1:]
    song = {}
    for fld, cnvf in cnvdefs.items():
        val = vals.pop(0)
        song[fld] = cnvf(val)
    return song
def estr(val):
    return "\"" + urllib.parse.quote(str(val)) + "\""
def cint(val):
    return str(val)
def song2csv(song):
    cnvdefs = {"dsId":estr, "ti":estr, "ar":estr, "ab":estr,
               "el":cint, "al":cint, "kws":estr, "rv":cint, "fq":estr,
               "nt":estr, "lp":estr, "pd":estr, "pc":cint}
    cvals = []
    for fld, cnvf in cnvdefs.items():
        cvals.append(cnvf(song[fld]))
    return ",".join(cvals)


# Each uploaded song needs to be queried and updated, which is substantial
# database work.  Average length of a song is 3min15sec or roughly 20 songs
# per hour.  More than that in a single upload is unreasonable load.
HSMAXUP = 20
def upd_hs_upload_songs(hsd, accid, uplds):
    uplds = [csv2song(u) for u in uplds]
    uplds = [unescape_song_fields(s) for s in uplds]
    uplds = [s for s in uplds if not is_unrated_song(s)]
    uplds = uplds[0:HSMAXUP]
    retsongs = []
    for song in uplds:
        try:  # if any given song write fails, continue with rest
            retsongs.append(write_upd_song(song, accid))
        except ValueError as e:
            logpre = "upd_hs_uploaded_songs write_upd_song call failed: "
            logging.warning(logpre + str(e))
    hsd["action"] = "received"
    hsd["provdat"] = ""  # reset any previous value
    hsd["syncts"] = ""
    if retsongs:
        hsd["syncts"] = retsongs[len(retsongs) - 1]["lp"]
    return retsongs


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


# rv is no longer part of the default rating. More harmful than helpful.
rfdvs = {"el":49, "al":49, "kws":""}

def unset_rating_fields(song):
    for fld, val in rfdvs.items():
        song[fld] = val

def set_srcrat_from_rating_fields(song):
    song["srcrat"] = ":".join([str(song[v]) for v in rfdvs])

def set_rating_fields_from_source(digacc, song, source):
    for fld, val in rfdvs.items():
        song[fld] = source.get(fld, val)
    # restrict possibly offensive and/or junk keywords from being copied in
    # unless the recipient already has that keyword defined.
    allowkws = list(json.loads(digacc["kwdefs"]))
    givenkws = source["kws"].split(",")
    song["kws"] = ",".join([k for k in givenkws if k in allowkws])
    set_srcrat_from_rating_fields(song)

def ratings_changed_from_srcrat(song):
    rats = dict(zip(rfdvs.keys(), song["srcrat"].split(":")))
    for fld in rfdvs:
        if str(song[fld]) != rats[fld]:
            return True
    return False


# Factored method to set default values appropriately.
def copy_song(song, digacc):
    cs = {"dsType":"Song", "dsId":"", "created":"", "modified":"",
          "batchconv":"", "aid":digacc["dsId"], "path":song["path"],
          "ti":song["ti"], "ar":song["ar"], "ab":song["ab"],
          "fq":"N", "lp":"", "nt":"", "pc":0,
          "srcid":"", "srcrat":"", "spid":song.get("spid", "")}
    rebuild_derived_song_fields(song)
    unset_rating_fields(song)
    return cs


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
    song = {"path": path_for_spotify_track(track),
            "ti": track["name"],
            "ar": track["artists"][0]["name"],
            "ab": spotify_track_album(track),
            "spid": spid}
    song = copy_song(song, digacc)
    song["batchconv"] = "spidmap"
    song["fq"] = "P"  # playable since filling in lp
    song["lp"] = dbacc.timestamp(-1 * 60 * 24)  # yesterday
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


def note_song_recommendation(song, digacc):
    if song["aid"] == digacc["dsId"]:
        return  # can't recommend a song to yourself
    where = ("WHERE songid = " + song["dsId"] +
             " AND sfr = " + song["aid"] +
             " AND rfr = " + digacc["dsId"] +
             " ORDER BY created LIMIT 1")
    recs = dbacc.query_entity("SongRec", where)
    if len(recs) > 0:
        if recs[0]["modified"] >= dbacc.timestamp(-1 * 60 * 24):
            return  # only increment once per day, may have multiple calls
        rec = recs[0]
        rec["count"] += 1
    else:
        rec = {"dsType":"SongRec", "songid":song["dsId"],
               "sfr":song["aid"], "rfr":digacc["dsId"], "count":1,
               "modified":""}
    rec = dbacc.write_entity(rec, vck=rec["modified"])
    logging.info("DigAcc " + str(rec["sfr"]) + " recommended Song " +
                 str(song["dsId"]) + " (" + song["ti"] + ") to DigAcc " +
                 str(digacc["dsId"]) + " (" + digacc["firstname"] + ")")


def user_song_by_songid(digacc, songid):
    song = dbacc.cfbk("Song", "dsId", songid, required=True)
    if song["aid"] != digacc["dsId"]:
        note_song_recommendation(song, digacc)
        cs = copy_song(song, digacc)
        cs["srcid"] = song["aid"]
        set_rating_fields_from_source(digacc, cs, song)
        song = cs
    return song


def fetch_newest_songs(digacc, limit):
    where = ("WHERE aid = " + digacc["dsId"] +
             " AND spid LIKE \"z:%\"" +
             " AND (lp IS NULL OR (el = 49 AND al = 49 AND kws IS NULL))" +
             " ORDER BY created DESC LIMIT " + str(limit))
    logging.info("fetch_newest_songs " + where)
    songs = dbacc.query_entity("Song", where)
    return songs


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
    if fvs.get("ddst") == "newest":
        return fetch_newest_songs(digacc, limit)
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
    if fvs.get("startsongid"):
        songs.insert(0, user_song_by_songid(digacc, int(fvs["startsongid"])))
    return songs


def append_default_ratings_from_fan(digacc, mf, prcsongs, maxret):
    if len(prcsongs) >= maxret:
        return False # have enough songs already
    checksince = mf.get("checksince") or "1970-01-01T00:00:00Z"
    chkthresh = dbacc.ISO2dt(checksince) + datetime.timedelta(days=1)
    chkthresh = dbacc.dt2ISO(chkthresh)
    if chkthresh > dbacc.nowISO():
        return False # already checked today
    mf["obcontrib"] = 0  # reset in case no counts left
    obcs = dbacc.count_contributions(mf["dsId"], digacc["dsId"])
    if len(obcs) > 0:
        mf["obcontrib"] = obcs[0]["ccnt"]
    sflim = maxret - len(prcsongs)
    cds = dbacc.collaborate_default_ratings(digacc["dsId"], mf["dsId"],
                                            since=checksince, limit=sflim)
    if len(cds) > 0:
        for song in cds:
            mf["checksince"] = song["mfcreated"]
            mf["dhcontrib"] = mf.get("dhcontrib", 0) + 1
            song["srcid"] = song["mfid"]
            set_srcrat_from_rating_fields(song)
            # cds may contain duplicate songs due to join expansion. 14sep21
            # No need for overhead of querying for version before writing.
            prcsongs.append(dbacc.write_entity(song, vck="override"))
    else:
        mf["checksince"] = dbacc.nowISO()
    logging.info(mf.get("firstname") + " " + mf["dsId"] + " contributed " +
                 str(len(cds)) + " default ratings for " +
                 digacc.get("firstname") + " " + digacc["dsId"])
    return True


# For each fan rated song, if the srcrat is the same as the current
# settings, revert the song to unrated.  Clear srcid and srcrat.  Return a
# list of all updated Songs.
def clear_default_ratings_from_fan(digacc, mfid, maxret):
    where = ("WHERE aid=" + digacc["dsId"] + " AND srcid=" + mfid +
             " LIMIT " + str(maxret))
    songs = dbacc.query_entity("Song", where)
    logging.info("clearing " + str(len(songs)) + " default ratings from " +
                 mfid + " for " + digacc["dsId"])
    res = []
    for song in songs:
        if not ratings_changed_from_srcrat(song):
            unset_rating_fields(song)
        song["srcid"] = ""
        song["srcrat"] = ""
        res.append(dbacc.write_entity(song, song["modified"]))
    return res


# Fill unrated digacc songs with default song ratings from mfid.
def get_default_ratings_from_fan(digacc, mfid, maxret):
    sql = ("SELECT asg.dsId, fsg.kws, fsg.el, fsg.al" +
           " FROM Song AS asg, Song AS fsg" +
           " WHERE asg.aid = " + str(digacc["dsId"]) + " AND asg.kws IS NULL" +
           " AND asg.el = 49 AND asg.al = 49" +
           " AND fsg.aid = " + str(mfid) + " AND fsg.kws IS NOT NULL" +
           " AND fsg.el != 49 AND fsg.al != 49" +
           " AND asg.smti = fsg.smti AND asg.smar = fsg.smar" +
           " AND asg.smab = fsg.smab LIMIT " + str(maxret))
    drs = dbacc.custom_query(sql, ["dsId", "kws", "el", "al"])
    res = []
    for rat in drs:
        song = dbacc.cfbk("Song", "dsId", rat["dsId"], required=True)
        song["srcid"] = mfid
        set_rating_fields_from_source(digacc, song, rat)
        res.append(dbacc.write_entity(song, song["modified"]))
    logging.info(str(digacc["dsId"]) + " received " + str(len(res)) +
                 " default ratings from " + str(mfid))
    return res


# Calculate and update mf common and dfltsnd.  Do not recalc dfltrcv.
# mf.dfltrcv is the number of default ratings digacc has received from mf
# that digacc has not overridden with their own values.  Songs that digacc
# has changed the ratings for are now digacc rated, but mf still gets credit
# for having provided initial default values even if mf is no longer part of
# digacc's group.  They are counted in mf's dfltsnd.
def count_collaborations(digacc, mf):
    sql = ("SELECT COUNT(*) AS common FROM Song AS asg, Song AS fsg" +
           " WHERE asg.aid = " + str(digacc["dsId"]) +
           " AND fsg.aid = " + str(mf["dsId"]) +
           " AND asg.smti = fsg.smti AND asg.smar = fsg.smar" +
           " AND asg.smab = fsg.smab")
    drs = dbacc.custom_query(sql, ["common"])
    for row in drs:
        mf["common"] = row["common"]
    mf["lastcommon"] = dbacc.nowISO()
    sql = ("SELECT COUNT(*) AS dfltsnd FROM Song" +
           " WHERE aid = " + str(mf["dsId"]) +     # their songs
           " AND srcid = " + str(digacc["dsId"]))  # you provided default rating
    drs = dbacc.custom_query(sql, ["dfltsnd"])
    for row in drs:
        mf["dfltsnd"] = row["dfltsnd"]
    logging.info(str(digacc["dsId"]) + " has " + str(mf["common"]) +
                 " common with " + str(mf["dsId"]) +
                 ". dfltsnd: " + str(mf["dfltsnd"]))


def fetchcreate_song_from_fan(digacc, updsong):
    dsId = updsong["dsId"]
    logging.info("fetchcreate_song_from_fan updsong " + dsId)
    frsong = dbacc.cfbk("Song", "dsId", dsId[2:], required=True)
    dbsong = find_song({"aid":digacc["dsId"], "ti":updsong["ti"],
                        "ar":updsong["ar"], "ab":updsong["ab"]})
    if not dbsong:  # copy fan song data into new instance
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
        raise ValueError("Rating author id mismatch Song " +
                         str(updsong["dsId"]))
    dbsong = dbacc.cfbk("Song", "dsId", updsong["dsId"], required=True)
    update_song_fields(updsong, dbsong)
    if updsong.get("spid"):
        dbsong["spid"] = updsong["spid"]
    return dbsong


def acct2mf(digacc):
    mf = {"dsId": digacc["dsId"], "digname":digacc["digname"],
          "firstname": digacc["firstname"], "added":dbacc.nowISO(),
          "lastcommon":"", "lastpull":"", "lastheard":"",
          "common":0, "dfltrcv":0, "dfltsnd":0}
    return mf


# This might be improved, but whoever has listened to the most music in the
# past 6 monthis is not a bad person to meet.
def connect_me(digacc):
    now = datetime.datetime.utcnow()
    since = dbacc.dt2ISO(now - datetime.timedelta(days=180))
    sql = ("SELECT aid, count(dsId) AS scount FROM Song" +
           " WHERE modified >= \"" + since + "\"" +
           " AND aid != " + str(digacc["dsId"]) +
           " AND aid IN (SELECT dsId FROM DigAcc WHERE digname IS NOT NULL)" +
           " AND aid NOT IN" +
           " (SELECT dsId FROM DigAcc WHERE status = \"nongrata\")" +
           " GROUP BY aid ORDER BY scount DESC LIMIT 5")
    tls = dbacc.custom_query(sql, ["aid", "count"])
    logging.info("top listeners: " + json.dumps(tls))
    aids = [str(tl["aid"]) for tl in tls]
    where = ("WHERE dsId != " + str(digacc["dsId"]) +
             " AND dsId IN (" + (", ".join(aids)) + ")")
    fans = dbacc.query_entity("DigAcc", where)
    if not fans:
        raise ValueError("No listeners found")
    musfs = [acct2mf(fan) for fan in fans]
    return musfs


# idcsv is a prioritized list of music fan ids to query for recommendations.
# Returns at most 5 recommendations.  Matching on smti/smar/smab may miss due to
# bad metadata, resulting in a recommendation of a song the caller already has.
# The expectation is the caller will dismiss that recommendation and try again.
def make_song_recommendations(digacc, idcsv):
    logging.info("make_song_recommendations for " + digacc["dsId"] +
                 " from " + idcsv)
    recs = []
    for mfid in idcsv.split(","):
        sql = ("SELECT fsg.dsId, fsg.ti, fsg.ar, fsg.ab, fsg.nt" +
               " FROM Song AS fsg WHERE fsg.aid = " + mfid +
               " AND fsg.rv >= 8 AND NOT EXISTS (SELECT dsId FROM DigMsg" +
               " WHERE msgtype = 'recommendation' AND songid = fsg.dsId)" +
               " AND NOT EXISTS (SELECT dsId FROM Song AS osg" +
               " WHERE osg.aid = " + digacc["dsId"] +
               " AND fsg.smti = osg.smti AND fsg.smar = osg.smar" +
               " AND fsg.smab = osg.smab)" +
               " ORDER BY fsg.rv DESC, fsg.lp DESC LIMIT 1")
        # logging.info("msr sql: " + sql)
        sidrs = dbacc.custom_query(sql, ["dsId", "ti", "ar", "ab", "nt"])
        for row in sidrs:
            sug = {"dsType":"DigMsg", "modified":"", "sndr":int(mfid),
                   "rcvr":digacc["dsId"], "msgtype":"recommendation",
                   "status":"open", "songid":row["dsId"], "ti":row["ti"],
                   "ar":row["ar"], "ab":row["ar"], "nt":row["nt"]}
            recs.append(dbacc.write_entity(sug))
        # logging.info("len(recs): " + str(len(recs)));
        if len(recs) > 4:
            break
    return recs


# Send details about a recommendation or share.
def mail_digmsg_details(digacc, msgidstr):
    subj = "$SNDR $MSGT: $TI"
    body = """
You requested $SNDR $MSGT details be sent to you for the song

$TI
by $AR
off the album $AB

$COMMENT

Here are some prebuilt search links to help find the recording:

$LINKS

If you did not request this information, or if there is a problem with the content of this message, reply with any descriptive details you can so support can look into it.

"""
    dm = dbacc.cfbk("DigMsg", "dsId", msgidstr, required=True)
    sndr = dbacc.cfbk("DigAcc", "dsId", dm["sndr"], required=True)
    song = dbacc.cfbk("Song", "dsId", dm["songid"], required=True)
    links = [
        ("https://bandcamp.com/search?item_type&q=" +
         (urllib.parse.quote(dm["ti"] + " " + dm["ar"]).replace("%20", "%2B"))),
        ("https://www.amazon.com/s?k=" +
         (urllib.parse.quote(dm["ti"] + " " + dm["ar"]).replace("%20", "+"))),
        ("https://music.youtube.com/search?q=" +
         (urllib.parse.quote(dm["ti"] + " " + dm["ar"]).replace("%20", "+")))]
    if song.get("spid", "").startswith("z:"):
        links.append("https://open.spotify.com/track/" + song["spid"][2:])
    note = ""
    if song["nt"]:
        note = "Note from " + sndr["digname"] + ":\n" + song["nt"]
    repls = [["$SNDR", sndr["digname"]], ["$MSGT", dm["msgtype"]],
             ["$COMMENT", note], ["$TI", dm["ti"]], ["$AR", dm["ar"]],
             ["$AB", dm["ab"]], ["$LINKS", "\n\n".join(links)]]
    for repl in repls:
        body = body.replace(repl[0], repl[1])
        subj = subj.replace(repl[0], repl[1])
    util.send_mail(digacc["email"], subj, body)
    dm["procnote"] = "Mail message sent to " + digacc["email"]
    return dm


# Respond to received message.
def reply_to_digmsg(digacc, msgid, msgtype):
    mtypes = {"recresp": "Recommendation response",
              "recywel": "You're welcome",
              "shresp": "Share response"}
    srcmsg = dbacc.cfbk("DigMsg", "dsId", msgid, required=True)
    if srcmsg["status"] == "replied":
        logging.info("reply_to_digmsg " + str(msgid) + " already replied")
        return srcmsg
    too_many_messages = False
    if msgtype == "recresp":
        now = datetime.datetime.utcnow()
        time_window_start = dbacc.dt2ISO(now - datetime.timedelta(hours=24))
        where = ("WHERE msgtype = \"recresp\"" +
                 " AND sndr = " + str(digacc["dsId"]) +
                 " AND rcvr = " + str(srcmsg["sndr"]) +
                 " AND created > \"" + time_window_start + "\"")
        logging.info(where)
        prevmsgs = dbacc.query_entity("DigMsg", where)
        logging.info("reply_to_digmsg " + str(len(prevmsgs)) + " prev recresp")
        if len(prevmsgs) >= 2:
            too_many_messages = True
    if not too_many_messages:
        rspmsg = {"dsType":"DigMsg", "modified":"", "sndr":digacc["dsId"],
                  "rcvr":srcmsg["sndr"], "msgtype":msgtype, "status":"open",
                  "srcmsg":srcmsg["dsId"], "songid":srcmsg["songid"],
                  "ti":srcmsg["ti"], "ar":srcmsg["ar"], "ab":srcmsg["ab"],
                  "nt":""}
        logging.info("reply_to_digmsg sending " + msgtype)
        dbacc.write_entity(rspmsg)  # send response message
    srcmsg["status"] = "replied"
    srcmsg = dbacc.write_entity(srcmsg, srcmsg["modified"])
    rebuild_derived_song_fields(srcmsg)  # support client song matching
    srcmsg["procnote"] = mtypes.get(msgtype, "Reply") + " sent"
    return srcmsg


def broadcast_share_messages(digacc, song):
    shmsgs = []
    where = ("WHERE musfs LIKE \"%\\\"dsId\\\":\\\"" + str(digacc["dsId"]) +
             "\\\"%\"")
    listeners = dbacc.query_entity("DigAcc", where)
    for fan in listeners:
        # new msg instance even if previously shared, responses might differ.
        msg = {"dsType":"DigMsg", "modified":"", "sndr":digacc["dsId"],
               "rcvr":fan["dsId"], "msgtype":"share", "status":"open",
               "songid":song["dsId"], "ti":song["ti"], "ar":song["ar"],
               "ab":song["ab"], "nt":song["nt"]}
        shmsgs.append(dbacc.write_entity(msg))
    return shmsgs


def send_share_messages(digacc, idcsv):
    reactdays = 20  # must wait at least this many days before sharing again
    song = dbacc.cfbk("Song", "dsId", idcsv, required=True)
    rmsg = {"dsType":"DigMsg", "modified":"", "sndr":digacc["dsId"],
            "rcvr":"101", "msgtype":"share", "status":"open",
            "songid":song["dsId"], "ti":song["ti"], "ar":song["ar"],
            "ab":song["ab"], "nt":song["nt"]}
    where = ("WHERE msgtype = \"share\" AND sndr = " + str(digacc["dsId"]) +
             " AND rcvr = 101 AND songid = " + str(song["dsId"]))
    pms = dbacc.query_entity("DigMsg", where)
    if pms:
        rmsg = pms[0]
    now = datetime.datetime.utcnow()
    thresh = dbacc.dt2ISO(now - datetime.timedelta(days=reactdays))
    if not rmsg["modified"] or rmsg["modified"] < thresh:
        rmsg = dbacc.write_entity(rmsg, rmsg["modified"])
        broadcast_share_messages(digacc, song)
    return rmsg


############################################################
## API endpoints:

# Received syncdata is the DigAcc followed by zero or more updated Songs.
# See digger/docroot/docs/hubsyncNotes.txt
def hubsync(path="hubsync"):  # non-default path is "api/xx..."
    try:
        # raise ValueError("hubsync offline")
        if path == "hubsync":
            raise ValueError("account specific hubsync call required")
        accid = path[6:]
        # if accid == "2020":
        #     raise ValueError("hubsync disabled for DigAcc " + accid)
        startTime = datetime.datetime.now()
        hsct = hubsync_authenticate(accid)
        syncdata = json.loads(dbacc.reqarg("syncdata", "json", required=True))
        if not syncdata:
            raise ValueError("No syncdata received")
        hsd = json.loads(syncdata[0])  # hub sync directive: action etc
        hsd["hsct"] = hsct  # update communications token
        upsongs = syncdata[1:]  # uploaded songs if provided
        downsongs = []
        if hsd["action"] == "start":
            hsd["action"] = "started"
        elif hsd["action"] == "pull":
            downsongs = find_hs_merge_songs(hsd, accid)
            hsd["action"] = "merge"
        elif hsd["action"] == "upload":
            downsongs = upd_hs_upload_songs(hsd, accid, upsongs)
            hsd["action"] = "received"
        else:
            raise ValueError("Unknown hsd action: " + hsd["action"])
        # not necessary to web escape song field values on return
        downsongs = [song2csv(s) for s in downsongs]
        syncdata = [json.dumps(hsd)] + downsongs
        difft = round((datetime.datetime.now() - startTime).total_seconds(), 4)
        logging.info("hubsync " + accid + " " + hsd["action"] + " in " +
                     str(difft) + " seconds")
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(syncdata)


def songfetch():
    try:
        digacc, _ = util.authenticate()
        fvs = json.loads(dbacc.reqarg("fvs", "json", required=True))
        songs = fetch_matching_songs(digacc, fvs, 400)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(songs)


def savesongs():
    try:
        digacc, _ = util.authenticate()
        songs = json.loads(dbacc.reqarg("songs", "json", required=True))
        songs = songs[0:20]  # update at most 20 songs at a time. heavy work
        upds = []
        for idx, song in enumerate(songs):
            unescape_song_fields(song)
            dsId = song.get("dsId")
            if not dsId:  # assigned during hub sync
                raise ValueError("Missing dsId for " + song["ti"])
            logging.info("savesongs " + str(idx) + " Song " + str(dsId) +
                         " " + song["ti"])
            if dsId.startswith("fr"):  # song suggested from music fan
                song = fetchcreate_song_from_fan(digacc, song)
            elif dsId.startswith("spotify"):  # song direct play from Spotify
                song = fetchcreate_song_from_spid(digacc, song)
            else: # standard update from web player
                song = update_song_by_id(digacc, song)
            # always write song to reflect the modified time and any mod fields
            upds.append(dbacc.write_entity(song, song["modified"]))
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(upds)


def fangrpact():
    try:
        digacc, _ = util.authenticate()
        musfs = json.loads(digacc["musfs"] or "[]")
        musfs = [m for m in musfs if not m.get("email")]  # filter old data
        action = dbacc.reqarg("action", "string", required=True)
        digname = dbacc.reqarg("digname", "string")
        if action == "remove":
            if not digname:
                raise ValueError("Need digname to remove")
            musfs = [m for m in musfs if m["digname"] != digname]
        elif action == "add":
            if digname:
                mf = dbacc.cfbk("DigAcc", "digname", digname)
                if not mf:
                    raise ValueError(digname + " not found")
                musfs.insert(0, acct2mf(mf))
            else:
                if len(musfs) > 0:
                    raise ValueError("Already connected to other fans")
                musfs = connect_me(digacc)
        else:
            raise ValueError("Unknown action " + action)
        digacc["musfs"] = json.dumps(musfs)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([digacc], audience="private")


def fancollab():
    try:
        digacc, _ = util.authenticate()
        musfs = json.loads(digacc["musfs"] or "[]")
        mfid = dbacc.reqarg("mfid", "dbid", required=True)
        specfans = [fan for fan in musfs if fan["dsId"] == mfid]
        if not specfans:
            raise ValueError(str(mfid) + " not found in fan group.")
        fan = specfans[0]
        ctype = dbacc.reqarg("ctype", "string", required=True)
        maxret = 200
        if ctype == "clear":
            res = clear_default_ratings_from_fan(digacc, mfid, maxret)
            if len(res) < 200:  # no more default ratings to remove after this
                fan["dfltrcv"] = 0
            else: # decrement dfltrcv, floor at zero in case counts ever off
                fan["dfltrcv"] = max(fan["dfltrcv"] - len(res), 0)
        elif ctype == "get":
            res = get_default_ratings_from_fan(digacc, mfid, maxret)
            fan["dfltrcv"] += len(res)
            now = dbacc.nowISO()
            if res:  # have at least one default result
                fan["lastheard"] = now
            fan["lastpull"] = now
        elif ctype == "count":
            res = []
            count_collaborations(digacc, fan)
        digacc["musfs"] = json.dumps(musfs)
        # even though digacc was just retrieved above, it is still possible to
        # fail with an outdated version check due to mysql repeatable read.
        digacc = dbacc.write_entity(digacc, "override")
        res.insert(0, digacc)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(res, audience="private")


def fanmsg():
    try:
        digacc, _ = util.authenticate()
        action = dbacc.reqarg("action", "string", required=True)
        idcsv = dbacc.reqarg("idcsv", "string")
        msgs = []
        if action == "recommend":
            msgs = make_song_recommendations(digacc, idcsv)
        elif action == "dismiss":
            msg = dbacc.cfbk("DigMsg", "dsId", idcsv, required=True)
            msg["status"] = "dismissed"
            msgs.append(dbacc.write_entity(msg, msg["modified"]))
        elif action == "emdet":
            msgs.append(mail_digmsg_details(digacc, idcsv))
        elif action == "thxnrmv":
            msgs.append(reply_to_digmsg(digacc, idcsv, "recresp"))
        elif action == "welnrmv":
            msgs.append(reply_to_digmsg(digacc, idcsv, "recywel"))
        elif action == "rspnrmv":
            msgs.append(reply_to_digmsg(digacc, idcsv, "shresp"))
        elif action == "share":
            msgs.append(send_share_messages(digacc, idcsv))
        else:  # fetch
            where = ("WHERE rcvr = " + str(digacc["dsId"]) +
                     " AND status = 'open'" +
                     " ORDER BY modified DESC LIMIT 50")
            msgs = dbacc.query_entity("DigMsg", where)
        for msg in msgs:
            rebuild_derived_song_fields(msg)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(msgs)


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


# Auth required. Fetch the oldest hub songs to maybe transfer to device.
def suggdown():
    try:
        digacc, _ = util.authenticate()
        poskws = dbacc.reqarg("poskws", "string")
        negkws = dbacc.reqarg("negkws", "string")
        almin = dbacc.reqarg("almin", "string") or "0"
        almax = dbacc.reqarg("almax", "string") or "100"
        elmin = dbacc.reqarg("elmin", "string") or "0"
        elmax = dbacc.reqarg("elmax", "string") or "100"
        where = ("WHERE aid = " + str(digacc["dsId"]) +
                 " AND ab IS NOT NULL AND ab != \"\"")
        if poskws:
            for poskw in poskws.split(","):
                where += " AND find_in_set(\"" + poskw + "\", kws)"
        if negkws:
            for negkw in negkws.split(","):
                where += " AND NOT find_in_set(\"" + negkw + "\", kws)"
        where += (" AND al >= " + almin +
                  " AND al <= " + almax +
                  " AND el >= " + elmin +
                  " and el <= " + elmax +
                  " AND find_in_set(fq, \"N,P,B,Z,O\")" +
                  " AND lp IS NOT NULL" +
                  # avg 10-15 tracks per album, need 5+1 albums worth
                  " ORDER BY lp LIMIT 100")
        logging.info("suggdown query " + where)
        songs = dbacc.query_entity("Song", where)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(songs)


def stint_summary_counts(sitype):
    stcs = ["Pending", "Active", "Complete"]
    sql = "SELECT sitype"
    for stc in stcs:
        sql += (", COUNT(CASE status WHEN '" + stc + "'" +
                " then 1 else null end) AS " + stc.lower())
    sql += " FROM StInt WHERE sitype = \"" + sitype + "\""
    stcs = [stc.lower() for stc in stcs]
    stcs.insert(0, "sitype")
    return dbacc.custom_query(sql, stcs)


# Determining platform by path is no longer possible since path is not
# uploaded, but some platform information could be recorded in the path for
# future testing so leaving the code commented for now.  Not currently
# testing creation time since test started.
def platform_song_counts_for_tester(digacc):
    # plat = dbacc.reqarg("platform", "string", required=True)
    # pathexprs = {"iOS": r"//item/item\..*\?id=",
    #              "Android": r"^/?storage/.*/Music/"}
    # regex = pathexprs.get(plat)
    # if not regex:
    #     raise ValueError("No match for platform: " + plat)
    where = ("WHERE aid = " + str(digacc["dsId"]) +
             " AND (el != 49 OR al != 49 OR kws IS NOT NULL)" +
             # " AND path REGEXP \"" + regex + "\"" +
             " ORDER BY modified DESC LIMIT 100")
    return dbacc.query_entity("Song", where)


def update_stint_for_tester(digacc, sitype, action):
    stint = {"dsType":"StInt", "modified":"", "aid":digacc["dsId"],
             "email":digacc["email"], "status":"Pending",
             "sitype":sitype}
    where = ("WHERE aid = " + str(digacc["dsId"]) +
             " AND sitype = \"" + sitype + "\"")
    stints = dbacc.query_entity("StInt", where)
    if len(stints) > 0:
        stint = stints[0]
        if stint["status"] == "Complete":
            # do not do any further calculations or updates on this record
            return [stint]
    confcode = dbacc.reqarg("confcode", "string")
    if confcode:
        if confcode != stint["confcode"]:
            raise ValueError("confcode did not match")
        stint["email"] = digacc["email"]
        stint["stdat"] = "{\"activated\":\"" + dbacc.nowISO() + "\"}"
        stint["status"] = "Active"
    elif action == "sendInvite":
        stint["confcode"] = util.make_activation_code()
        subj = "Digger Beta Testing confirmation"
        body = ("Follow this link to confirm email communications" +
                " and start your beta testing!\n\n" +
                "https://diggerhub.com/beta" +
                "?an=" + digacc["email"] +
                "&at=" + util.token_for_user(digacc) +
                "&confcode=" + stint["confcode"])
        util.send_mail(digacc["email"], subj, body)
    elif action == "save":
        stdat = dbacc.reqarg("stdat", "json")
        logging.info("betastat save stdat: " + str(stdat))
        subj = "betastat save from " + digacc["email"]
        body = ("sitype: " + str(stint["sitype"]) + "\n" +
                "aid: " + str(stint["aid"]) + "\n" +
                "email: " + str(stint["email"]) + "\n" +
                "status: " + str(stint["status"]) + "\n" +
                "stdat: " + str(stint["stdat"]) + "\n")
        util.send_mail(None, subj, body)
        stint["stdat"] = stdat
    stint = dbacc.write_entity(stint, stint["modified"])
    return [stint]


def betastat():
    try:
        sitype = dbacc.reqarg("sitype", "string", required=True)
        action = dbacc.reqarg("action", "string")
        digacc = None
        emaddr = dbacc.reqarg("an", "DigAcc.email")
        if emaddr:
            digacc, _ = util.authenticate()
        if not digacc:  # GET of summary counts for sitype
            res = stint_summary_counts(sitype)
        elif action == "songCounts":
            res = platform_song_counts_for_tester(digacc)
        else:  # get stint for account and update as needed
            res = update_stint_for_tester(digacc, sitype, action)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(res, audience="private")


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


# General web streaming playback error recorder. Currently just deals with
# unavailable spids, factor out different types later.
def playerr():
    try:
        digacc, _ = util.authenticate()
        errt = dbacc.reqarg("type", "string", required=True)
        if errt != "spid":
            raise ValueError("Unknown playerr type " + errt)
        spid = dbacc.reqarg("spid", "string", required=True)
        error = dbacc.reqarg("type", "string", required=True)
        skmap = dbacc.cfbk("SKeyMap", "spid", spid, required=True)
        notes = json.loads(skmap["notes"])
        if not notes.get("playerr"):
            notes["playerr"] = {"first":dbacc.nowISO(),
                                "fuser":digacc["dsId"]}
        notes["playerr"]["latest"] = dbacc.nowISO()
        notes["playerr"]["lauser"] = digacc["dsId"]
        notes["playerr"]["errtxt"] = error
        skmap["notes"] = json.dumps(notes)
        skmap = dbacc.write_entity(skmap, vck=skmap["modified"])
        logging.info(skmap["notes"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([skmap])


# Note song recommendation and return the recommended song.
def songtip():
    try:
        digacc, _ = util.authenticate()
        songid = dbacc.reqarg("songid", "dbid", required=True)
        song = dbacc.cfbk("Song", "dsId", int(songid), required=True)
        if song["aid"] != digacc["dsId"]:
            note_song_recommendation(song, digacc)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([song])


# Fetch and return the N most recently modified bookmarks for the given
# accid, updated befiso or now, including the bmrkid bookmark if given,
# and matching the collstat value if given.  Page through on modified
# rather than created.  If you just bought something you noted years ago
# that's more important than when you first created a bookmark for it.
def bookmarks():
    try:
        accid = dbacc.reqarg("accid", "dbid", required=True)
        befiso = dbacc.reqarg("befiso", "string")
        if not befiso:
            befiso = dbacc.nowISO()
        collstat = dbacc.reqarg("collstat", "string")
        if collstat:
            collstat = " AND cs = \"" + collstat + "\""
        bmrkid = dbacc.reqarg("bmrkid", "dbid")
        if not bmrkid:
            bmrkid = 0
        where = ("WHERE aid = " + str(accid) +
                 " AND ((created < \"" + befiso + "\"" + collstat + ")" +
                 "       OR" +
                 "      (dsId = " + str(bmrkid) + "))" +
                 " ORDER BY created DESC LIMIT 300")
        bkms = dbacc.query_entity("Bookmark", where)
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(bkms)


# Create or update the given bookmark.
def updbmrk():
    try:
        digacc, _ = util.authenticate()
        artist = dbacc.reqarg("ar", "string", required=True)
        album = dbacc.reqarg("ab", "string", required=True)
        bmrk = {"dsType": "Bookmark", "aid": digacc["dsId"],
                "dsId": dbacc.reqarg("dsId", "dbid"),  # specified if update
                "modified":dbacc.reqarg("modified", "string"),
                "bmtype": dbacc.reqarg("bmtype", "string", required=True),
                "ar": artist, "ab": album,
                "smar": standardized_colloquial_match(artist),
                "smab": standardized_colloquial_match(album),
                "nt": dbacc.reqarg("nt", "text"),
                "url": dbacc.reqarg("url", "url", required=True),
                "upi": dbacc.reqarg("upi", "image"),
                "ai": dbacc.reqarg("ai", "json"),
                "ti": dbacc.reqarg("ti", "json"),
                "si": dbacc.reqarg("si", "json"),
                "sd": dbacc.reqarg("sd", "json"),
                "cs": dbacc.reqarg("cs", "string", required=True)}
        bmrk = dbacc.write_entity(bmrk, vck=bmrk["modified"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON([bmrk])


# Fetch the latest backup data for the account
def backdat(path):
    logging.info("backdat path: " + str(path))
    try:
        digacc, _ = util.authenticate()
        settings = json.loads(digacc.get("settings") or "{}")
        bdat = ""  # new account might not have a backup yet
        backup = settings.get("backup")
        if backup:
            burl = backup.get("url")
            if not burl or burl != path[4:]:  # path is "api/bd..."
                raise ValueError("Invalid backup data path")
            logging.info("backdat fetching data for " + str(digacc["dsId"]) +
                         json.dumps(backup))  # log the access
            path = util.runtime_home_dir() + backup.get("file")
            try:
                with open(path, "r", encoding="utf-8") as datfile:
                    bdat = datfile.read()
            except OSError as e:
                raise ValueError("Error reading file " + path) from e
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respond(bdat)
