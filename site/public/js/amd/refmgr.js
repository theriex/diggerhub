//////////////////////////////////////////////////
//
//     D O   N O T   E D I T
//
// This file was written by makeCRUD.js.  Any changes should be made there.
//
//////////////////////////////////////////////////
// Local object reference cache and server persistence access.  Automatically
// serializes/deserializes JSON fields.

/*global app, jt, window, console */

/*jslint browser, white, fudge, long */

app.refmgr = (function () {
    "use strict";

    var cache = {};

    var persistentTypes = ["DigAcc", "Song", "Bookmark", "SKeyMap", "DigMsg", "SASum", "XConvo", "StInt", "AppService"];


    //All json fields are initialized to {} so they can be accessed directly.
    function reconstituteFieldJSONObject (field, obj) {
        if(!obj[field]) {
            obj[field] = {}; }
        else {
            var text = obj[field];
            try {
                obj[field] = JSON.parse(text);
            } catch (e) {
                jt.log("reconstituteFieldJSONObject " + obj.dsType + " " +
                       obj.dsId + " " + field + " reset to empty object from " +
                       text + " Error: " + e);
                obj[field] = {};
            } }
    }


    function reconstituteFieldJSONArray (field, obj) {
        reconstituteFieldJSONObject(field, obj);
        if(!Array.isArray(obj[field])) {
            obj[field] = []; }
    }


    function deserialize (obj) {
        switch(obj.dsType) {
        case "DigAcc":
            reconstituteFieldJSONObject("hubdat", obj);
            reconstituteFieldJSONObject("kwdefs", obj);
            reconstituteFieldJSONObject("igfolds", obj);
            reconstituteFieldJSONObject("settings", obj);
            reconstituteFieldJSONArray("musfs", obj);
            break;
        case "Song":
            break;
        case "Bookmark":
            reconstituteFieldJSONObject("abi", obj);
            reconstituteFieldJSONObject("trk", obj);
            reconstituteFieldJSONObject("si", obj);
            reconstituteFieldJSONObject("det", obj);
            break;
        case "SKeyMap":
            reconstituteFieldJSONObject("notes", obj);
            break;
        case "DigMsg":
            break;
        case "SASum":
            reconstituteFieldJSONArray("songs", obj);
            reconstituteFieldJSONObject("easiest", obj);
            reconstituteFieldJSONObject("hardest", obj);
            reconstituteFieldJSONObject("chillest", obj);
            reconstituteFieldJSONObject("ampest", obj);
            break;
        case "XConvo":
            break;
        case "StInt":
            reconstituteFieldJSONObject("stdat", obj);
            break;
        case "AppService":
            break;
        }
        return obj;
    }


    function serialize (obj) {
        switch(obj.dsType) {
        case "DigAcc":
            obj.hubdat = JSON.stringify(obj.hubdat);
            obj.kwdefs = JSON.stringify(obj.kwdefs);
            obj.igfolds = JSON.stringify(obj.igfolds);
            obj.settings = JSON.stringify(obj.settings);
            obj.musfs = JSON.stringify(obj.musfs);
            break;
        case "Song":
            break;
        case "Bookmark":
            obj.abi = JSON.stringify(obj.abi);
            obj.trk = JSON.stringify(obj.trk);
            obj.si = JSON.stringify(obj.si);
            obj.det = JSON.stringify(obj.det);
            break;
        case "SKeyMap":
            obj.notes = JSON.stringify(obj.notes);
            break;
        case "DigMsg":
            break;
        case "SASum":
            obj.songs = JSON.stringify(obj.songs);
            obj.easiest = JSON.stringify(obj.easiest);
            obj.hardest = JSON.stringify(obj.hardest);
            obj.chillest = JSON.stringify(obj.chillest);
            obj.ampest = JSON.stringify(obj.ampest);
            break;
        case "XConvo":
            break;
        case "StInt":
            obj.stdat = JSON.stringify(obj.stdat);
            break;
        case "AppService":
            break;
        }
        return obj;
    }


    function clearPrivilegedFields (obj) {
        switch(obj.dsType) {
        case "DigAcc":
            obj.email = "";
            obj.hubdat = "";
            obj.status = "";
            break;
        case "Song":
            break;
        case "Bookmark":
            break;
        case "SKeyMap":
            break;
        case "DigMsg":
            break;
        case "SASum":
            break;
        case "XConvo":
            break;
        case "StInt":
            obj.email = "";
            obj.status = "";
            obj.stdat = "";
            break;
        case "AppService":
            break;
        }
    }


return {

    cached: function (dsType, dsId) {  //Returns the cached obj or null
        if(dsType && dsId && cache[dsType] && cache[dsType][dsId]) {
            return cache[dsType][dsId]; }
        return null; },


    put: function (obj) {  //obj is already deserialized
        if(!obj) {
            jt.log("refmgr.put: Attempt to put null obj");
            console.trace(); }
        clearPrivilegedFields(obj);  //no sensitive info in cache
        cache[obj.dsType] = cache[obj.dsType] || {};
        cache[obj.dsType][obj.dsId] = obj;
        return obj;
    },


    getFull: function (dsType, dsId, contf) {
        var obj = app.refmgr.cached(dsType, dsId);
        if(obj) {  //force an async callback for consistent code flow
            return setTimeout(function () { contf(obj); }, 50); }
        if(persistentTypes.indexOf(dsType) < 0) {
            jt.log("refmgr.getFull: unknown dsType " + dsType);
            console.trace(); }
        var url = app.util.dr("/api/fetchobj?dt=" + dsType + "&di=" + dsId +
                         jt.ts("&cb=", "second"));
        var sem = jt.semaphore("refmgr.getFull" + dsType + dsId);
        if(sem && sem.critsec === "processing") {
            setTimeout(function () {
                app.refmgr.getFull(dsType, dsId, contf); }, 200);
            return; }  //try again later, hopefully find cached
        var logpre = "refmgr.getFull " + dsType + " " + dsId + " ";
        jt.call("GET", url, null,
                function (objs) {
                    var retobj = null;
                    if(objs.length > 0) {
                        retobj = objs[0];
                        jt.log(logpre + "cached.");
                        deserialize(retobj);
                        app.refmgr.put(retobj); }
                    contf(retobj); },
                function (code, errtxt) {
                    jt.log(logpre + code + ": " + errtxt);
                    contf(null); },
                sem);
    },


    uncache: function (dsType, dsId) {
        cache[dsType] = cache[dsType] || {};
        cache[dsType][dsId] = null;
    },


    serverUncache: function (dsType, dsId, contf, errf) {
        app.refmgr.uncache(dsType, dsId);
        var logpre = "refmgr.serverUncache " + dsType + " " + dsId + " ";
        var url = app.util.dr("/api/uncache?dt=" + dsType + "&di=" + dsId +
                         jt.ts("&cb=", "second"));
        jt.call("GET", url, null,
                function () {
                    jt.log(logpre + "completed.");
                    if(contf) { contf(); } },
                function (code, errtxt) {
                    jt.log(logpre + "failed " + code + ": " + errtxt);
                    if(errf) { errf(); } },
                jt.semaphore("refmgr.serverUncache" + dsType + dsId));
    },


    deserialize: function (obj) {
        return deserialize(obj);
    },


    postdata: function (obj, skips) {
        serialize(obj);
        var dat = jt.objdata(obj, skips);
        deserialize(obj);
        return dat;
    }

}; //end of returned functions
}());

