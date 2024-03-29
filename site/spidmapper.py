""" Sweep unmapped Songs to fill out spid """
#pylint: disable=wrong-import-position
#pylint: disable=wrong-import-order
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy
#pylint: disable=line-too-long
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
import json
import sys
from string import Template


svcdef = util.get_connection_service("spotify")
svckey = svcdef["ckey"] + ":" + svcdef["csec"]
ainf = {"basic": base64.b64encode(svckey.encode("UTF-8")).decode("UTF-8"),
        "tok": ""}
# Dashes (e.g. "B-52") match ok and are needed.  Quoting can't be escaped
# with backslashes and they don't match. ':" is used as a query key delimiter.
# Python string.punctuation: '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
probpunc = "\"'`:"
fluffpunc = "!#$%&()*+,./;<=>?@[\\]^`{|}"


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


def has_contained_probpunc(word):
    for c in word:
        if c in probpunc:
            return True
    return False


def prepare_query_term(value):
    words = value.split()  # trim/strip and split on whitespace
    for idx, word in enumerate(words):  # trim surrounding punctuation
        if word.endswith("'s"):
            word = word[0:-2]
        word = word.strip(probpunc + fluffpunc)
        words[idx] = word
    # 15apr21 search will NOT match embedded ' or " even if encoded, so
    # remove any preceding or trailing words with contained punctuation
    while len(words) > 0 and has_contained_probpunc(words[0]):
        words = words[1:]
    while len(words) > 0 and has_contained_probpunc(words[len(words) - 1]):
        words = words[0:(len(words) - 1)]
    # If any of the middle words contain punctuation then they have to be
    # removed, which means a quoted match will fail due to the ordering.
    quotable = True
    filtered = [w for w in words if not has_contained_probpunc(w)]
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


def query_spotify(query):
    resp = requests.get(
        "https://api.spotify.com/v1/search?q=" + query,
        headers={"Authorization": "Bearer " + ainf["tok"]})
    if resp.status_code != 200:
        raise ValueError("Search failed " + str(resp.status_code) +
                         ": " + resp.text)
    logging.info(resp.text)
    rob = resp.json()
    return rob


def fetch_spid(query):
    rob = query_spotify(query)
    spid = ""
    items = rob["tracks"]["items"]
    if len(items) > 0:
        spid = items[0]["id"]
    return spid


# Adjust known album name mismatches to what spotify wants.
def fix_album_name(album):
    sxps = [{"exp":r"Oumou\s+[\(\[]disk\s+1[\)\]]", "use":"Oumou"},
            {"exp":r"Swiss\sMovement\s.*",
             "use":"Swiss Movement (Montreux 30th Anniversary)"},
            {"exp":r"Astro[\-\s]Creep:\s2000.*",
             "use":"Astro Creep: 2000 Songs Of Love, Destruction And Other Synthetic Delusions Of The Electric Head"},
            {"exp":r"Like Stars In My Hands",
             "use":"Millions, Like Stars in My Hands, The Daggers in My Heart Wage War (Bonus Version)"},
            {"exp":r"Sandinista!.*", "use":"Sandinista! (Remastered)"}]
    for sxp in sxps:
        abfix = re.sub(sxp["exp"], sxp["use"], album, flags=re.I)
        if abfix != album:
            return abfix
    return album


def fix_artist_album_name(artist, album):
    sxps = [{"arx":"Oceania", "abx":"CD", "use":"Oceania"},
            {"arx":"The Doors", "abx":"American Prayer", "use":"An American Prayer"}]
    for sxp in sxps:
        if re.match(sxp["arx"], artist, flags=re.I):
            if re.match(sxp["abx"], album, flags=re.I):
                return sxp["use"]
    return album


