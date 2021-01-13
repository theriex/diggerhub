""" Songs and related data access processing. """
#pylint: disable=line-too-long
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy

import logging
import json
import py.dbacc as dbacc
import py.util as util


def find_song(spec):
    """ Lookup by dsId or altkeys. Return None if no db inst. """
    if spec.get("dsId", ""):
        return dbacc.cfbk("Song", "dsId", spec["dsId"])
    # Lookup by aid/title/artist/album
    where = ("WHERE aid = " + spec["aid"] +
             " AND ti = \"" + spec["ti"] + "\"" +
             " AND ar = \"" + spec["ar"] + "\"" +
             " AND al = \"" + spec["ab"] + "\"" +
             # should never be more than one, but be resilient and optimized
             " ORDER BY modified DESC LIMIT 1")
    songs = dbacc.query_entity("Song", where)
    if len(songs) > 0:
        return songs[0]
    return None


def write_song(upds):
    """ Write the given update song. upds["aid"] required. """
    song = find_song(upds)
    if song:
        for field, fdesc in dbacc.entdefs["Song"].items():
            song[field] = upds.get(field, fdesc["dv"])
    else:
        song = upds
    return dbacc.write_entity(song, song.get("modified", ""))



############################################################
## API endpoints:

def uploadsongs():
    try:
        digacc, _ = util.authenticate()
        songs = json.loads(dbacc.reqarg("songs", "json", required=True))
        for idx, song in enumerate(songs):
            song["aid"] = digacc["dsId"]
            songs[idx] = write_song(song)
        logging.info("uploaded " + str(len(songs)) + " songs for " +
                     digacc["email"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(songs)


def downloadsongs():
    try:
        digacc, _ = util.authenticate()
        since = dbacc.reqarg("since", "string", required=True)
        where = ("WHERE aid = " + digacc["dsId"] +
                 " AND modified > \"" + since + "\"" +
                 # No LIMIT. They might need all their data for a new machine.
                 " ORDER BY modified DESC")
        result = dbacc.query_entity("Song", where)
        logging.info("downloading " + str(len(result)) + " songs for " +
                     digacc["email"])
    except ValueError as e:
        return util.serve_value_error(e)
    return util.respJSON(result)
