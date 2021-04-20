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
    # 15apr21 search will NOT match embedded ' or " even if encoded, so
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


# Adjust known album name mismatches to what spotify wants.
def fix_album_name(album):
    sxps = [{"exp":r"Oumou\s+[\(\[]disk\s+1[\)\]]", "use":"Oumou"}]
    for sxp in sxps:
        abfix = re.sub(sxp["exp"], sxp["use"], album, flags=re.I)
        if abfix != album:
            return abfix
    return album


def remove_contextual_title_suffix(title, album):
    cxps = [{"abx":r"Oumou", "tix":r"\(.*\)", "trt":""},
            {"abx":r"Paganini: 24 Caprices for Solo Violin, Op. 1",
             "tix":r"Paganini: Caprice #\d\d? In", "trt":"Caprice In"},
            {"abx":r"Paganini: 24 Caprices for Solo Violin, Op. 1",
             "tix":r"Op\.\s1/", "trt":"Op. 1, No. "},
            {"abx":r"Paganini: 24 Caprices for Solo Violin, Op. 1",
             "tix":r" - .*", "trt":""}]
    for cxp in cxps:
        if re.match(cxp["abx"], album, flags=re.I):
            title = re.sub(cxp["tix"], cxp["trt"], title, flags=re.I)
    return title


def remove_general_suffix(title):
    rxs = [r"\s*[\(\[]\d{4}\s+Digital\s+Remaster.*[\)\]]",
           r"\s*[\(\[]Remastered\s+Version.*[\)\]]",
           r"\s*[\(\[]Explicit[\)\]]"]
    for rx in rxs:
        tifix = re.sub(rx, "", title, flags=re.I)
        if tifix != title:
            return tifix
    return title


# Suffixes that can be removed from the title if no match was found.
def remove_ignorable_suffix(title, album):
    tifix = remove_contextual_title_suffix(title, album)
    if tifix != title:
        return tifix
    return remove_general_suffix(title)


def reduce_collaborative_name(artist):
    # Sarah Vaughan With Her Trio is not the same as with her orchestra.
    sxps = [{"exp":r"Prince\s+(&|And)\s+The+\s+Revolution", "use":"Prince"},
            {"exp":r"Patti\s+Smith\s+Group", "use":"Patti Smith"},
            {"exp":r"Patti\s+La\s+Belle", "use":"Patti LaBelle"},
            {"exp":r"Oceania", "use":"Jaz Coleman"},  # very ugly
            {"exp":r"^OMD$", "use":"Orchestral Manoeuvres In The Dark"},
            {"exp":r"Midori", "use":"Niccolò Paganini"}]  # absurd
    for sxp in sxps:
        artfix = re.sub(sxp["exp"], sxp["use"], artist, flags=re.I)
        if artfix != artist:
            return artfix
    return artist


# e.g. find_spid("I'm Every Woman", "Chaka Khan", "Epiphany - The Best Of Chaka Khan Vol 1")
def find_spid(ti, ar, ab):
    verify_token()
    ab = fix_album_name(ab)
    skm = {"qtxt":make_query_string(ti, ar, ab), "qtype":"tiarab"}
    spid = fetch_spid(skm["qtxt"])
    # ti: "whatever song (2015 Digital Remaster) is not how Spotify lists it.
    if not spid:  # check for ignorable title suffix
        tifix = remove_ignorable_suffix(ti, ab)
        if tifix != ti:  # retry without ignorable suffix
            ti = tifix
            skm = {"qtxt":make_query_string(ti, ar, ab), "qtype":"tiarab"}
            spid = fetch_spid(skm["qtxt"])
    # Spotify reduces collaborative names to individual artists
    if not spid:  # check if known collaborative name
        artfix = reduce_collaborative_name(ar)
        if artfix != ar:  # retry with individual name
            ar = artfix
            skm = {"qtxt":make_query_string(ti, ar, ab), "qtype":"tiarab"}
            spid = fetch_spid(skm["qtxt"])
    # Common for an artist to release a track on more than one album, and
    # equally common for Spotify to only carry one of them, so generalize.
    if not spid:  # retry with just title and artist
        skm["qtxt"] = make_query_string(ti, ar, "")
        skm["qtype"] = "tiar"
        spid = fetch_spid(skm["qtxt"])
    # Pretenders, KLF, Buzzcocks etc have inconsistent metadata "The" naming
    if not spid:  # retry with alternate "The" prefix
        if ar.lower().startswith("the "):
            ar = ar[4:]
        else:
            ar = "The " + ar
        skm["altq"] = make_query_string(ti, ar, "")
        spid = fetch_spid(skm["altq"])
    # Done with attempts, return found or not
    if spid:  # found a mapping
        skm["spid"] = "z:" + spid
    else:   # nothing found at this time
        skm["qtype"] = "failed"
        skm["spid"] = "x:" + dbacc.nowISO()
    return skm


