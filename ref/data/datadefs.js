/*jslint node, white, fudge */

//Fields used for database search and retrieval must either be declared
//unique or listed within one or more queries.  Fields used only client side
//and fields not needed for search may be grouped into JSON as appropriate.

module.exports = (function () {
    "use strict";

    var fieldDescriptors = [
        {dn:"priv[ate]", h:"authorized access only e.g. owner personal info"},
        {dn:"adm[in]", h:"administrative access only e.g. activation codes"},
        {dn:"req[uired]", h:"Save error if null or empty"},
        {dn:"uniq[ue]", h:"Indexed. Save err if matches another's value"},
        {dn:"str[ing]", h:"Rough max 128 char text, truncation ok.", aliases:[
            {dn:"email", h:"email address format"},
            {dn:"isod[ate]", h:"ISO date format"},
            {dn:"isomod", h:"ISO date;int count"},
            {dn:"srchidcsv", h:"short string length idcsv, searchable"}]},
        {dn:"text", h:"unindexable max 1mb string.", aliases:[
            {dn:"json", h:"JSON encoded data. default '{}'"},
            {dn:"jsarr", h:"JSON encoded data. default '[]'"},
            {dn:"idcsv", h:"comma separated unique integer ids"},
            {dn:"isodcsv", h:"comma separated ISO date values"},
            {dn:"gencsv", h:"general comma separated values"},
            {dn:"url", h:"a URL, possibly longer than 128chars"}]},
        {dn:"image", h:"base64 encoded binary image data (max 1mb)"},
        {dn:"dbid", h:"long int db id translated to string for JSON"},
        {dn:"int", h:"low range integer value JavaScript can handle"}];
    var descrLookup = null;

    //All entities have the following fields automatically created:
    //  dsId: Large integer value unique within the entity type
    //  created: ISO UTC timestamp string when the instance was first saved
    //  modified: timestamp;version
    //  batchconv: string indicator for batch conversion processing
    //On retrieval, instances have dbType set to the entity name.
    var ddefs = [ //data storage entity definitions

    {entity:"DigAcc", descr:"Digger Hub access account", fields:[
        {f:"email", d:"priv req unique email", c:"username/contact" },
        {f:"phash", d:"adm req string", c:"Auth processing"},
        {f:"hubdat", d:"priv json", c:"OAuth and similar server side data"},
        {f:"status", d:"priv string", c:"Not currently used",
         enumvals:["Pending", "Active", "Inactive", "Unreachable"]},
        {f:"actsends", d:"adm gencsv", c:"latest first isod;emaddr vals"},
        {f:"actcode", d:"adm string", c:"account activation code"},
        {f:"firstname", d:"req string", c:"general display use"},
        {f:"digname", d:"unique string", c:"collaboration handle"},
        {f:"kwdefs", d:"json", c:"keyword definitions for this account (*1)"},
        {f:"igfolds", d:"json", c:"ignore folders used by this account"},
        {f:"settings", d:"json", c:"ctrl vals, general options (*2)"},
        {f:"musfs", d:"jsarr", c:"music fans in whatever sort order (*3)"}],
     //*1 kwdefs: At least 4 keyword definitions by keyword, each with
     //    pos: position of keyword in selection/filters
     //    sc: song count, how many songs have this keyword
     //    ig: ignore flag, hide this keyword from display even if used
     //    dsc: description of what the keyword means
     //*2 settings:
     //    waitcodedays: player.js mgrs.tun B/Z/O time overrides
     //    songcounts: fetched, posschg, totals
     //    xps: playlist exports by platform, then by playlist name
     //    spimport: counts of imported library tracks and when
     //    sumact: activity summary info sendon day, lastsend timestamp
     //*3 musfs: Music fan instances
     //    dsId: id of music fan
     //    digname: digname of music fan
     //    firstname: fan firstname
     //    added: timestamp when fan was added
     //    lastcommon: ISO timestamp of last common ratings check
     //    lastpull: ISO timestamp of last default rating pull check
     //    lastheard: max of latest msg received or latest default rating pulled
     //    common: count of songs you both have
     //    dfltrcv: count of default ratings provided from this fan
     //    dfltsnd: count of default ratings sent to this fan
     //  The common/dfltrcv/dfltsnd fields are computed once when the fan
     //  is added to the group.  Counts are updated when new songs are added
     //  to the collection.  Deleting and re-adding a fan to your group may
     //  result in different counts if ratings have changed.
     cache:{minutes:2*60}, //fast auth after initial load
     logflds:["email", "firstname"]},

    {entity:"Song", descr:"Rating and play information", fields:[
        {f:"aid", d:"req dbid", c:"the account this song info is from"},
        {f:"path", d:"text", c:"full file path from most recent update"},
        {f:"ti", d:"req string", c:"title of song"},
        {f:"ar", d:"string", c:"artist for song"},
        {f:"ab", d:"string", c:"album for song"},
        {f:"smti", d:"string", c:"standardized match title"},
        {f:"smar", d:"string", c:"standardized match artist"},
        {f:"smab", d:"string", c:"standardized match album"},
        {f:"el", d:"int", i:49, c:"energy level Chill/Amped 0-99"},
        {f:"al", d:"int", i:49, c:"approachability level Easy/Hard 0-99"},
        {f:"kws", d:"string", c:"keywords CSV associated with this song"},
        {f:"rv", d:"int", i:5, c:"rating value (stars) 1-10"},
        {f:"fq", d:"string", c:"play frequency code (see player)"},
        {f:"nt", d:"text", c:"note text (whatever the user wrote)"},
        {f:"lp", d:"isodate", c:"last played timestamp"},
        {f:"pd", d:"string", c:"last played disposition (*1)"},
        {f:"pc", d:"int", c:"how many times song was loaded into player"},
        {f:"mddn", d:"int", c:"metadata album disk number or zero"},
        {f:"mdtn", d:"int", c:"metadata album track number or zero"},
        {f:"srcid", d:"dbid", c:"music fan id or source id (*2)"},
        {f:"srcrat", d:"string", c:"src el:al:rv:kwscsv values"},
        {f:"spid", d:"string", c:"z:trackID, code:val or null/empty (*3)"}],
     //SHOW TABLE STATUS WHERE NAME="Song"\G
     //*1 pd: null or empty string if playback disposition unknown
     //         "played": normal interactive playback
     //         "iosqueue": queued background playback on iOS
     //         "digaudpl": queued background playback on Android
     //         "dupe": processed as a duplicate of the song that was played
     //         "snoozed": fq bumped and lp updated, pulled from deck.
     //         "skipped": hit the skip button when playback started
     //         "error ...": playback failed. May include error text
     //*2 srcid: null or zero if not music fan contributed.  Special ids:
     //         1: spotify playback (Digger reacted to song on spotify player)
     //*3 spid: null if not searched.
     //         "z:" + spotify track id - successfully mapped.
     //         "x:" + ISO time - no spotify mapping found.
     //         "m:" + ISO time - unmappable due to bad metadata.
     //         "q:" + ISO time - not queryable
     //         "k:" + ISO time - known unmappable (previously verified)
     //   bcid, ytid, azid, apid etc. will be additional fields when supported
     cache:{minutes:0},
     logflds:["aid", "ti", "ar"]},

    {entity:"Bookmark", descr:"A link to web music", fields:[
        {f:"aid", d:"req dbid", c:"the account whose bookmark this is"},
        {f:"bmt", d:"string", c:"bookmark type (*1)"},
        {f:"ar", d:"string", c:"artist name"},
        {f:"ab", d:"req string", c:"name of album (*2)"},
        {f:"smar", d:"string", c:"standardized match artist"},
        {f:"smab", d:"string", c:"standardized match album"},
        {f:"uti", d:"string", c:"url title, possibly autofilled from site"},
        {f:"nt", d:"text", c:"note text (whatever the user writes)"},
        {f:"url", d:"string", c:"public web source to listen (*3)"},
        {f:"upi", d:"image", c:"url link preview image"},
        {f:"haf", d:"string", c:"heard about from. optional friend/src name"},
        {f:"abi", d:"json", c:"album info like release year, label etc"},
        {f:"trk", d:"json", c:"track info, names and ordering"},
        {f:"si", d:"json", c:"song info, digger songs summary (*4)"},
        {f:"det", d:"json", c:"supporting details release year, label etc"},
        {f:"cs", d:"string", c:"collection status (*5)"}],
     //Informational fields might not have anything in them.
     //*1 bmt: bookmark type is Performance/Album/Song/Other
     //        "Other" encompasses Review, Documentary, Movie, Interview etc
     //*2  ab: Album name should match for all contained songs.  If bmtype
     //        "Song" this is the song title, if "Performance" then some kind
     //        of "live at" or whatever identification.
     //*3 url: Permalink limited to 128 char indexable string limit.  aid+url
     //        is an alternate key.
     //*4  si: song info on display request, may be old/missing.
     //*5  cs: most recent change day stamp kept in sd field
     //        "Pending" - Intending to listen to this later.
     //        "Listened" - Listened to it, see my comments if I bothered.
     //        "Notable" - Worth hearing, not considering owning.
     //        "Considering" - Might add this to my collection.
     //        "Collected" - Own this, might have associated song ratings.
     //        "Archived" - No longer in listening rotation.
     //        "Deleted" - Mark for deletion processing.
        cache:{minutes:0},
     logflds:["aid", "ab", "ar"]},

    {entity:"SKeyMap", descr:"Song Title/Artist/Album key mappings", fields:[
        {f:"skey", d:"req string unique", c:"Canonical ti/ar/ab text"},
        {f:"spid", d:"string", c:"same as Song.spid"},
        {f:"notes", d:"json", c:"optional data processing details"}],
     cache:{minutes:0},
     logflds:["skey", "spid"]},

    {entity:"DigMsg", descr:"Music communications between DigAccs", fields:[
        {f:"sndr", d:"req dbid", descr:"Originating DigAcc for this message"},
        {f:"rcvr", d:"req dbid", descr:"Receiving DigAcc for this message"},
        {f:"msgtype", d:"req string", descr:"Message type label"},
        {f:"status", d:"req string", descr:"open|dismissed|replied"},
        //procnote: runtime-only server processing message returned to client
        {f:"srcmsg", d:"dbid", descr:"Source message if reply msgtype"},
        {f:"songid", d:"dbid", descr:"dsId of source song for message"},
        {f:"ti", d:"req string", c:"title of source song"},
        {f:"ar", d:"string", c:"artist for source song"},
        {f:"ab", d:"string", c:"album for source song"},
        {f:"nt", d:"text", c:"note text from source song"}],
     //*1 msgtype: "share", "shresp", "recommendation", "recresp", "recywel"
     //*2 status: "open", "replied", "dismissed"
     cache:{minutes:0},
     logflds:["sndr", "msgtype", "rcvr", "songid", "ti"]},

    {entity:"SASum", descr:"Song activity summary, e.g. weekly top20", fields:[
        {f:"aid", d:"req dbid", c:"the account this summary is for"},
        {f:"digname", d:"string", c:"handle for lookup"},
        {f:"sumtype", d:"req string", descr:"Summary type label"},
        {f:"songs", d:"jsarr", descr:"Songs in this summary (*1)"},
        {f:"easiest", d:"json", descr:"Easiest song in time period"},
        {f:"hardest", d:"json", descr:"Hardest song in time period"},
        {f:"chillest", d:"json", descr:"Chillest song in time period"},
        {f:"ampest", d:"json", descr:"Ampest song in time period"},
        {f:"curate", d:"json", descr:"Curated selections from top 20 (*2)"},
        {f:"start", d:"isodate", descr:"Start timestamp for summary"},
        {f:"end", d:"isodate", descr:"End timestamp for summary"},
        {f:"ttlsongs", d:"int", descr:"Count of songs considered for summary"}],
     //*1 songs: Immutable copies of songs at the time the summary was written.
     //*2 curate: User modifiable overlay information about songs.
     //    inits: ISO when curation was first started.
     //    rovrs: Recommendations song overlay array, songs array decorator
     //      recommended: ISO when checkbox selected, or "" if not selected
     //      text: How&why from song.nt
     cache:{minutes:30},  //relatively small records, mostly read-only
     logflds:["aid", "sumtype", "start", "end", "ttlsongs"]},

    {entity:"SAResp", descr:"Song activity response", fields:[
        {f:"aid", d:"req dbid", c:"the responding account"},
        {f:"sasid", d:"req dbid", c:"SASum this response is for"},
        {f:"acts", d:"jsarr", descr:"song collection responses (*1)"},
        {f:"rebchk", d:"isodate", descr:"when response last rebuilt"}],
     //*1 acts: response interactions from collection and bookmarks
     //    recid: recommended song id (dsId of song from recommender)
     //    sngid: responder corresponding song id or ""
     //    bmkid: responder corresponding bookmark id or ""
     //    updts: ISO when last changed
     cache:{minutes:30},  //single user update
     logflds:["aid", "sasid"]},

    {entity:"XConvo", descr:"Extended conversation e.g. hubsync", fields:[
        {f:"xctype", d:"req string", c:"extended conversation type"},
        {f:"aid", d:"req dbid", c:"the account this converation is with"},
        {f:"xctok", d:"string", c:"random token to authorize next call"}],
     cache:{minutes:0},
     logflds:["xctype", "aid", "xctok"]},

    {entity:"StInt", descr:"Structured interaction e.g. beta test", fields:[
        {f:"aid", d:"req dbid", c:"interacting account"},
        {f:"email", d:"priv req unique email", c:"confirmed contact email" },
        {f:"confcode", d:"adm string", c:"interaction confirmation code"},
        {f:"status", d:"priv string", c:"testing stage workflow (*1)"},
        {f:"sitype", d:"req string", descr:"Structured interaction type label"},
        {f:"stdat", d:"priv json", descr:"Interaction state data"}],
     //*1 status: Pending|Active|Complete|Abandoned|Queued
     cache:{minutes:0},
     logflds:["aid", "sitype"]},
        
    {entity:"AppService", descr:"Processing service access", fields:[
        {f:"name", d:"string req unique", c:"Name of service"},
        {f:"ckey", d:"string", c:"consumer key"},
        {f:"csec", d:"string", c:"consumer secret"},
        {f:"data", d:"idcsv", c:"svc specific support data"}],
     cache:{minutes:4*60},  //small instances, minimum change, used a lot
     logflds:["name"]}];


    function makeFieldDescriptionLookup (fds, aliasKey) {
        descrLookup = descrLookup || {};
        aliasKey = aliasKey || "";
        fds.forEach(function (fd) {
            var key = fd.dn;
            var abbrevIndex = key.indexOf("[");
            if(abbrevIndex >= 0) {
                key = key.slice(0, abbrevIndex); }
            descrLookup[key] = {name:key, aliasof:aliasKey, src:fd};
            //console.log(key + "(" + aliasKey + "): " + fd.h);
            if(fd.aliases) {
                makeFieldDescriptionLookup(fd.aliases, key); } });
    }


    function lookupKey (dts) {
        return Object.keys(descrLookup).find(function (lokey) {
            if(dts.indexOf(lokey) >= 0) {
                //console.log("lookupKey found " + dts + " key: " + lokey);
                return true; } });
    }


    //Return true if the given field description string contains the given
    //field description name, taking into acount abbrevs and aliases. 
    //Example: fieldIs("req isodate", "string") === true
    function fieldIs (fds, dts) {
        if(!descrLookup) {
            makeFieldDescriptionLookup(fieldDescriptors); }
        var dtsk = lookupKey(dts);
        if(!dtsk) {
            throw("Unknown field type description: " + dts); }
        //console.log("fieldIs testing for: " + dtsk);
        fds = fds.split(/\s/);
        return fds.find(function (fd) {
            var fdk = lookupKey(fd);
            //console.log("fieldIs comparing against: " + fdk);
            if(!fdk) {
                throw("Bad field description element: " + fd); }
            if(fdk === dtsk) {  //same top level field descriptor lookupKey
                return true; }
            var kob = descrLookup[fdk];
            if(kob.aliasof && kob.aliasof === dtsk) {
                return true; } });
    }


    return {
        fieldDescriptors: function () { return fieldDescriptors; },
        dataDefinitions: function () { return ddefs; },
        fieldIs: function (fdef, dts) { return fieldIs(fdef, dts); }
    };
}());