# General compilations where the artist is "Various"
def unpack_general_compilation(ti, ar, ab):
    cxps = [{"abx":r"^God Save the Queen: 76-96.*", "spo":"arti", "sep":" / "},
            {"abx":r"Racer Radio, Vol 1", "spo":"arti", "sep":" / "},
            {"abx":r"Great 70's Dance Grooves", "spo":"arti", "sep":" / "},
            {"abx":r"The Breakfast Club", "spo":"arti", "sep":" / "},
            {"abx":r"Happy Anniversary.*Charlie Brown.*", "spo":"arti", "sep":" / "}]
    for cxp in cxps:
        if re.match(cxp["abx"], ab, flags=re.I):
            tes = ti.split(cxp["sep"])
            if len(tes) < 2:
                break  # separator not found, can't fix track.
            if cxp["spo"] == "arti":
                ar = tes[0]
                ti = tes[1]
            else:  # "tiar"
                ti = tes[0]
                ar = tes[1]
            break
    return ti, ar, ab


# General alterations to be done before attempting a match
def fix_known_bad_values(ti, ar, ab):
    ab = fix_album_name(ab)
    ab = fix_artist_album_name(ar, ab)
    ti, ar, ab = unpack_general_compilation(ti, ar, ab)
    return ti, ar, ab


def remove_contextual_title(title, album):
    cxps = [{"abx":r"Oumou", "tix":r"\(.*\)", "trt":""},
            {"abx":r"Paganini: 24 Caprices for Solo Violin, Op. 1",
             "tix":r"Paganini: Caprice #\d\d? In", "trt":"Caprice In"},
            {"abx":r"Paganini: 24 Caprices for Solo Violin, Op. 1",
             "tix":r"Op\.\s1/", "trt":"Op. 1, No. "},
            {"abx":r"Paganini: 24 Caprices for Solo Violin, Op. 1",
             "tix":r" - .*", "trt":""},
            {"abx":r"Storm The Studio", "tix":r"\(Part", "trt":"(Pt"},
            {"abx":r"Astro[\-\s]Creep:\s2000.*", "tix":r"Pt\.\s", "trt":"Part "},
            {"abx":r"Guilty 'Til Proved Innocent!", "tix":r"\[Hidden Track\] \[Live\]", "trt":""},
            {"abx":r"Twitch", "tix":r"^Ministry", "trt":""}]
    for cxp in cxps:
        if re.match(cxp["abx"], album, flags=re.I):
            title = re.sub(cxp["tix"], cxp["trt"], title, flags=re.I)
    return title


# safe to remove these if no match was found
def remove_general_suffix(title):
    rxs = [r"\s*[\(\[]\d{4}\s+Digital\s+Remaster.*[\)\]]",
           r"\s*[\(\[]\d{4}\s+Remastered\s+Version.*[\)\]]",
           r"\s*[\(\[]Remastered\s+Version.*[\)\]]",
           r"\s*[\(\[]Remastered\s+LP\s+Version.*[\)\]]",
           r"\s*[\(\[]Remixed\s+Album\s+Version.*[\)\]]",
           r"\s*[\(\[]Remixed\s+And\s+.*[\)\]]",
           r"\s*[\(\[]Explicit[\)\]]",
           r"\s[\(\[]\d\d?\-\d\d?\-\d\d[\)\]]$",  # recording date
           r"^\d\d?\s",  # title starts with track number
           r"\.mp3$",
           r"\S\s(re)?mix",  # whoever "mix" or "remix", just match on whoever.
           r"\s*[\(\[]Featuring\s+.*[\)\]]"]
    for rx in rxs:
        title = re.sub(rx, "", title, flags=re.I)
    return title


# Suffixes that can be removed from the title if no match was found.
def remove_ignorable_suffix(title, album):
    tifix = remove_contextual_title(title, album)
    if tifix != title:
        return tifix
    return remove_general_suffix(title)


