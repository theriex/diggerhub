/*global app, jt, rundata */
/*jslint browser, white, unordered, long */

app.prof = (function () {
    "use strict";

    var mgrs = {};  //container for managers. used for dispatch

    //manager dispatch function string - shorthand for event defs
    function mdfs (mgrfname, ...args) {
        var pstr = app.util.paramstr(args); var fstr;
        mgrfname = mgrfname.split(".");
        fstr = "app.prof.dispatch('" + mgrfname[0] + "','" +
            mgrfname[1] + "'" + pstr + ")";
        if(!pstr.startsWith(",event")) {  //don't return false from event hooks
            fstr = jt.fs(fstr); }
        return fstr;
    }


    mgrs.util = (function () {
    return {
        bookmarkIdentHTML: function (b) {
            return jt.tac2html(
                [["span", {cla:"dsarspan"}, b.ar],
                 " - ",
                 ["span", {cla:"dsabspan"}, b.ab]]); }
    };  //end mgrs.util returned functions
    }());


    //The home mgr displays the listener main home page contents, using the
    //server provided data.  More detailed access to any user's song data
    //requires authentication and authorization.
    mgrs.home = (function () {
        const dst = {  //display state
            //sord, songs set on init
            slen:5,
            slentoga:"more...",
            //bord, bkmks set on init
            blen:5,
            blentoga:"more..."};
        function modTimeStr (sb) {  //song or bookmark
            return sb.modified.slice(0, 19).replace("T", " "); }
        function t20star (song) {
            const playcsv = "played,iosqueue,digaudpl";
            if(song.pd && !playcsv.csvcontains(song.pd)) { return "p"; }
            if(!song.kws.csvcontains("Social")) { return "s"; }
            if(song.rv < 5) { return "g"; }
            return "&#x2605;"; }
        function linkUnless (cond, hreft, oct, txt) {
            if(cond) { return txt; }
            return jt.tac2html(["a", {href:hreft, onclick:oct}, txt]); }
        function displaySongs () {
            if(!rundata.songs) {
                return jt.out("songsdiv", 
                              "No songs for " + rundata.acct.digname); }
            jt.out("songsdiv", jt.tac2html(
                ["table", {id:"profsongstable"},
                 [["tr", {style:"text-align:left"},
                   [["th", {id:"pshmodth"},
                     linkUnless(dst.sord === "modified", "#byrecent",
                                mdfs("home.byRecent"), "modified")],
                    ["th", {id:"psht20th"},
                     linkUnless(dst.sord === "best", "#bybest",
                                mdfs("home.byBest"), "&#x2605;")],
                    ["th", {id:"pshidth"},
                     ["a", {href:"#more", onclick:mdfs("home.toglen", "slen",
                                                       "slentoga"),
                            cla:"profdescth"},
                      dst.slentoga]]]],
                  ...dst.songs.slice(0, dst.slen).map((s) =>
                      ["tr",
                       [["td", {cla:"profmodtd"}, modTimeStr(s)],
                        ["td", {cla:"psdt20td"}, t20star(s)],
                        ["td", {cla:"psdidenttd"},
                         app.deck.dispatch("util", "songIdentHTML", s)]]])
                 ]])); }
        function displayBookmarks () {
            if(!rundata.bkmks) {
                return jt.out("bkmksdiv",
                              "No bookmarks for " + rundata.acct.digname); }
            jt.out("bkmksdiv", jt.tac2html(
                ["table", {id:"profbkmkstable"},
                 [["tr", {style:"text-align:left"},
                   [["th", {id:"pbhmodth"},
                     linkUnless(dst.bord === "modified", "#byUpdate",
                                mdfs("home.byUpdated"), "updated")],
                    ["th", {id:"pbhpurth"},
                     linkUnless(dst.bord === "collected", "#collected",
                                mdfs("home.byCollected"), "collected")],
                    ["th", {id:"pbhidth"},
                     ["a", {href:"#more", onclick:mdfs("home.toglen", "blen",
                                                       "blentoga"),
                            cla:"profdescth"},
                      dst.blentoga]]]],
                  ...dst.bkmks.slice(0, dst.blen).map((b) =>
                      ["tr",
                       [["td", {cla:"profmodtd"}, modTimeStr(b)],
                        ["td", {cla:"pbdcstd"}, b.cs],
                        ["td", {cla:"pbdidenttd"},
                         mgrs.util.bookmarkIdentHTML(b)]]])
                  ]])); }
        function emptyPlaceholder (afld) {
            const mod = "0000-00-00T--:--:--Z";
            const nbsp8 = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            const spaces = nbsp8 + nbsp8 + nbsp8;
            const phs = {
                bkmks:{modified:mod, cs:"-", ar:spaces, ab:""},
                songs:{modified:mod, dsId:0, kws:"", el:49, al:49,
                       ti:spaces, ar:" ", ab:""}};
            const placeholder = phs[afld];
            dst[afld] = [placeholder]; }
    return {
        toglen: function (lenfld, togafld) {
            if(dst[lenfld] === 5) {
                dst[lenfld] = 20;
                dst[togafld] = "less..."; }
            else {
                dst[lenfld] = 5;
                dst[togafld] = "more..."; }
            displaySongs();
            displayBookmarks(); },
        byRecent: function () {
            dst.sord = "modified";
            dst.songs = rundata.songs;
            displaySongs(); },
        byBest: function () {
            dst.sord = "best";
            const cutoff = new Date(Date.now() - 2 * 7 * 24 * 60 * 60 * 1000)
                  .toISOString();
            dst.songs = rundata.songs.filter((s) => s.modified >= cutoff)
                .sort((a, b) => ((b.rv - a.rv) ||
                                 b.modified.localeCompare(a.modified)));
            displaySongs(); },
        byUpdated: function () {
            dst.bord = "modified";
            dst.bkmks = rundata.bkmks;
            emptyPlaceholder("bkmks");
            displayBookmarks(); },
        byCollected: function () {
            dst.bord = "collected";
            dst.bkmks = rundata.bkmks.filter((b) => b.cs === "Collected");
            emptyPlaceholder("bkmks");
            displayBookmarks(); },
        initialize: function () {
            if(!rundata) {
                return jt.out("reptbodydiv",
                              "Data currently unavailable, try again later"); }
            app.top.dispatch("hcu", "deserializeAccount", rundata.acct);
            jt.out("reportinnercontentdiv", jt.tac2html(
                [["div", {id:"proftitlelinediv"},
                  ["span", {id:"profnamespan"}, rundata.acct.digname]],
                 ["div", {cla:"profsectiontitlediv"}, "Songs"],
                 ["div", {id:"songsdiv"}],
                 ["div", {id:"profmuwkdiv"},
                  [["span", {id:"profmuwklabel"},
                    "collection listening summary on"],
                   ["span", {id:"profmuwkday"},
                    ((rundata.acct.settings &&
                      rundata.acct.settings.sumact &&
                      rundata.acct.settings.sumact.sendon) || "Default")]]],
                 ["div", {cla:"profsectiontitlediv"}, "Bookmarks"],
                 ["div", {id:"bkmksdiv"}]]));
            mgrs.home.byRecent();    //display songs
            mgrs.home.byUpdated(); } //display bookmarks
    };  //end mgrs.home returned functions
    }());


    //The general manager handles top level page setup and actions
    mgrs.gen = (function () {
    return {
        initialize: function () {
            if(app.startPath.startsWith("/listener")) {
                mgrs.home.initialize(); } }
    };  //end mgrs.gen returned functions
    }());


return {
    init: function () { mgrs.gen.initialize(); },
    dispatch: function (mgrname, fname, ...args) {
        return mgrs[mgrname][fname].apply(app.login, args); }
};  //end of returned functions
}());
