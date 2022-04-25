/*global app, jt */
/*jslint browser, white, unordered */

app.login = (function () {
    "use strict";

    var initialTopActionHTML = "";  //initial form html kept for sign out
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
                jt.log("login.mgrs.ap.clear exception: " + e); } }
    };  //end mgrs.ap returned functions
    }());


    //The action manager handles signin/out and account updates
    mgrs.act = (function () {
        var authflds = ["an", "at", "email", "emailin", "passin"];
        function updateAuthObj (accntok) {
            authobj = app.refmgr.deserialize(accntok[0]);
            authobj.token = accntok[1];
            mgrs.ap.save(); }
    return {
        authContent: function () {
            switch(app.startPath) {
            case "/songfinder": mgrs.sgf.display(); break;
            case "/digger": app.initDiggerModules(); break;
            default: mgrs.spl.display(); } },
        successfulSignIn: function (result) {
            if(result) {
                updateAuthObj(result); }
            jt.out("acctmsglinediv", "");
            if(authflds.some((f) => app.startParams[f])) {
                //clear auth app params to avoid conflicts with auth changes
                authflds.forEach(function (a) { delete app.startParams[a]; });
                window.history.replaceState({}, document.title, "/"); }
            jt.out("topactiondiv", jt.tac2html(
                [["div", {id:"loginlinksdiv"},
                  [["a", {href:"#settings", title:"Account info and settings",
                          onclick:mdfs("act.accountInfoDisplay", true)},
                    authobj.firstname],
                   ["a", {href:"#signout", title:"Sign out and clear cookie",
                          onclick:mdfs("act.signOut")},
                    "Sign Out"]]],
                 ["div", {id:"tactdiv"}]]));
            mgrs.act.authContent(); },
        signOut: function () {
            mgrs.ap.clear();
            authobj = null;
            app.login.init(true); },
        accountInfoDisplay: function (toggle) {
            if(toggle && jt.byId("tactdiv").innerHTML) { //toggle off
                jt.out("tactdiv", "");
                return; }
            jt.out("tactdiv", jt.tac2html(
                [["div", {cla:"acctactdiv", id:"acctactivdiv"},
                  mgrs.act.acctActivHTML()],
                 ["div", {cla:"acctactdiv", id:"chgpwddiv"},
                  ["a", {href:"#ChgPwd", title:"Change your account password",
                         onclick:mdfs("act.changePasswordDisplay")},
                   "Change Password"]],
                 ["div", {cla:"forminline"},
                  [["label", {cla:"forminlab", fo:"firstnamein"}, "First Name"],
                   ["input", {type:"text", cla:"formin", id:"firstnamein",
                              value:authobj.firstname}]]],
                 ["div", {cla:"forminline"},
                  [["label", {cla:"forminlab", fo:"hashtagin"}, "Hashtag #"],
                   ["input", {type:"text", cla:"formin", id:"hashtagin",
                              value:authobj.hashtag}]]],
                 ["div", {id:"acctmsglinediv"}],
                 ["div", {cla:"formbuttonsdiv"},
                  ["button", {type:"button", id:"updaccb",
                              onclick:mdfs("act.updateAccountInfo")},
                   "Update Account"]]])); },
        updateAccount: function (data, contf, errf) {
            jt.call("POST", app.dr("/api/updacc"), data,
                    function (accntok) {
                        updateAuthObj(accntok);
                        contf(); },
                    errf,
                    jt.semaphore("login.act.updateAccount")); },
        updateAccountInfo: function () {
            var data = jt.objdata(
                {an:authobj.email, at:authobj.token,
                 firstname:jt.byId("firstnamein").value || "NOVAL",
                 hashtag:jt.byId("hashtagin").value || "NOVAL"});
            jt.byId("updaccb").disabled = true;
            mgrs.act.updateAccount(data, mgrs.act.successfulSignIn,
                function (code, errtxt) {
                    jt.byId("updaccb").disabled = false;
                    jt.out("acctmsglinediv", "Account update failed " +
                           code + ": " + errtxt); }); },
        noteUpdatedAccount: function (digacc) {
            digacc.token = authobj.token;
            authobj = digacc;
            return authobj; },
        changePasswordDisplay: function () {
            jt.out("tactdiv", jt.tac2html(
                [["div", {cla:"forminline"},
                  [["label", {cla:"forminlab", fo:"pwdin"}, "New Password"],
                   ["input", {type:"password", cla:"formin", id:"pwdin"}]]],
                 ["div", {id:"acctmsglinediv"}],
                 ["div", {cla:"formbuttonsdiv"},
                  ["button", {type:"button", id:"updaccb",
                              onclick:mdfs("act.changePassword")},
                  "Change Password"]]])); },
        changePassword: function () {
            //No need to change email. Just sign out of the local server
            //then sign in with a new account. Data preserved.
            jt.byId("updaccb").disabled = true;
            const data = jt.objdata(
                {an:authobj.email, at:authobj.token, updemail:authobj.email,
                 updpassword:jt.byId("pwdin").value});
            mgrs.act.updateAccount(data, mgrs.act.successfulSignIn,
                function (code, errtxt) {
                    jt.out("acctmsglinediv", "Password change failed " +
                           code + ": " + errtxt); }); },
        acctActivHTML: function () {
            if(authobj.status !== "Pending") { return ""; }
            return jt.tac2html(
                ["a", {href:"#sendactcode", 
                       title:"Email a link to activate this account",
                       onclick:mdfs("act.sendActivationCode")},
                 "Send Activation Code"]); },
        sendActivationCode: function () {
            jt.out("acctactivdiv", "Activation code sent");
            const data = jt.objdata({an:authobj.email, at:authobj.token});
            jt.call("POST", app.dr("/api/mailactcode"), data,
                    function () {
                        jt.log("Activation send completed successfully"); },
                    function (code, errtxt) {
                        jt.out("acctactivdiv", "Send failed " + code + ": " +
                               errtxt); },
                    jt.semaphore("login.act.sendActivationCode")); },
        createNewAccountDisplay: function () {
            var emv = jt.byId("emailin") || "";
            if(emv) { emv = emv.value || ""; }
            jt.out("topactiondiv", jt.tac2html(
                ["div", {id:"tactdiv"},
                 [["div", {cla:"forminline"},
                   [["label", {cla:"forminlab", fo:"emailin"}, "Email"],
                    ["input", {type:"email", cla:"formin", id:"emailin",
                               value:emv, placeholder:"nospam@example.com"}]]],
                  ["div", {cla:"forminline"},
                   [["label", {cla:"forminlab", fo:"passin"}, "Password"],
                    ["input", {type:"password", cla:"formin", id:"passin",
                               placeholder:"min 6 chars"}]]],
                  ["div", {cla:"forminline"},
                   [["label", {cla:"forminlab", fo:"firstin"}, "First Name"],
                    ["input", {type:"text", cla:"formin", id:"firstin",
                               placeholder:"How you like to be called"}]]],
                  ["div", {id:"acctmsglinediv"}],
                  ["div", {cla:"formbuttonsdiv"},
                   ["button", {type:"button", id:"newaccb",
                               onclick:mdfs("act.createAccount")},
                    "Join"]]]])); },
        createAccount: function () {
            jt.byId("newaccb").disabled = true;
            const data = jt.objdata(
                {email:jt.byId("emailin").value,
                 password:jt.byId("passin").value,
                 firstname:jt.byId("firstin").value});
            jt.call("POST", app.dr("/api/newacct"), data,
                    function (result) {
                        mgrs.act.successfulSignIn(result); },
                    function (code, errtxt) {
                        jt.byId("newaccb").disabled = false;
                        jt.out("acctmsglinediv", "Account creation failed " +
                               code + ": " + errtxt); },
                    jt.semaphore("login.act.createAccount")); },
        sendResetPasswordLink: function () {
            var emaddr = jt.byId("emailin").value;
            if(!jt.isProbablyEmail(emaddr)) {
                jt.out("acctmsglinediv", "Need email address to send to"); }
            jt.out("acctactivdiv", "Reset password link sent");
            const data = jt.objdata({email:emaddr});
            jt.call("POST", app.dr("/api/mailpwr"), data,
                    function () {
                        jt.out("acctmsglinediv", "Password reset sent."); },
                    function (code, errtxt) {
                        jt.out("acctactivdiv", "Send failed " + code + ": " +
                               errtxt); },
                    jt.semaphore("login.act.sendResetPasswordLink")); }
    };  //end mgrs.act returned functions
    }());


    //The splash manager handles default screen display functions
    mgrs.spl = (function () {
    return {
        activateFileOrStreamChoices: function () {
            var oc = "app.togdivdisp({rootids:['spchfile','spchstrm']," +
                                     "clicked:'CLICK'})";
            jt.out("fileorstreamchoicediv", jt.tac2html(
                [["a", {href:"#files",
                        onclick:oc.replace("CLICK", "spchfile")},
                  ["span", {id:"tcgcspchfile", cla:"spchspan"},
                   "Files"]],
                 "&nbsp", "or", "&nbsp",
                 ["a", {href:"#streaming",
                        onclick:oc.replace("CLICK", "spchstrm")},
                  ["span", {id:"tcgcspchstrm", cla:"spchspan"},
                   "Streaming"]]]));
            if(window.location.href.endsWith("#files")) {
                app.togdivdisp({rootids:["spchfile","spchstrm"],
                                clicked:"spchfile"}, "block"); }
            if(window.location.href.endsWith("#streaming")) {
                app.togdivdisp({rootids:["spchfile","spchstrm"],
                                clicked:"spchstrm"}, "block"); } },
        verifySignedIn: function (event) {
            if(!authobj) {
                jt.out("loginreqdiv", "Sign in to launch Digger");
                jt.evtend(event); }
            else {
                jt.out("loginreqdiv", "Starting Digger..."); } },
        activateDiggerLaunchLinks: function () {
            const links = document.getElementsByClassName("diggerlaunchlink");
            Array.prototype.forEach.call(links, function (link) {
                jt.on(link, "click", mgrs.spl.verifySignedIn); });
            jt.out("loginreqdiv", ""); },
        decorateSplashContents: function () {
            mgrs.spl.activateFileOrStreamChoices();
            mgrs.spl.activateDiggerLaunchLinks(); },
        display: function () {
            mgrs.spl.decorateSplashContents();
            mgrs.mrq.runMarquee();
            mgrs.sld.runSlideshow(); }
    };  //end mgrs.spl returned functions
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
        const slides = [8200, 2800, 2200, 2800, 2800];
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


    function signIn () {
        jt.out("acctmsglinediv", "");  //clear any previous login error
        const sav = mgrs.ap.read() || {};
        const ps = {an:app.startParams.an || sav.authname || "",
                    at:app.startParams.at || sav.authtoken || "",
                    emailin:jt.safeget("emailin", "value") || "",
                    passin:jt.safeget("passin", "value") || "",
                    actcode:app.startParams.actcode || ""};
        if(ps.emailin && !(ps.at || ps.passin)) {
            jt.byId("passin").focus();
            return mgrs.act.authContent(); }
        if(!((ps.an || ps.emailin) && (ps.at || ps.passin))) {
            jt.byId("emailin").focus();
            return mgrs.act.authContent(); } //not trying to sign in or activate
        jt.out("acctmsglinediv", "Signing in...");
        jt.byId("topsectiondiv").style.cursor = "wait";
        //URL parameters cleared after sign in
        jt.call("POST", app.dr("/api/acctok"), jt.objdata(ps),
                function (result) {
                    jt.byId("topsectiondiv").style.cursor = "default";
                    mgrs.act.successfulSignIn(result); },
                function (code, errtxt) {
                    jt.byId("topsectiondiv").style.cursor = "default";
                    jt.log("authentication failure " + code + ": " + errtxt);
                    jt.out("acctmsglinediv", errtxt);
                    mgrs.act.authContent(); },
                jt.semaphore("login.signIn"));
    }


    function writeSupportContact () {
        var bot = "@diggerhub.com";
        var repls = [
            {p:"ISSUESONGITHUB", h:"https://github.com/theriex/digger/issues",
             t:"issues on GitHub"},
            {p:"SUPPORTEMAIL", h:"mailto:support" + bot, t:"support" + bot},
            {p:"EPINOVA", h:"https://epinova.com", t:"epinova.com"}];
        var html = jt.byId("suppdiv").innerHTML;
        repls.forEach(function (r) {
            var link = "<a href=\"" + r.h + "\"";
            if(r.h.startsWith("https")) {
                link += " onclick=\"window.open('" + r.h + "')" + 
                    ";return false\""; }
            link += ">" + r.t + "</a>"
            html = html.replace(r.p, link); });
        jt.out("suppdiv", html);
    }


    //This works in conjunction with the static undecorated form created by
    //start.py, decorating to provide login without page reload.
    function initialize (restore) {
        if(initialTopActionHTML && !restore) {
            return; }  //form setup and initial signIn already done.
        if(!initialTopActionHTML) {  //save so it can be restored on logout
            initialTopActionHTML = jt.byId("topactiondiv").innerHTML; }
        if(restore) {
            jt.out("topactiondiv", initialTopActionHTML); }
        jt.out("loginlinksdiv", jt.tac2html(
            [["a", {href:"#newaccount", title:"Create a DiggerHub account",
                    onclick:mdfs("act.createNewAccountDisplay")},
              "join"],
             ["a", {href:"#resetpassword", title:"Email a password reset link",
                    onclick:mdfs("act.sendResetPasswordLink")},
              "reset password"]]));
        jt.on("loginform", "submit", app.login.formSubmit);
        setTimeout(writeSupportContact, 5000);
        signIn();  //attempt to sign in with cookie then update content
    }


return {
    init: function (restore, contf) { initialize(restore, contf); },
    formSubmit: function (event) { jt.evtend(event); signIn(); },
    getAuth: function () { return authobj; },
    dispatch: function (mgrname, fname, ...args) {
        return mgrs[mgrname][fname].apply(app.login, args); }
};  //end of returned functions
}());