def has_bad_metadata(song):
    # Could also check for placeholder title ending with ".mp3", or
    # containing multiple "/"s, but in those cases the artist is also
    # missing.  Realistically, if there is no artist, the chances of finding
    # a reasonable mapping to the appropriate track is basically zero.
    # Fixing bad metadata is a local storage issue, not a mapping issue.
    ar = song.get("ar", "")
    if not ar:
        return True
    return False


def get_song_key_map(song):
    ti = song["ti"]
    ar = song.get("ar", "")
    ab = song.get("ab", "")
    logging.info(song["dsId"] + " " + ti + " - " + ar + " - " + ab)
    srx = re.compile(r"[\s\'\"]")
    skey = re.sub(srx, "", ti) + re.sub(srx, "", ar) + re.sub(srx, "", ab)
    skey = skey.lower()
    skmap = dbacc.cfbk("SKeyMap", "skey", skey)
    if not skmap:  # no mapping for key yet, make one
        skmap = {"dsType":"SKeyMap", "modified":"", "skey":skey,
                 "notes":json.dumps({
                     "orgsong":{"dsId":song["dsId"],
                                "ti":ti, "ar":ar, "ab":ab}})}
    return skmap


def map_song_spid(song, refetch=False, title="", artist=""):
    if has_bad_metadata(song):
        song["spid"] = "m:" + dbacc.nowISO()
    else:
        skmap = get_song_key_map(song)
        if refetch or ("dsId" not in skmap):
            skm = find_spid(title or song["ti"],
                            artist or song.get("ar", ""),
                            song.get("ab", ""))
            skmap["spid"] = skm["spid"]
            notes = json.loads(skmap["notes"])
            notes["spotify"] = {"qtxt":skm["qtxt"], "qtype":skm["qtype"]}
            skmap["notes"] = json.dumps(notes)
            skmap = dbacc.write_entity(skmap, vck=skmap["modified"])
            logging.info(skmap["notes"])
            song["spid"] = skmap["spid"]
        else: # not refetch, so using existing lookup
            if skmap["spid"].startswith("x:"):
                # note this is a known failed lookup so sweep doesn't halt
                song["spid"] = "k:" + skmap["spid"][2:]
            else:
                song["spid"] = skmap["spid"]
    song = dbacc.write_entity(song, vck=song["modified"])
    return song


def explicitely_map(song, spid):
    if not spid.startswith("z:"):
        spid = "z:" + spid
    skmap = get_song_key_map(song)
    skmap["spid"] = spid
    notes = json.loads(skmap["notes"])
    notes["spotify"] = {"qtxt":"", "qtype":"hardmapped"}
    skmap["notes"] = json.dumps(notes)
    skmap = dbacc.write_entity(skmap, vck=skmap["modified"])
    logging.info(skmap["notes"])
    song["spid"] = skmap["spid"]
    song = dbacc.write_entity(song, vck=song["modified"])
    return song


def manual_verification_needed(song):
    if song["spid"].startswith("z"):  # mapped
        return False
    if song["spid"].startswith("m"):  # bad metadata
        return False
    if song["spid"].startswith("k"):  # known unmappable
        return False
    return True


# A previously failed mapping could succeed on retry at a later time.  To
# automate retry, the spid for a Song could be cleared if it starts with
# "x:" followed by a time older than 4 weeks.  Meanwhile the sweep process
# could remove or ignore any "x:" mappings older than 3 weeks.
def sweep_songs():
    songs = dbacc.query_entity("Song", "WHERE spid IS NULL LIMIT 50")
    for song in songs:
        updsong = map_song_spid(song)
        if manual_verification_needed(updsong):
            logging.info("Song " + song["dsId"] + " not mapped, stopping.")
            break


def interactive_lookup(title, artist, album):
    print("title: " + title)
    print("artist: " + artist)
    print("album: " + album)
    print(json.dumps(find_spid(title, artist, album)))


def recheck_or_sweep():
    if len(sys.argv) > 1:
        if sys.argv[1] == "lookup":
            interactive_lookup(sys.argv[2], sys.argv[3], sys.argv[4])
            return
        song = dbacc.cfbk("Song", "dsId", sys.argv[1])
        ovrti = ""
        ovrar = ""
        if len(sys.argv) > 3:
            if sys.argv[2] == "title":
                ovrti = sys.argv[3]
                if len(sys.argv) > 5:
                    if sys.argv[4] == "artist":
                        ovrar = sys.argv[5]
            elif sys.argv[2] == "artist":
                ovrar = sys.argv[3]
            elif sys.argv[2] == "spid":
                explicitely_map(song, sys.argv[3])
                return
        map_song_spid(song, refetch=True, title=ovrti, artist=ovrar)
    else:
        sweep_songs()


# run it
recheck_or_sweep()
