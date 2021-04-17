""" Sweep unmapped Songs to fill out spid """
#pylint: disable=wrong-import-position
#pylint: disable=wrong-import-order
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy
import py.mconf as mconf
import logging
import logging.handlers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(module)s %(asctime)s %(message)s',
    handlers=[logging.handlers.TimedRotatingFileHandler(
        mconf.logsdir + "plg_spidmapper.log", when='D', backupCount=10)])
import py.util as util
import py.dbacc as dbacc
import base64
import re
import requests
import urllib.parse     # to be able to use urllib.parse.quote
import string
import json
import sys


svcdef = util.get_connection_service("spotify")
svckey = svcdef["ckey"] + ":" + svcdef["csec"]
ainf = {"basic": base64.b64encode(svckey.encode("UTF-8")).decode("UTF-8"),
        "tok": ""}

def verify_token():
    if not ainf["tok"]:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": "Basic " + ainf["basic"]},
            data={"grant_type": "client_credentials"})
        # "expires_in": 3600 (1 hour)
        if resp.status_code != 200:
            raise ValueError("Token retrieval failed " + str(resp.status_code) +
                             ": " + resp.text)
        logging.info(resp.text)
        ainf["tok"] = resp.json()["access_token"]


def has_contained_punctuation(word):
    for c in word:
        if c in string.punctuation:
            return True
    return False


def prepare_query_term(value):
    words = value.split()  # trim/strip and split on whitespace
    for idx, word in enumerate(words):  # remove all surrounding punctuation
        words[idx] = word.strip(string.punctuation)
    # 15apr21 search will NOT match embedded ' or " even if encoded
    # remove any preceding or trailing words with contained punctuation
    while len(words) > 0 and has_contained_punctuation(words[0]):
        words = words[1:]
    while len(words) > 0 and has_contained_punctuation(words[len(words) - 1]):
        words = words[0:(len(words) - 1)]
    # If any of the middle words contain punctuation then they have to be
    # removed, which means a quoted match will fail due to the ordering.
    quotable = True
    filtered = [w for w in words if not has_contained_punctuation(w)]
    if len(filtered) != len(words):
        quotable = False
    value = urllib.parse.quote(" ".join(filtered))
    if quotable:
        value = "\"" + value + "\""
    return value


def make_query_string(ti, ar, ab):
    query = ""
    qfs = {"track":ti, "artist":ar, "album":ab}
    for key, value in qfs.items():
        if query:
            query += "%20"
        if value:
            query += key + ":" + prepare_query_term(value)
    query += "&type=track"
    logging.info("q=" + query)
    return query


def fetch_spid(query):
    resp = requests.get(
        "https://api.spotify.com/v1/search?q=" + query,
        headers={"Authorization": "Bearer " + ainf["tok"]})
    if resp.status_code != 200:
        raise ValueError("Search failed " + str(resp.status_code) +
                         ": " + resp.text)
    logging.info(resp.text)
    rob = resp.json()
    spid = ""
    items = rob["tracks"]["items"]
    if len(items) > 0:
        spid = items[0]["id"]
    return spid


# e.g. find_spid("I'm Every Woman", "Chaka Khan", "Epiphany - The Best Of Chaka Khan Vol 1")
def find_spid(ti, ar, ab):
    verify_token()
    skm = {"qtxt":make_query_string(ti, ar, ab), "qtype":"tiarab"}
    spid = fetch_spid(skm["qtxt"])
    # Common for an artist to release a track on more than one album, and
    # common for Spotify to only have one of them.
    if not spid:  # retry with just title and artist
        skm["qtxt"] = make_query_string(ti, ar, "")
        skm["qtype"] = "tiar"
        spid = fetch_spid(skm["qtxt"])
    if spid:  # found a mapping
        skm["spid"] = "z:" + spid
    else:   # nothing found at this time
        skm["qtype"] = "failed"
        skm["spid"] = "x:" + dbacc.nowISO()
    return skm


def map_song_spid(song, refetch=False, title="", artist=""):
    ti = song["ti"]
    ar = song.get("ar", "")
    ab = song.get("ab", "")
    logging.info(song["dsId"] + " " + ti + " - " + ar + " - " + ab)
    srx = re.compile(r"[\s\'\"]")
    skey = re.sub(srx, "", ti) + re.sub(srx, "", ar) + re.sub(srx, "", ab)
    skey = skey.lower()
    skmap = dbacc.cfbk("SKeyMap", "skey", skey)
    if not skmap:  # no mapping for key yet, make one
        refetch = True
        skmap = {"dsType":"SKeyMap", "modified":"", "skey":skey,
                 "notes":json.dumps({
                     "orgsong":{"dsId":song["dsId"],
                                "ti":ti, "ar":ar, "ab":ab}})}
    if refetch:  # new or specific request
        skm = find_spid(title or ti, artist or ar, ab)
        skmap["spid"] = skm["spid"]
        notes = json.loads(skmap["notes"])
        notes["spotify"] = {"qtxt":skm["qtxt"], "qtype":skm["qtype"]}
        skmap["notes"] = json.dumps(notes)
        skmap = dbacc.write_entity(skmap, vck=skmap["modified"])
        logging.info(skmap.notes)
    song["spid"] = skmap["spid"]
    song = dbacc.write_entity(song, vck=song["modified"])
    return song


# A previously failed mapping could succeed on retry at a later time.  To
# automate retry, the spid for a Song could be cleared if it starts with
# "x:" followed by a time older than 4 weeks.  Meanwhile the sweep process
# could remove or ignore any "x:" mappings older than 3 weeks.
def sweep_songs():
    songs = dbacc.query_entity("Song", "WHERE spid IS NULL LIMIT 50")
    for song in songs:
        updsong = map_song_spid(song)
        if not updsong["spid"].startswith("z"):
            logging.info("Song " + song["dsId"] + " not mapped, stopping.")
            break


def recheck_or_sweep():
    if len(sys.argv) > 1:
        song = dbacc.cfbk("Song", "dsId", sys.argv[1])
        ovrti = ""
        ovrar = ""
        if len(sys.argv) > 3:
            if sys.argv[2] == "title":
                ovrti = sys.argv[3]
            elif sys.argv[2] == "artist":
                ovrar = sys.argv[3]
        map_song_spid(song, refetch=True, title=ovrti, artist=ovrar)
    else:
        sweep_songs()


# run it
recheck_or_sweep()
