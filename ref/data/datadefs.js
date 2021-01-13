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
        {f:"email", d:"priv req unique email"},
        {f:"phash", d:"adm req string"},
        {f:"status", d:"priv string", c:"Not currently used",
         enumvals:["Pending", "Active", "Inactive", "Unreachable"]},
        {f:"actsends", d:"adm gencsv", c:"latest first isod;emaddr vals"},
        {f:"actcode", d:"adm string", c:"account activation code"},
        {f:"lastsync", d:"string", c:"latest sync timestamp for this account"},
        {f:"firstname", d:"req string", c:"general display use"},
        {f:"hashtag", d:"unique", c:"activity view handle"},
        {f:"kwdefs", d:"json", c:"keyword definitions used by this account"},
        {f:"igfolds", d:"json", c:"ignore folders used by this account"},
        {f:"settings", d:"json", c:"general options, e.g. no activity disp"}],
     cache:{minutes:2*60}, //fast auth after initial load
     logflds:["email", "firstname"]},

    {entity:"Song", descr:"Rating and play information", fields:[
        {f:"aid", d:"req dbid", c:"the account this song info is from"},
        {f:"path", d:"text", c:"full file path from most recent update"},
        {f:"ti", d:"req string", c:"title of song"},
        {f:"ar", d:"string", c:"artist for song"},
        {f:"ab", d:"string", c:"album for song"},
        {f:"el", d:"int", i:49, c:"energy level for this song"},
        {f:"al", d:"int", i:49, c:"approachability level for this song"},
        {f:"kws", d:"string", c:"keywords associated with this song"},
        {f:"rv", d:"int", i:5, c:"rating value (stars) 1-10"},
        {f:"fq", d:"string", c:"play frequency code (see player)"},
        {f:"lp", d:"isodate", c:"last played timestamp"},
        {f:"nt", d:"text", c:"note text (whatever the user wrote)"}],
     cache:{minutes:0},
     logflds:["aid", "ti", "ar"]},
        
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

