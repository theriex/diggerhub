/*global app, jt */
/*jslint browser, white, unordered */

app.login = (function () {
    "use strict";

    var authobj = null;  //basically the DigAcc, but may skip some fields
    var mgrs = {};  //container for managers. used for dispatch


    //manager dispatch function string - shorthand for event defs
    function mdfs (mgrfname, ...args) {
        var pstr = app.paramstr(args); var fstr;
        mgrfname = mgrfname.split(".");
        fstr = "app.login.dispatch('" + mgrfname[0] + "','" +
            mgrfname[1] + "'" + pstr + ")";
        if(pstr !== ",event") {  //don't return false from event hooks
            fstr = jt.fs(fstr); }
        return fstr;
    }


    //The authentication persistence manager handles cookies.  Could use 
    //window.localStorage except that is insecure it and can fail when 
    //running on localhost.  A SameSite=Strict cookie may also fail on
    //localhost.  Going with tried and true cookies for now.
    mgrs.ap = (function () {
        var delim = "..diggerhubauth..";
        var sname = "diggerhubauth";
    return {
        save: function () {
            try {
                jt.cookie(sname, authobj.email + delim + authobj.token,
                          //The cookie is rewritten each login.  Good to
                          //expire if inactive, since security and storage
                          //options continue to evolve.
                          30);
                jt.log("login.mgrs.ap.save success");
            } catch (e) {
                jt.log("login.mgrs.ap.save exception: " + e); } },
        read: function () {
            var ret = null;
            try {
                ret = jt.cookie(sname);  //ret null if not found
                if(ret) {
                    if(ret.indexOf(delim) < 0) {
                        jt.log("login.mgrs.ap.read clearing " + ret + ": " +
                               delim + " delimiter not found.");
                        mgrs.ap.clear();
                        ret = null; }
                    else {
                        ret = ret.split(delim);
                        ret[0] = ret[0].replace("%40", "@");
                        if(!jt.isProbablyEmail(ret[0]) || ret[1].length < 20) {
                            jt.log("login.mgrs.ap.read clearing bad values: " +
                                   ret[0] + ", " + ret[1]);
                            mgrs.ap.clear();
                            ret = null; }
                        else {
                            jt.log("login.mgrs.ap.read success");
                            ret = {authname:ret[0], authtoken:ret[1]}; } } }
            } catch (e) {
                jt.log("login.mgrs.ap.read exception: " + e);
                ret = null;
            }
            return ret; },
        clear: function () {
            try {
                jt.cookie(sname, "", -1);
            } catch (e) {
                jt.log("login.mgrs.ap.clear exception: " + e); } },
        signInUsingCookie: function (contf, errf) {
            var ret = mgrs.ap.read();
            if(!ret) {
                return errf(403, "Cookie read failed"); }
            const ps = {an:ret.authname, at:ret.authtoken};
            jt.call("POST", app.dr("/api/acctok"), jt.objdata(s),
                    contf, errf); }
    };  //end mgrs.ap returned functions
    }());


    //The hub account display manager handles account access outside of app
    mgrs.had = (function () {
        var cred = null;
    return {
        initialSignIn: function (contf, errf) {
            var auth = null;
            if(app.startParams.an && app.startParams.at) {
                auth = {an:app.startParams.an, at:app.startParams.at}; }
            else {
                const cookauth = mgrs.ap.read();
                if(cookauth) {
                    auth = {an:cookauth.authname, at:cookauth.authtoken}; } }
            if(auth) {
                jt.call("POST", app.dr("/api/acctok"), jt.objdata(auth),
                        contf, errf); }
            else {
                errf(403, "No authentication parameters given"); } },
        signOut: function () {
            authobj = null;
            mgrs.ap.clear(); },
        display: function () {
            window.history.replaceState({}, document.title, "/account");
            jt.out("logodiv", "");  //clear overlay
            jt.out("outercontentdiv", jt.tac2html(
                ["div", {id:"hubactionpagediv"},
                 [["div", {id:"hubactionheaderdiv"},
                   [["div", {id:"homelinkdiv"},
                     ["a", {href:"/", title:"DiggerHub Home Page"},
                      ["img", {src:"/img/appicon.png", cla:"hubacttitleimg"}]]],
                    ["div", {id:"hubactiontitlediv"},
                     "DiggerHub Account"]]],
                  ["div", {id:"contentdiv"},  //as used in digger app
                   ["div", {id:"haddiv"}, "Starting..."]]]]));
            app.top.dispatch("afg", "setDisplayDiv", "haddiv");
            app.top.dispatch("afg", "setInApp", "");
            mgrs.had.initialSignIn(
                function (accntok) {
                    app.top.dispatch("hcu", "deserializeAccount", accntok[0]);
                    app.top.dispatch("aaa", "reflectAccountChangeInRuntime",
                                     accntok[0], accntok[1]);
                    authobj = app.top.dispatch("aaa", "getAccount");
                    mgrs.ap.save();
                    app.top.dispatch("afg", "accountFanGroup", "personal"); },
                function () {  //not signed in
                    app.top.dispatch("afg", "accountFanGroup"); }); }
    };  //end mgrs.had returned functions
    }());


    //The marquee manager handles headline text in the default display
    mgrs.mrq = (function () {
        const mst = {  //marguee settings
            fis:0.3,   //fade-in seconds
            fos:1.2,   //fade-out seconds
            dts:8};    //text display time seconds
        const mhds = [
            "Music is art",
            "What you listen to matters",
            "Your collection is you",
            "Your impressions matter",
            "Artists enrich your life",
            "Songs touch your soul"];
        var idx = 0;
    return {
        nextStatement: function () {
            const md = jt.byId("marqueediv");
            md.style.transition = "opacity " + mst.fos + "s";
            md.style.opacity = 0.0;
            setTimeout(function () {
                md.innerHTML = mhds[idx] + ".";
                idx = (idx + 1) % mhds.length;
                md.style.transition = "opacity " + mst.fis + "s";
                md.style.opacity = 1.0; }, mst.fos * 1000);
            setTimeout(mgrs.mrq.nextStatement, (mst.fis + mst.dts) * 1000); },
        runMarquee: function () {
            if(jt.byId("marqueediv")) { return; }  //already set up and running
            jt.out("headertextdiv", jt.tac2html(["div", {id:"marqueediv"}]));
            mgrs.mrq.nextStatement(); }
    };  //end mgrs.mrq returned functions
    }());


    //The slides manager handles displaying how the app works
    mgrs.sld = (function () {
        const slides = [9200, 2800, 2200, 2800, 2800];
        const srcp = "docs/slideshow/slide$I.png";
        var idx = 0;
        var tmo = null;
    return {
        nextSlide: function (slideindex) {
            clearTimeout(tmo);
            const previdx = idx;
            if(slideindex >= 0) {
                idx = slideindex; }
            else {
                idx = (idx + 1) % slides.length; }
            jt.out("slidepgindspan", jt.tac2html(
                slides.map((ignore /*millis*/, i) =>
                    ["a", {href:"#slide" + i, onclick:mdfs("sld.nextSlide", i)},
                     ((i === idx)? "&#x2b24;" : "&#x25ef;")])));
            jt.byId("prevslide").src = srcp.replace(/\$I/g, previdx);
            const currslide = jt.byId("currslide");
            currslide.style.opacity = 0.0;
            setTimeout(function () {
                currslide.src = srcp.replace(/\$I/g, idx);
                currslide.style.opacity = 1.0; }, 500);  //match css transition
            if(slideindex >= 0 && tmo) { //pause on specific slide
                clearTimeout(tmo);
                tmo = null;
                return; }
            tmo = setTimeout(mgrs.sld.nextSlide, slides[idx]); },
        runSlideshow: function () {
            if(!jt.byId("slidesdiv")) { return; }
            jt.out("slidesdiv", jt.tac2html(
                [["div", {id:"slidepgdiv"},
                  ["span", {id:"slidepgindspan"}]],
                 ["div", {id:"slidedispdiv"},
                  [["img", {src:srcp.replace(/\$I/g, 0)}],
                   ["img", {id:"prevslide", src:srcp.replace(/\$I/g, 0)}],
                   ["img", {id:"currslide", src:srcp.replace(/\$I/g, 0)}]]]]));
            setTimeout(mgrs.sld.nextSlide, 12000); }
    };  //end mgrs.sld returned functions
    }());


    //The songfinder manager handles the song connect process
    mgrs.sgf = (function () {
    return {
        spotifyAvailability: function (song) {
            const ret = {svc:"Spotify", av:"no", links:[]};
            if(song.spid && song.spid.startsWith("z:")) {
                const du = "https://diggerhub.com/digger?songid=" + song.dsId;
                const su = "https://open.spotify.com/track/" +
                      song.spid.slice(2);
                ret.links = [{txt:"Digger", url:du}, {txt:"Track", url:su}];
                ret.av = "yes"; }
            return ret; },
        amazonAvailability: function (song) {
            const st = jt.enc(song.ti + " " + song.ar).replace(/%20/g, "+");
            const su = "https://www.amazon.com/s?k=" + st;
            return {svc:"Amazon", av:"maybe",
                    links:[{txt:"Search", url:su}]}; },
        youtubeAvailability: function (song) {
            const st = jt.enc(song.ti + " " + song.ar).replace(/%20/g, "+");
            const su = "https://music.youtube.com/search?q=" + st;
            return {
                svc:"YouTube", av:"maybe",
                links:[{txt:"Search", url:su}]}; },
        bandcampAvailability: function (song) {
            const st = jt.enc(song.ti + " " + song.ar).replace(/%20/g, "%2B");
            const su = "https://bandcamp.com/search?item_type&q=" + st;
            return {svc:"Bandcamp", av:"maybe",
                    links:[{txt:"Search", url:su}]}; },
        availabilityGlyph: function (av) {
            switch(av) {
            case "yes": return "&check;";
            case "no": return "x";
            default: return "?"; } },
        makeFindDisplay: function (song) {
            const savs = [{a:"Title", v:song.ti, s:"font-weight:bold;"},
                          {a:"Artist", v:song.ar, s:""},
                          {a:"Album", v:song.ab, s:"opacity:0.7;"}];
            const svcs = [mgrs.sgf.spotifyAvailability(song),
                          //tidal (no web player - no free access link)
                          //audible (owned by amazon, using amazon access)
                          //apple (music.apple.com - no free access link)
                          mgrs.sgf.youtubeAvailability(song),
                          mgrs.sgf.bandcampAvailability(song),
                          mgrs.sgf.amazonAvailability(song)];
            jt.out("sgfdiv", jt.tac2html(
                [["div", {id:"songfindertitlediv"}, "Song Finder"],
                 ["div", {id:"sgfsongiddiv"},
                  ["table", {id:"songavtable"},
                   savs.map((sav) =>
                       ["tr",
                        [["td", {cla:"sgfattr"}, sav.a],
                         ["td", {cla:"sgfval", style:sav.s}, sav.v]]])]],
                 ["div", {id:"sgfsvcsdiv"},
                  ["table", {id:"availtable"},
                   svcs.map((svc) =>
                       ["tr", {cla:"sgfsvcline"},
                        [["td", mgrs.sgf.availabilityGlyph(svc.av)],
                         ["td", ["div", {cla:"sgfsvcname"}, svc.svc]],
                         ["td", svc.links.map((link, i) =>
                             [(i? "&nbsp;&nbsp;&nbsp;" : ""),
                              ["a", {href:link.url,
                                     onclick:"window.open('" + link.url +
                                             "');return false"},
                               link.txt]])]]])]]])); },
        displayContent: function () {
            if(!authobj) {
                jt.out("sgfdiv", "Login required to use the song finder."); }
            else if(!app.startParams.songid) {
                jt.out("sgfdiv", "No songid specified"); }
            else {
                jt.out("sgfdiv", "Fetching Song " + app.startParams.songid);
                const dat = {an:authobj.email, at:authobj.token,
                             songid:app.startParams.songid};
                jt.call("POST", app.dr("/api/songtip"), jt.objdata(dat),
                        function (songs) {
                            mgrs.sgf.makeFindDisplay(songs[0]); },
                        function (code, errtxt) {
                            return jt.out("sgfdiv", "Fetch failed " +
                                          code + ": " + errtxt); },
                        jt.semaphore("sgf.songtip")); } },
        display: function () {
            jt.out("logodiv", "");  //clear overlay
            jt.out("outercontentdiv", jt.tac2html(
                ["div", {id:"sgfdiv"}]));
            mgrs.sgf.displayContent(); }
    };  //end mgrs.sgf returned functions
    }());


    //This works in conjunction with the static undecorated form created by
    //start.py, decorating to provide login without page reload.
    function initialize () {        
        app.svc.dispatch("gen", "initplat", "web");  //doc content retrieval
        Array.from(jt.byId("contactdiv").children).forEach(function (a) {
            jt.on(a, "click", function (event) {
                jt.evtend(event);
                app.displayDoc("hpgoverlaydiv", event.target.href); }); });
        switch(app.startPath) {
        case "/account": return mgrs.had.display();
        case "/songfinder": return mgrs.sgf.display();
        case "/digger": return app.initDiggerModules();
        default: jt.log("Standard site homepage display"); }
        mgrs.mrq.runMarquee();
        mgrs.sld.runSlideshow();
    }


return {
    init: function () { initialize(); },
    getAuth: function () { return authobj; },
    dispatch: function (mgrname, fname, ...args) {
        return mgrs[mgrname][fname].apply(app.login, args); }
};  //end of returned functions
}());