# reduce artist name if initial match fails.  Also used for name corrections.
def reduce_collaborative_name(artist):
    # Sarah Vaughan With Her Trio is not the same as with her orchestra.
    sxps = [{"exp":r"Prince\s+(&|And)\s+The+\s+Revolution", "use":"Prince"},
            {"exp":r"Patti\s+Smith\s+Group", "use":"Patti Smith"},
            {"exp":r"Patti\s+La\s+Belle", "use":"Patti LaBelle"},
            {"exp":r"Oceania", "use":"Jaz Coleman"},  # very ugly
            {"exp":r"^OMD$", "use":"Orchestral Manoeuvres In The Dark"},
            {"exp":r"Midori", "use":"Niccolò Paganini"},  # absurd
            {"exp":r"Les McCann & Eddie Harris", "use":"Les McCann"},
            {"exp":r"Curtis Mayfield & The Impressions",
             "use":"Curtis Mayfield"},
            {"exp":r"Amy X Newburg", "use":"Amy X Neuburg"},
            {"exp":r"ClockDVA", "use":"Clock DVA"},
            {"exp":r"Miles Davis Sextet", "use":"Miles Davis"},
            {"exp":r"Time Zone featuring .*", "use":"Time Zone"},
            {"exp":r"Mickey Hart, Zakir Hussain, Sikiru Adepoju, .*",
             "use":"Sikiru Adepoju"},
            {"exp":r"Jello Biafra With Nomeansno", "use":"Jello Biafra"},
            {"exp":r"Ian Dury & The Blockheads", "use":"Ian Dury"},
            {"exp":r"Stevie Ray Vaughan & Double Trouble",
             "use":"Stevie Ray Vaughan"},
            {"exp":r"Hassan Hakmoun And Zahar", "use":"Hassan Hakmoun"},
            {"exp":r"Robert Fripp and Brian Eno", "use":"Robert Fripp"},
            {"exp":r"Band of Gypsys", "use":"Jimi Hendrix"},
            {"exp":r"Gary Clail and On-U Sound System", "use":"Gary Clail"},
            {"exp":r"Gary Clail & On-U Sound System", "use":"Gary Clail"},
            {"exp":r"Thelonius Monk with John Coltrane",
             "use":"Thelonious Monk"},
            {"exp":r"The Royal Macademians", "use":"The Royal Macadamians"},
            {"exp":r"Elizabeth Daily", "use":"E.G. Daily"},
            {"exp":r"Jerome Patrick Holan/Chuck Berry", "use":"Chuck Berry"},
            {"exp":r"Cure, The", "use":"The Cure"},
            {"exp":r"Jesse Johnson & Stephanie Spruill", "use":"Jesse Johnson"},
            {"exp":r"Screaming Jay Hawkins", "use":"Screamin' Jay Hawkins"},
            {"exp":r"Robert Fripp featuring.*", "use":"Robert Fripp"},
            {"exp":r"M.I.A.\sfeat.*", "use":"M.I.A."},
            {"exp":r"Geri Allen\s.*", "use":"Geri Allen"},
            {"exp":"Gus Gus", "use":"GusGus"},
            {"exp":"くるり", "use":"Quruli"},
            {"exp":"Hassan Hakmoun.*Zahar", "use":"Hassan Hakmoun"},
            {"exp":"The Doors", "use":"Jim Morrison"}]
    for sxp in sxps:
        artfix = re.sub(sxp["exp"], sxp["use"], artist, flags=re.I)
        if artfix != artist:
            return artfix
    return artist


def is_reasonable_query_text(qtxt):
    mob = re.match(r"track:(.*?)(?=%20artist:)%20artist:(.*)", qtxt)
    title = mob.group(1)
    artist = mob.group(2).split("%20album:")[0]
    for val in [title, artist]:
        if not val.lower().strip("\"").strip("the"):
            return False
    return True


def push_skm_try(phase, skm):
    skm["tries"] = skm.get("tries", [])
    skm["tries"].append({"phase":phase, "qtxt":skm["qtxt"],
                         "qtype":skm["qtype"]})


