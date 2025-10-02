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
                 ["span", {cla:"dsabspan"}, b.ab]]); },
        v4f: function (fld) {
            switch(fld) {
            case "cs": return ["Listened","Notable","Considering","Collected"];
            case "bmt": return ["Album","Performance","Song","Other"]; } },
        authdata: function (obj) {
            const acct = app.login.getAuth();
            const authobj = {an:acct.email, at:acct.token};
            var authdat = jt.objdata(authobj);
            if(obj) {
                authdat += "&" + jt.objdata(obj); }
            return authdat; },
        deactivateButton: function (bid) {
            const button = jt.byId(bid);
            if(button) {
                button.disabled = true;
                button.style.opacity = 0.5; }},
        activateButton: function (bid) {
            const button = jt.byId(bid);
            if(button) {
                button.disabled = false;
                button.style.opacity = 1.0; }}
    };  //end mgrs.util returned functions
    }());


    //The edit bookmark manager handles adding or updating a bookmark
    mgrs.edb = (function () {
        var bmk = null;
        function formValInput (fld, itype) {
            const iphs = {
                url:"Link address for bookmark",
                ar:"Artist name",
                ab:"Title of album, performance, or song",
                nt:"First impression? 2nd, 3rd?",
                haf:"Heard about this from (name or site)"};
            switch(itype) {
            case "string": return jt.tac2html(
                ["input", {type:"text", id:"edbin" + fld, size:30,
                           placeholder:iphs[fld],
                           value:(bmk[fld] || "")}]);
            case "select": return jt.tac2html(
                ["select", {id:fld + "valsel"},
                 mgrs.util.v4f(fld).map((val) =>
                     ["option", {value:val,
                                 selected:jt.toru(val === bmk[fld])},
                      val])]);
            case "text": return jt.tac2html(
                ["textarea", {id:"edbta" + fld, rows:4, cols:34,
                              placeholder:iphs[fld]},
                 (bmk[fld] || "")]); } }
        function formAttrVal (fld, itype) {
            return jt.tac2html(
                [["div", {cla:"edbformattrdiv"}, fld],
                 ["div", {cla:"edbformvalindiv"}, formValInput(fld, itype)]]); }
        function formline (content) {
            return ["div", {cla:"edbformlinediv"}, content]; }
        function readFormFieldValues () {
            bmk.url = jt.byId("edbinurl").value;
            bmk.bmt = jt.byId("bmtvalsel").value;
            bmk.cs = jt.byId("csvalsel").value;
            bmk.ar = jt.byId("edbinar").value;
            bmk.ab = jt.byId("edbinab").value;
            bmk.nt = jt.byId("edbtant").value;
            bmk.haf = jt.byId("edbinhaf").value; }
        function verifyFields () {
            var errs = [];
            const digacc = app.login.getAuth();
            if(!digacc) {
                errs.push({a:"aid", e:"Sign In to Save"}); }
            else {
                bmk.aid = digacc.dsId; }
            if(!bmk.url) {
                errs.push({a:"url", e:"URL required"}); }
            if(!mgrs.util.v4f("bmt").includes(bmk.bmt)) {
                errs.push({a:"bmt", e:"Invalid bookmark type"}); }
            if(!mgrs.util.v4f("cs").includes(bmk.cs)) {
                errs.push({a:"cs", e:"Invalid collection status value"}); }
            if(!bmk.ar.trim()) {
                errs.push({a:"ar", e:"Artist name required"}); }
            if(!bmk.ab.trim()) {
                errs.push({a:"ab", e:"Identifying title needed"}); }
            return errs; }
        function updateAndEnd (po) {  //params object.  bmk ready to save
            jt.out("edbformactmsgdiv", po.waitmsg);
            po.btids.forEach(function (btid) { 
                mgrs.util.deactivateButton(btid); });
            setTimeout(function () {  //reflect the display updates first
                const dat = mgrs.util.authdata(bmk);
                jt.call("POST", app.util.dr("/api/updbmrk"), dat,
                        function (bkmks) {
                            bmk = bkmks[0];
                            jt.out("edbformactmsgdiv", po.okmsg);
                            po.btids.forEach(function (btid) {
                                mgrs.util.activateButton(btid); });
                            setTimeout(mgrs.bks.initialize, 500); },
                        function (code, errtxt) {
                            mgrs.util.activateButton("edbsaveb");
                            jt.out("edbformactmsgdiv", po.failpre + " " + code +
                                   ": " + errtxt); }); }, 100); }
    return {
        bmkshtxt: function (b) {
            return [b.url,
                    "type: " + b.bmt + ",  stat: " + b.cs,
                    b.ar,
                    b.ab,
                    b.nt].join("\n"); },
        share: function () {
            const sdivid = "edbformtopmsgdiv";
            if(!bmk.dsId) {
                jt.out("edbformtopmsgdiv", "Save bookmark before sharing"); }
            else {
                app.svc.copyToClipboard(
                    mgrs.edb.bmkshtxt(bmk),
                    function () {
                        jt.out(sdivid, "Bookmark copied to clipboard."); },
                    function () {
                        jt.out(sdivid, "Bookmark text copy failed."); }); }
            setTimeout(function () {
                jt.out(sdivid, ""); }, 3800); },
        cancel: function () {
            jt.out("profelemdetdiv", ""); },
        rmbkmk: function () {
            jt.out("edbformactmsgdiv", "Delete bookmark?");
            jt.out("edbformbuttonsdiv", jt.tac2html(
                [["button", {type:"button", id:"edbdelcancelb",
                             onclick:mdfs("edb.editBookmark")}, "Cancel"],
                 ["button", {type:"button", id:"edbdelconfb",
                             onclick:mdfs("edb.rmbkconf")}, "Delete"]])); },
        rmbkconf: function () {
            bmk.cs = "Deleted";
            updateAndEnd({waitmsg:"Deleting...", okmsg:"Deleted.",
                          failpre:"Delete failed",
                          btids:["edbsaveb", "edbdelcancelb"]}); },
        save: function () {
            readFormFieldValues();
            const errs = verifyFields();
            if(errs.length) {
                return jt.out("edbformactmsgdiv", jt.tac2html(errs.map((e) =>
                    ["div", {cla:"edbformfielderrline"}, e.e]))); }
            updateAndEnd({waitmsg:"Saving...", okmsg:"Saved.",
                          failpre:"Save failed",
                          btids:["edbdeleteb", "edbsaveb"]}); },
        editBookmark: function (bookmark) {
            bmk = bookmark;
            jt.out("profelemdetdiv", jt.tac2html(
                ["div", {id:"edbform"},
                 [["div", {id:"edbformtopdiv"},
                   [["div", {id:"edbformtitlediv"}, "Edit Bookmark"],
                    ["div", {id:"edbformsharediv"},
                     ["a", {href:"#share", onclick:mdfs("edb.share")},
                      ["img", {cla:"featureico", id:"shareicoimg",
                               src:app.util.dr("img/share.png")}]]],
                    ["div", {id:"edbformtopmsgdiv"}],
                    ["div", {id:"edbformxdiv"},
                     ["a", {href:"#close", onclick:mdfs("edb.cancel")}, "X"]]]],
                  formline(formAttrVal("url", "string")),
                  formline([formAttrVal("bmt", "select"),
                            formAttrVal("cs", "select")]),
                  formline(formAttrVal("ar", "string")),
                  formline(formAttrVal("ab", "string")),
                  formline(formAttrVal("nt", "text")),
                  formline(formAttrVal("haf", "string")),
                  ["div", {id:"edbformactionsdiv"},
                   [["div", {id:"edbformactmsgdiv"}],
                    ["div", {id:"edbformbuttonsdiv", cla:"dlgbuttonsdiv"},
                     [["button", {type:"button", id:"edbdeleteb",
                                  onclick:mdfs("edb.rmbkmk")}, "Delete"],
                      ["button", {type:"button", id:"edbsaveb",
                                  onclick:mdfs("edb.save")}, "Save"]]]]]]]));
            if(!bmk.dsId) {
                mgrs.util.deactivateButton("edbdeleteb");
                jt.byId("shareicoimg").style.opacity = 0.5; } }
    };  //end mgrs.edb returned functions
    }());


    //The bookmarks manager handles the interface for your bookmarks.
    mgrs.bks = (function () {
        const dst = {  //runtime display state
            hfs:{  //header field definitions
                sortord:{t:"toggle", vi:0, vs:["recent", "oldest"],
                         bmkfld:"modified", vdf:(v) => jt.tac2html(
                             ["span", {cla:"bmfmodspan"},
                              v.slice(0,16).replace("T", " ")])},
                cs:{t:"select", vi:0, vs:["collstat", ...mgrs.util.v4f("cs")],
                    tdc:"bmfldcentertd"},
                bmt:{t:"select", vi:0, vs:["type", ...mgrs.util.v4f("bmt")],
                     tdc:"bmfldcentertd"},
                ar:{t:"search", val:"", lab:"artist"},
                ab:{t:"search", val:"", lab:"title"}},
            fbks:{}}; //fetched bookmarks by fetch key
        function hfval (hfld) {
            var val = "unknown";
            const fldat = dst.hfs[hfld];
            if(fldat.t !== "search") {
                val = fldat.vs[fldat.vi]; }
            else {
                val = fldat.val || fldat.lab; }
            return val; }
        function fetchKey () {
            return Object.keys(dst.hfs).map((k) => hfval(k)).join(""); }
        function bkrowStyle (bmk) {
            switch(bmk.cs) {
                case "Collected": return "background-color:#f6ee9f";  //yellow
                case "Considering": return "background-color:#9ff6c1"; //green;
                case "Notable": return "background-color:#9feaf6";     //blue;
                default: return ""; } }
        function makeTabularDisplay (ctrs) {  //redraw matched header/content
            jt.out("profcontdispdiv", jt.tac2html(
                [["div", {cla:"profsectiontitlediv"},
                  ["Bookmarks",
                   ["a", {href:"#addbookmark", id:"addbookmarklink",
                          onclick:mdfs("bks.showDetails", -1)},
                    ["img", {src:app.util.dr("img/plusbutton.png"),
                             cla:"featureico"}]]]],
                 ["table", {id:"profbktable"},
                  [["tr", {id:"profbktableheadertr"},
                    Object.keys(dst.hfs).map((fnm) =>
                        ["td", {id:fnm + "htd", cla:"bmhtd",
                                onclick:mdfs("bks.headerFieldClick", fnm)},
                         hfval(fnm)])],
                   ...ctrs]]])); }  //content table rows
        function displayBookmarks () {  //redraw header row to ensure data match
            Object.keys(dst.hfs).forEach(function (fk) {
                const fd = dst.hfs[fk];
                fd.bmkfld = fd.bmkfld || fk;
                fd.tdc = fd.tdc || "bmfldtd";
                fd.vdf = fd.vdf || function(v) { return jt.tac2html(
                    ["span", {cla:"bmf" + fk + "span"}, v]); }; });
            const bookmarks = dst.fbks[fetchKey()]
                  .filter((b) => b.cs !== "Deleted");  //in case cached
            makeTabularDisplay(bookmarks.map((bmk, idx) =>
                ["tr", {id:"bktr" + bmk.dsId, cla:"clickabletr",
                        onclick:mdfs("bks.showDetails", idx),
                        style:bkrowStyle(bmk)},
                  jt.tac2html(Object.keys(dst.hfs).map((fk) =>
                     ["td", {cla:dst.hfs[fk].tdc},
                      dst.hfs[fk].vdf(bmk[dst.hfs[fk].bmkfld])]))])); }
        function dispErr (txt) {
            makeTabularDisplay(
                [["tr", ["td", {colspan:Object.keys(dst.hfs).length,
                                id:"bmkerrtd"},
                         txt]]]); }
        function prepareDisplay (digname) {
            if(digname) {
                jt.out("profnamespan", jt.tac2html(
                    ["a", {href:app.util.dr("/listener/" + digname)},
                     digname])); }
            dispErr(""); }
        function fetchAndDisplayBookmarks () {
            const acct = app.login.getAuth();
            prepareDisplay(acct.digname);
            if(dst.fbks[fetchKey()]) {
                if(!dst.fbks[fetchKey()].length) {
                    return dispErr("No bookmarks found"); }
                return displayBookmarks(); }
            const data = {an:acct.email, at:acct.token};
            Object.keys(dst.hfs).forEach(function (fnm) {
                const fldat = dst.hfs[fnm];
                if(fldat.t === "toggle") {
                    data[fnm] = fldat.vs[fldat.vi]; }
                else if(fldat.t === "select" && fldat.vi > 0) {
                    data[fnm] = fldat.vs[fldat.vi]; }
                else if(fldat.t === "search" && fldat.val) {
                    data[fnm] = fldat.val; } });
            const url = app.util.cb(app.util.dr("/api/bmrkfetch"), data);
            jt.call("GET", url, null,
                    function (bms) {
                        dst.fbks[fetchKey()] = bms;
                        if(!bms.length) {
                            return dispErr("No bookmarks found"); }
                        displayBookmarks(); },
                    function (code, errtxt) {
                        dispErr("Fetch error " + code + ": " + errtxt); }); }
    return {
        headerFieldClick: function (fnm) {
            var iref;
            const fldat = dst.hfs[fnm];
            switch(fldat.t) {
            case "toggle":
                fldat.vi = (fldat.vi? 0 : 1);
                return fetchAndDisplayBookmarks();
            case "select":
                iref = jt.byId(fnm + "sel");
                if(!iref) {
                    return jt.out(fnm + "htd", jt.tac2html(
                        ["select", {id:fnm + "sel"},
                         fldat.vs.map((val, idx) =>
                             ["option", {value:(idx? val : ""),
                                         selected:jt.toru(idx === fldat.vi),
                                         onchange:mdfs("bks.headerFieldClick",
                                                       fnm)},
                              val])])); }
                else {  //have selection
                    fldat.vi = iref.selectedIndex;
                    return fetchAndDisplayBookmarks(); }
            case "search":
                iref = jt.byId(fnm + "srchin");
                if(!iref) {
                    jt.out(fnm + "htd", jt.tac2html(
                        ["input", {type:"text",
                                   id:fnm + "srchin", size:16}]));
                    fldat.wiv = "";  //working input value
                    fldat.wvsc = 0;  //working value stability count
                    fldat.tmo = setTimeout(mgrs.bks.headerFieldClick,
                                           800); }
                else {  //have field value filter input
                    iref = jt.byId(fnm + "srchin").value;
                    if(iref !== fldat.wiv) {  //input value has changed
                        fldat.wiv = iref;
                        fldat.wvsc = 0;
                        fldat.tmo = setTimeout(mgrs.bks.headerFieldClick,
                                               800); }
                    else {  //input value unchanged
                        if(fldat.wvsc >= 3) {
                            fldat.val = fldat.wiv;
                            clearTimeout(fldat.tmo);  //just in case
                            fetchAndDisplayBookmarks(); }
                        else {  //still waiting
                            fldat.wvsc += 1;
                            fldat.tmo = setTimeout(mgrs.bks.headerFieldClick,
                                                   800); } } }
                break; } },
        showDetails: function (bmidx) {
            var bmk = {};
            if(bmidx >= 0) {
                bmk = dst.fbks[fetchKey()][bmidx]; }
            mgrs.edb.editBookmark(bmk); },
        initialize: function () {
            jt.out("profnamespan", "Bookmarks");
            mgrs.gen.setRequireAccountFunctions(
                fetchAndDisplayBookmarks,
                fetchAndDisplayBookmarks);
            jt.out("profelemdetdiv", "");
            jt.out("profcontdispdiv", "");
            dst.fbks = {};
            prepareDisplay();
            mgrs.gen.requireAcc(); }
    };  //end mgrs.bks returned functions
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
            return sb.modified.slice(0, 19).replace("T", " "); }  //placeholder
        function t20star (song) {
            const playcsv = "played,iosqueue,digaudpl";
            if(song.pd && !playcsv.csvcontains(song.pd)) { 
                return "&#x21B7;"; }  //skip arrow indicator
            if(!song.kws.csvcontains("Social")) {
                return "-"; }  //no rating to share socially
            if(song.rv < 5) { return "g"; }
            return "&#x2605;"; }
        function linkUnless (cond, hreft, oct, txt) {
            if(cond) { return txt; }
            return jt.tac2html(["a", {href:hreft, onclick:oct}, txt]); }
        function rowsOrPlaceholder(typestr, rows) {
            if(!rows.length) {
                return jt.tac2html(
                    ["tr", ["td", {cla:"profmodtd"},
                            "No " + typestr + " found"]]); }
            return rows; }
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
                  ...rowsOrPlaceholder("Songs",
                      dst.songs.slice(0, dst.slen).map((s, i) =>
                          ["tr",
                           [["td", {cla:"profmodtd"}, modTimeStr(s)],
                            ["td", {cla:"psdt20td"}, t20star(s)],
                            ["td", {cla:"psdidenttd"},
                             ["a", {href:"#" + s.dsId,
                                    onclick:mdfs("home.itemdet", "songs", i)},
                              app.deck.dispatch("util", "songIdentHTML",
                                                s)]]]]))]])); }
        function displayBookmarks () {
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
                  ...rowsOrPlaceholder("Bookmarks",
                      dst.bkmks.slice(0, dst.blen).map((b, i) =>
                          ["tr",
                           [["td", {cla:"profmodtd"}, modTimeStr(b)],
                            ["td", {cla:"bmfldcentertd"},
                             ["span", {cla:"bmfcsspan"}, b.cs]],
                            ["td", {cla:"pbdidenttd"},
                             ["a", {href:"#" + b.dsId,
                                    onclick:mdfs("home.itemdet", "bkmks", i)},
                             mgrs.util.bookmarkIdentHTML(b)]]]]))]]));
            app.pdat.addApresDataNotificationTask("displayBookmarkPageAccess",
                                                  displayBookmarkPageAccess); }
        function displayBookmarkPageAccess () {
            mgrs.gen.setRequireAccountFunctions(mgrs.bks.initialize,
                                                displayBookmarkPageAccess);
            jt.out("profbkmkaccessdiv", jt.tac2html(
                ["a", {href:"#update", onclick:mdfs("gen.requireAcc")},
                 "Update"])); }
        function wt20label () {
            var lab = "collection listening summary";
            const st = jt.saferef(rundata, "acct.?settings.?sumact.?lastsend");
            if(st) {
                const std = jt.isoString2Time(st);
                if(Date.now() - std.getTime() <= 7 * 24 * 60 * 60 * 1000) {
                    const url = app.util.dr("/plink/wt20/theriex/" +
                                            st.slice(0, 10));
                    lab = jt.tac2html(["a", {href:url}, lab]); } }
            return lab; }
        function wt20day () {
            const so = jt.saferef(rundata, "acct.?settings.?sumact.?sendon");
            return so || "Default"; }
        function searchURLForSong (song) {
            var txt = song.ti + " " + song.ar;
            if(song.ab && song.ab !== "Singles") {
                txt += " " + song.ab; }
            return "https://duckduckgo.com/?q=" + jt.escq(jt.enc(txt)); }
        function songdethtml (s) {
            const eavs = app.player.dispatch("cmt", "elal2txtvals", s);
            return jt.tac2html(
                [["a", {href:"#search",
                        onclick:"window.open('" + searchURLForSong(s) +
                                "');return false"},
                  [["div", {id:"pititlediv"}, s.ti],
                   ["div", {id:"piartistdiv"}, s.ar],
                   ["div", {id:"pialbumdiv"}, s.ab]]],
                 ["div", {id:"picommentdiv"},
                  app.player.dispatch("cmt", "cleanCommentText", s.nt)],
                 ["div", {id:"piimprdiv"},
                  [Object.keys(eavs).map((k) =>
                      ["div", {cla:"profitemattrvaldiv"},
                       [["span", {cla:"piattrspan"}, eavs[k].pn + ":"],
                        ["span", {cla:"pivalspan"}, eavs[k].val]]])]],
                 ["div", {id:"pikwdsdiv"}, s.kws.csvarray().join(", ")]]); }
        function bkmkdethtml (b) {
            return jt.tac2html(
                [["div", {id:"piurldiv"},
                  ["a", {href:b.url,
                         onclick:"window.open('" + b.url + "');return false"},
                   b.url]],
                 ["div", {id:"piimprdiv"},
                  [["div", {cla:"profitemattrvaldiv"},
                    [["span", {cla:"piattrspan"}, "type:"],
                     ["span", {cla:"pivalspan"}, b.bmt]]],
                   ["div", {cla:"profitemattrvaldiv"},
                    [["span", {cla:"piattrspan"}, "stat:"],
                     ["span", {cla:"pivalspan"}, b.cs]]]]],
                 ["div", {id:"piartistdiv"}, b.ar],
                 ["div", {id:"pititlediv"}, b.ab],
                 ["div", {id:"picommentdiv"}, b.nt],
                 ["div", {id:"pikwdsdiv"}, b.haf]]); }
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
            displayBookmarks(); },
        byCollected: function () {
            dst.bord = "collected";
            dst.bkmks = rundata.bkmks.filter((b) => b.cs === "Collected");
            displayBookmarks(); },
        closedet: function () {
            jt.out("profelemdetdiv", ""); },
        itemdet: function (fld, idx) {
            jt.out("profelemdetdiv", jt.tac2html(
                ["div", {id:"profelemdetcontdiv"},
                 [["div", {id:"profelemitemdetdiv"},
                   (fld === "songs"? songdethtml(dst.songs[idx])
                                   : bkmkdethtml(dst.bkmks[idx]))],
                  ["div", {id:"profelemitemsharediv"},
                   ["a", {href:"#share",
                          onclick:mdfs("home.itemshare", fld, idx)},
                    ["img", {cla:"featureico", id:"shareicoimg",
                             src:app.util.dr("img/share.png")}]]],
                  ["div", {id:"profelemdetxdiv"},
                   ["a", {href:"#close", onclick:mdfs("home.closedet")},
                    "X"]]]])); },
        itemshare: function (fld, idx) {
            var txt = "";
            const de = dst[fld][idx];
            const sdivid = "profelemitemsharediv";
            switch(fld) {
            case "songs":
                txt = app.player.dispatch("cmt", "clipboardTextForSong", de);
                break;
            case "bkmks":
                txt = mgrs.edb.bmkshtxt(de);
                break; }
            app.svc.copyToClipboard(txt,
                function () {
                    jt.out(sdivid, "Details copied to clipboard."); },
                function () {
                    jt.out(sdivid, "Clipboard copy failed."); }); },
        wt20init: function (songs) {  //called from login.rpt.initialize
            dst.songs = songs; },
        initialize: function () {
            app.top.dispatch("hcu", "deserializeAccount", rundata.acct);
            if(rundata.bkmks && rundata.bkmks.length) {
                rundata.bkmks = rundata.bkmks.filter((b) =>
                    b.cs !== "Deleted"); }  //in case cached
            jt.out("profnamespan", rundata.acct.digname);
            jt.out("profcontdispdiv", jt.tac2html(
                [["div", {cla:"profsectiontitlediv"}, "Songs"],
                 ["div", {id:"songsdiv"}],
                 ["div", {id:"profmuwkdiv"},
                  [["span", {id:"profmuwklabel"}, wt20label()],
                   ["span", {id:"profmuwkday"}, wt20day()]]],
                 ["div", {cla:"profsectiontitlediv"},
                  ["Bookmarks",
                   ["div", {id:"profbkmkaccessdiv"}]]],
                 ["div", {id:"bkmksdiv"}]]));
            mgrs.home.byRecent();   //display songs
            mgrs.home.byUpdated();  //display bookmarks
            app.login.dispatch("hua", "initDisplay"); }
    };  //end mgrs.home returned functions
    }());


    //The general manager handles top level page setup and actions
    mgrs.gen = (function () {
        const rafs = {  //require account functions
            haf: function () {
                jt.log("prof.rafs have account function default message"); },
            psf: function () {
                jt.log("prof.rafs post signin function default message"); }};
    return {
        setRequireAccountFunctions: function(haf, psf) {
            rafs.haf = haf;
            rafs.psf = psf; },
        requireAcc: function () {
            const acc = app.login.getAuth();
            if(!acc) {
                const siid = "hubaccountcontentdiv";
                jt.byId(siid).style.display = "block";
                app.login.dispatch("hsi", "signIn", siid, function (siacc) {
                    app.login.dispatch("ap", "save", siacc);
                    jt.byId(siid).style.display = "none";
                    rafs.psf(); });
                const emailin = jt.byId("emailin");
                if(emailin) {
                    emailin.focus(); } }
            else { //have account
                rafs.haf(); } },
        initialize: function () {
            if(!rundata) {
                return jt.out("reptbodydiv",
                              "Data currently unavailable, try again later"); }
            jt.out("reportinnercontentdiv", jt.tac2html(
                [["div", {id:"proftitlelinediv"},
                  ["span", {id:"profnamespan"}]],
                 ["div", {id:"hubaccountcontentdiv", cla:"boxedcontentdiv",
                          style:"display:none"}],
                 ["div", {id:"profcontentdiv"},
                  [["div", {id:"profcontdispdiv"}],
                   ["div", {id:"profelemdetdiv"}]]]]));
            app.top.dispatch("aaa", "initialize");
            app.top.dispatch("afg", "runOutsideApp", "hubaccountcontentdiv");
            if(app.startPath.startsWith("/listener")) {
                mgrs.home.initialize(); }
            else if(app.startPath.startsWith("/bookmarks")) {
                mgrs.bks.initialize(); } }
    };  //end mgrs.gen returned functions
    }());


return {
    init: function () { mgrs.gen.initialize(); },
    dispatch: function (mgrname, fname, ...args) {
        return mgrs[mgrname][fname].apply(app.login, args); }
};  //end of returned functions
}());
