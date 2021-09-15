#pylint: disable=missing-module-docstring
#pylint: disable=import-error
#pylint: disable=wrong-import-position
#pylint: disable=missing-function-docstring

import sys
sys.path.append("..")
import py.dbacc as dbacc
import py.appdat as appdat

def fill_sm_fields_for_any_songs_where_smti_is_null():
    lim = 12000
    songs = dbacc.query_entity("Song", "WHERE smti IS NULL LIMIT " + str(lim))
    for song in songs:
        print(song["ti"] + " - " + song["ar"])
        appdat.rebuild_derived_song_fields(song)
        dbacc.write_entity(song, song["modified"])
    print("Processed " + str(len(songs)) + " Songs.")
    if len(songs) >= lim:
        print("Run again for more")

fill_sm_fields_for_any_songs_where_smti_is_null()