# e.g. find_spid("I'm Every Woman", "Chaka Khan", "Epiphany - The Best Of Chaka Khan Vol 1")
def find_spid(ti, ar, ab):
    ti, ar, ab = fix_known_bad_values(ti, ar, ab)
    skm = {"qtxt":make_query_string(ti, ar, ab), "qtype":"tiarab"}
    if not is_reasonable_query_text(skm["qtxt"]):
        skm["qtype"] = "badquery"
        skm["spid"] = "q:" + dbacc.nowISO()
        return skm
    verify_token()
    push_skm_try("original", skm)
    spid = fetch_spid(skm["qtxt"])
    # ti: "whatever song (2015 Digital Remaster) is not how Spotify lists it.
    if not spid:  # check for ignorable title suffix
        tifix = remove_ignorable_suffix(ti, ab)
        if tifix != ti:  # retry without ignorable suffix
            ti = tifix
            skm["qtxt"] = make_query_string(ti, ar, ab)
            skm["qtype"] = "tiarab"
            push_skm_try("remove_ignorable_suffix", skm)
            spid = fetch_spid(skm["qtxt"])
    # Spotify reduces collaborative names to individual artists
    if not spid:  # check if known collaborative name
        artfix = reduce_collaborative_name(ar)
        if artfix != ar:  # retry with individual name
            ar = artfix
            skm["qtxt"] = make_query_string(ti, ar, ab)
            skm["qtype"] = "tiarab"
            push_skm_try("reduce_collaborative_name", skm)
            spid = fetch_spid(skm["qtxt"])
    # Common for an artist to release a track on more than one album, and
    # equally common for Spotify to only carry one of them, so generalize.
    if not spid:  # retry with just title and artist
        skm["qtxt"] = make_query_string(ti, ar, "")
        skm["qtype"] = "tiar"
        push_skm_try("just_title_artist", skm)
        spid = fetch_spid(skm["qtxt"])
    # Pretenders, KLF, Buzzcocks etc have inconsistent metadata "The" naming
    if not spid:  # retry with alternate "The" prefix
        if ar.lower().startswith("the "):
            ar = ar[4:]
        else:
            ar = "The " + ar
        skm["qtxt"] = make_query_string(ti, ar, "")
        skm["qtype"] = "tiar"
        push_skm_try("swapped_the_prefix", skm)
        spid = fetch_spid(skm["qtxt"])
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
    if not ar or ar == "Unknown":
        return True
    return False


def get_song_key_map(song):
    ti = song["ti"]
    ar = song.get("ar", "")
    ab = song.get("ab", "")
    logging.info(song["dsId"] + " " + ti + " - " + ar + " - " + ab)
    skey = dbacc.get_song_key(song)
    skmap = dbacc.cfbk("SKeyMap", "skey", skey)
    if not skmap:  # no mapping for key yet, make one
        skmap = {"dsType":"SKeyMap", "modified":"", "skey":skey}
    if not skmap.get("notes"):
        skmap["notes"] = json.dumps({
            "orgsong":{"dsId":song["dsId"], "ti":ti, "ar":ar, "ab":ab}})
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


def is_known_unavailable_artist_work(song):
    artists = [r"Toshinori Kondo.*IMA",
               "The Miceteeth"]
    art = song["ar"]
    arm = [a for a in artists if re.match(a, art, flags=re.I)]
    if arm and len(arm) > 0:
        logging.info("known unavail arm: " + str(arm))
        return True
    albums = [r"Deep In The Heart Of Tuva.*Cowboy Music From The Wild East",
              r"Requiem For The Americas.*Songs From The Lost World",
              r"The Wired CD.*"]
    abm = [a for a in albums if re.match(a, song["ab"], flags=re.I)]
    if abm and len(abm) > 0:
        logging.info("known unavail abm: " + str(abm))
        return True
    # If a song was available on a different album, that should have already
    # been remapped.  This is for when all songs on the entire album are
    # generally unavailable.
    artalbs = {"Think Tree": ["Like The Idea"],
               "The Zulus": ["Down on the Floor"],
               "Thievery Corporation": ["Abductions and Reconstructions"],
               "The Mighty Lemon Drops": ["World Without End"],
               "Talvin Singh": ["Anokha"],
               "Stone Fox": ["Stone Fox"],  # The 90's San Francisco band
               "Scientist": ["Heavyweight Dub Champion"],
               "Keith Jarret.*": [r"Live, Hanover Germany.*"],
               "Ray Charles": [r"Genius.*Soul.*50.*Anniversary"],
               "Prach": [r"Dalama.*"],
               "Pizzicato Five": ["女性上位時代", r"singles.*",
                                  r".*Big Hits and Jet Lags*"],
               "No Man": ["Whammon Express"],
               "Arthur Loves Plastic": ["The Zero State"],
               "Jon Hassel": [r"The Surgeon of the Nightsky.*"],
               "小沢健二": [r"Ecology Of Everyday Life.*", "Eclectic"],
               "Ini Kamoze": ["Lyrical Gangsta"],
               "Curve": ["Doppelgänger"],
               "Birdsongs Of The Mesozoic": ["Sonic Geology"],
               "Franco Battiato": ["Shadow, Light"],
               "King Tubby": [r"Meets Scientist In A World Of.*"],
               "Omoide Hatoba": ["Mantako"],
               "World's End Girlfriend": ["Xmas Song"],
               "Mussolini Headkick": ["Blood on the Flag"],
               "Huun Huur Tu": ["60 Horses in My Herd"]}
    albums = [v for k, v in artalbs.items() if re.match(k, art, flags=re.I)]
    if not albums or len(albums) < 1:
        return False
    albums = albums[0]
    mabs = [a for a in albums if re.match(a, song["ab"], flags=re.I)]
    if len(mabs) > 0:
        logging.info("known unavail mabs: " + str(mabs))
        return True
    return False


