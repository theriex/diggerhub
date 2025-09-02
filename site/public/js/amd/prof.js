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


    //The home mgr displays the listener main home page contents, using the
    //server provided data.  More detailed access to any user's song data
    //requires authentication and authorization.
    mgrs.home = (function () {
        const dst = {  //display state
            sord:"modified",
            songs:rundata.songs,  //already sorted most recent first
            slen:5,
            slentoga:"more..."};
        function modTimeStr (song) {
            return song.modified.slice(0, 19).replace("T", " "); }
        function t20star (song) {
            const playcsv = "played,iosqueue,digaudpl";
            if(song.pd && !playcsv.csvcontains(song.pd)) { return "p"; }
            if(!song.kws.csvcontains("Social")) { return "s"; }
            if(song.rv < 5) { return "g"; }
            return "&#x2605;"; }
        function displaySongs () {
            if(!rundata.songs) {
                return jt.out("songsdiv", 
                              "No songs for " + rundata.acct.digname); }
            jt.out("songsdiv", jt.tac2html(
                ["table", {id:"profsongstable"},
                 [["tr", {style:"text-align:left"},
                   [["th", {id:"pshmodth"},
                     ["a", {href:"#byrecent", onclick:mdfs("home.byRecent")},
                      "modified"]],
                    ["th", {id:"psht20th"},
                     ["a", {href:"#bybest", onclick:mdfs("home.byBest")},
                      "&#x2605;"]],
                    ["th", {id:"pshidth"},
                     ["a", {href:"#more", onclick:mdfs("home.togslen"),
                            id:"moresongstoggle", style:"padding-left:42px"},
                      dst.slentoga]]]],
                  ...dst.songs.slice(0, dst.slen).map((s) =>
                      ["tr",
                       [["td", {cla:"pshmodtd"}, modTimeStr(s)],
                        ["td", {cla:"psht20td"}, t20star(s)],
                        ["td", {cla:"pshidenttd"},
                         app.deck.dispatch("util", "songIdentHTML", s)]]])
                 ]])); }
    return {
        togslen: function () {
            if(dst.slen === 5) {
                dst.slen = 20;
                dst.slentoga = "less..."; }
            else {
                dst.slen = 5;
                dst.slentoga = "more..."; }
            displaySongs(); },
        byRecent: function () {
            dst.songs = rundata.songs;
            displaySongs(); },
        byBest: function () {
            const cutoff = new Date(Date.now() - 2 * 7 * 24 * 60 * 60 * 1000)
                  .toISOString();
            dst.songs = rundata.songs.filter((s) => s.modified >= cutoff)
                .sort((a, b) => ((b.rv - a.rv) ||
                                 b.modified.localeCompare(a.modified)));
            displaySongs(); },
        initialize: function () {
            if(!rundata) {
                return jt.out("reptbodydiv",
                              "Data currently unavailable, try again later"); }
            app.top.dispatch("hcu", "deserializeAccount", rundata.acct);
            jt.out("reportinnercontentdiv", jt.tac2html(
                [["div", {id:"proftitlelinediv"},
                  ["span", {id:"profnamespan"}, rundata.acct.digname]],
                 ["div", {id:"songsdiv"}],
                 ["div", {id:"bkmksdiv"}],
                 ["div", {id:"muwkdiv"},
                  [["span", {id:"profmuwklabel"}, "music week ends"],
                   ["span", {id:"profmuwkday"},
                    ((rundata.acct.settings &&
                      rundata.acct.settings.sumact &&
                      rundata.acct.settings.sumact.sendon) || "Default")]]]]));
            displaySongs(); }
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