def manual_verification_needed(song):
    if song["spid"].startswith("z"):  # mapped
        return False
    if song["spid"].startswith("m"):  # bad metadata
        return False
    if song["spid"].startswith("k"):  # known unmappable
        return False
    if is_known_unavailable_artist_work(song):
        return False
    return True  # spid set to x:timestamp or u:timestamp


def notice_body(song):
    return Template("""spidmapper was unable to map Song $dsId
    ti: $ti
    ar: $ar
    ab: $ab
If the equivalent can be found on Spotify, remap manually e.g.
python spidmapper.py $dsId spid <spotify track id>

Alternatively, specify "title" or "artist" instead of "spid".
Add a general mapping rule if that makes sense.

You can test automated lookup using:
python spidmapper.py lookup "$ti" "$ar" "$ab"

If not remapped, subsequent lookups will assume the track is unavailable.
""").substitute(song)


# Attempt to map all songs with no spid value.  Send an email message if
# running in batch and manual intervention needed.
# A previously failed mapping could succeed on retry at a later time.  To
# automate retry, the spid for a Song could be cleared if it starts with
# "x:" followed by a time older than 4 weeks.  Meanwhile the sweep process
# could remove or ignore any "x:" mappings older than 3 weeks.
def sweep_songs(batch=False):
    songs = dbacc.query_entity("Song", "WHERE spid IS NULL LIMIT 50")
    count = 0
    for song in songs:
        updsong = map_song_spid(song)
        if manual_verification_needed(updsong):
            logging.info("Song " + song["dsId"] + " not mapped, stopping.")
            if batch:
                util.send_mail(None, "spidmapper sweep", notice_body(updsong),
                               domain="diggerhub.com")
            break
        count += 1
    if batch:
        logging.info("batch processing completed. " + str(count) + " songs.")


def interactive_lookup(title, artist, album):
    print("title: " + title)
    print("artist: " + artist)
    print("album: " + album)
    if is_known_unavailable_artist_work({"ar":artist, "ti":title, "ab":album}):
        print("Known unavailable")
    else:
        print(json.dumps(find_spid(title, artist, album)))


def raw_qtxt_lookup(qtxt):
    verify_token()
    rob = query_spotify(qtxt)
    print(json.dumps(rob))
    items = rob["tracks"]["items"]
    if len(items) > 0:
        print("found spid: " + items[0]["id"])


def recheck_or_sweep():
    if len(sys.argv) > 1:
        if sys.argv[1] == "batch":
            sweep_songs(batch=True)
            return
        if sys.argv[1] == "lookup":
            interactive_lookup(sys.argv[2], sys.argv[3], sys.argv[4])
            return
        if sys.argv[1] == "qtxt":
            raw_qtxt_lookup(sys.argv[2])
            return
        song = dbacc.cfbk("Song", "dsId", sys.argv[1], required=True)
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
        sweep_songs()  # default is interactive sweep (no email)


# run it
recheck_or_sweep()
