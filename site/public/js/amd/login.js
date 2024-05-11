/*global app, jt */
/*jslint browser, white, unordered, long */

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
        if(!pstr.startsWith(",event")) {  //don't return false from event hooks
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
        save: function (updauth) {
            if(updauth) {
                authobj = updauth; }
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
            jt.call("POST", app.dr("/api/acctok"), jt.objdata(ps),
                    contf, errf); }
    };  //end mgrs.ap returned functions
    }());


    //The hub account manager handles account actions from the hub page.
    mgrs.hua = (function () {
        const haid = "hubaccountcontentdiv";
        function initialSignIn (contf, errf) {
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
                errf(403, "No authentication parameters given"); } }
    return {
        signOut: function () {
            authobj = null;
            mgrs.ap.clear();
            setTimeout(function () {
                app.top.dispatch("afg", "accountFanGroup", "offline", 1); },
                       400); },
        initDisplay: function (dispdiv) {
            dispdiv = dispdiv || haid;
            if(!jt.byId(dispdiv)) { return; }  //no account access
            app.top.dispatch("afg", "runOutsideApp", dispdiv);
            initialSignIn(
                function (accntok) {
                    app.top.dispatch("hcu", "deserializeAccount", accntok[0]);
                    app.top.dispatch("aaa", "reflectAccountChangeInRuntime",
                                     accntok[0], accntok[1]);
                    authobj = app.top.dispatch("aaa", "getAccount");
                    mgrs.ap.save();
                    app.top.dispatch("afg", "accountFanGroup", "groups", 2); },
                function () {  //not signed in
                    app.top.dispatch("afg", "accountFanGroup");
                    if(jt.byId("newacctb")) { //switch to sign in form to start
                        app.top.dispatch("afg", "accountFanGroup",
                                         "offline", 1); } }); }
    };  //end mgrs.hua returned functions
    }());



    //The hub account display manager handles account access outside of the
    //app and outside of the main hub page.  Essentially an independent
    //account management interface page.
    mgrs.had = (function () {
    return {
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
            mgrs.hua.initDisplay("haddiv"); }
    };  //end mgrs.had returned functions
    }());


    //The hub sign in manager handles account sign in or join.  Takes a div
    //id for form display and calls back with the account.
    mgrs.hsi = (function () {
        var context = null;
        function getAccount (ao, errf) {
            jt.call("POST", app.dr("/api/acctok"), jt.objdata(ao),
                function (accntok) {
                    app.top.dispatch("hcu", "deserializeAccount", accntok[0]);
                    app.top.dispatch("aaa", "reflectAccountChangeInRuntime",
                                     accntok[0], accntok[1]);
                    authobj = app.top.dispatch("aaa", "getAccount");
                    mgrs.ap.save();
                    context.cbf(authobj); },
                errf); }
        function acctFromForm () {
            app.top.dispatch("afg", "runOutsideApp", context.divid,
                             context.cbf);
            app.top.dispatch("afg", "accountFanGroup", "offline", 1); }
        function acctFromCookie () {
            const cookauth = mgrs.ap.read();
            if(cookauth) {
                getAccount({an:cookauth.authname, at:cookauth.authtoken},
                           acctFromForm); }
            else {
                acctFromForm(); } }
        function acctFromParameters() {
            if(app.startParams.an && app.startParams.at) {
                getAccount({an:app.startParams.an, at:app.startParams.at},
                           acctFromCookie); }
            else {
                acctFromCookie(); } }
    return {
        signIn: function (formDispId, callbackfunc) {
            var acct = app.top.dispatch("aaa", "getAccount");
            if(acct) {
                return callbackfunc(acct); }
            context = {divid:formDispId, cbf:callbackfunc};
            acctFromParameters(); }
    };  //end mgrs.hsi returned functions
    }());


    //The beta test questions manager handles defined survey questions.
    mgrs.btq = (function () {
        const sdefs = {
            pretest:[
                {q:"Which platform will you be testing with?",
                 id:"whichplat", qtype:"radio", sel:["iOS", "Android"]},
                {q:"How many albums do you own?",
                 id:"ttlab", qtype:"radio",
                 sel:["Only a few", "Several", "Hundreds"]},
                {q:"How would you describe the music you have?",
                 id:"varmus", qtype:"radio",
                 sel:["Varied", "Mostly similar genre"]},
                {q:"How many albums have you purchased in the past year?",
                 id:"ablastyr", qtype:"range",
                 sel:["0", "1", "2-5", "6-9", "10+"]},
                {q:"How many times have you seen live music in the past year?",
                 id:"livelastyr", qtype:"range",
                 sel:["0", "1", "2-5", "6-9", "10+"]},
                {q:"Name for USPS delivery:", id:"uspsname", qtype:"text"},
                {q:"Street address, city, state, zip:", id:"uspsaddr",
                 qtype:"text"}],
            aftertest:[
                {q:"What was the first listening situation you filtered for?",
                 id:"firstlisten", qtype:"text"},
                {q:"What was the second listening situation you tried?",
                 id:"secondlisten", qtype:"text"},
                {q:"Was anything bad about your Digger experience?",
                 id:"badstuff", qtype:"longtext"},
                {q:"What was good about your Digger experience?",
                 id:"goodstuff", qtype:"longtext"},
                {q:"How likely are you to use Digger in the future?",
                 id:"usefut", qtype:"range", 
                 sel:["Never", "", "", "Don't Know", "", "", "Definitely"]},
                {q:"Would you recommend Digger to others?",
                 id:"recommend", qtype:"range",
                 sel:["Never", "", "", "Unsure", "", "", "Definitely"]},
                {q:"Would you be willing to contacted in the future?",
                 id:"contact", qtype:"radio", sel:["No", "Yes"]}]};
        const rend = {
            radio:function (qas, qid, sel) {
                return jt.tac2html(
                    ["div", {cla:"btqradiocontdiv"},
                     sel.map((v) =>
                         ["div", {cla:"radiobdiv"},
                          [["input", {type:"radio", id:qid + v + "RadioButton",
                                      name:qid + "Radios", value:v,
                                      checked:jt.toru(qas[qid] === v),
                                      onclick:mdfs("btq.setAnswer", "event",
                                                   "radio", qid, v)}],
                           ["label", {fo:qid + v + "RadioButton"}, v]]])]); },
            range:function (qas, qid, sel) {
                return jt.tac2html(
                    ["div", {cla:"btqrangecontdiv"},
                     sel.map((v, idx) =>
                         ["div", {cla:"btqrangecelldiv"},
                          [["div", ["label", {fo:qid + v + "RadioButton"}, v]],
                           ["input", {type:"radio", id:qid + v + "RadioButton",
                                      name:qid + "Radios", value:idx,
                                      checked:jt.toru(qas[qid] === idx),
                                      onclick:mdfs("btq.setAnswer", "event",
                                                   "range", qid, idx)}]]])]); },
            text:function (qas, qid) {
                return jt.tac2html(
                    ["input", {type:"text", value:qas[qid] || "", size:28,
                               id:qid + "txtin",
                               oninput:mdfs("btq.setAnswer", "event",
                                            "text", qid)}]); },
            longtext:function (qas, qid) {
                return jt.tac2html(
                    ["textarea", {id:qid + "ta", rows:5, cols:40,
                                  oninput:mdfs("btq.setAnswer", "event",
                                               "longtext", qid)},
                     qas[qid] || ""]); } };
        const qtexttypes = ["text", "longtext"];
        var ctx = null;
        function findUnanswered (tdef, stint) {
            const qas = stint.stdat[tdef] || {};
            const noval = sdefs[tdef].find((q) =>
                ((qtexttypes.includes(q.qtype) && !qas[q.id]) ||
                 (qas[q.id] === undefined)));
            return noval; }
    return {
        setAnswer: function (ignore /*event*/, qtype, qid, val) {
            if(qtexttypes.includes(qtype)) {
                val = jt.byId(qid + "txtin").value; }
            jt.out(qid + "qerrdiv", "");
            ctx.stint.stdat[ctx.tdef][qid] = val; },
        checkAnswers: function () {
            sdefs[ctx.tdef].forEach(function (q) {  //clear any prev errmsgs
                jt.out(q.id + "qerrdiv", ""); });
            const noval = findUnanswered(ctx.tdef, ctx.stint);
            if(noval) {
                jt.out(noval.id + "qerrdiv", "Please answer this question");
                return; }
            ctx.cbf(); },
        completed: function (tdef, stint) {
            return !findUnanswered(tdef, stint); },
        survey: function (testdef, divid, respstint, donefunc) {
            ctx = {tdef:testdef, tdiv:divid, stint:respstint, cbf:donefunc};
            if(mgrs.btq.completed(ctx.tdef, ctx.stint)) {
                return ctx.cbf(); }
            ctx.stint.stdat[ctx.tdef] = ctx.stint.stdat[ctx.tdef] || {};
            const qas = ctx.stint.stdat[ctx.tdef];
            jt.out(ctx.tdiv, jt.tac2html(
                [sdefs[ctx.tdef].map((q) =>
                    ["div", {id:q.id + "contdiv", cla:"btqcontdiv"},
                     [["div", {id:q.id + "qtdiv", cla:"btqtdiv"}, q.q],
                      ["div", {id:q.id + "qerrdiv", cla:"btqerrdiv"}],
                      ["div", {id:q.id + "qadiv", cla:"btqadiv"},
                       rend[q.qtype](qas, q.id, q.sel)]]]),
                 ["div", {cla:"dlgbuttonsdiv"},
                  ["button", {type:"button", onclick:mdfs("btq.checkAnswers")},
                    "Continue"]]])); }
    };  //end mgrs.btq returned functions
    }());


    //The beta test program display manager handles a beta testing process
    mgrs.btp = (function () {
        const bprgnm = "beta1";
        const progmax = 10;
        const btpdivs = ["btphellodiv", "btpnavdiv", "btpdetdiv", "btpcpdiv"];
        const statvs = ["Pending", "Active", "Complete"];
        var stat = null;   //beta test program general status
        var acct = null;   //tester DigAcc
        var stint = null;  //step interaction info for tester
        var cnts = null;   //song rating counts for tester
        function callstat (txt) { jt.out("btpcpdiv", txt); }
        function errf (code, errtxt) { jt.out("btpcpdiv", "Call failed code " +
                                              code + ": " + errtxt); }
        function over50 (cnt) {
            if(cnt > 50) { return "over 50"; }
            return String(cnt); }
        const steps = {
            intro:{
                cmp:function () {
                    return (stat && acct && stint); },
                display:function () {
                    jt.out("btpnavdiv", "To participate, you must have at least 50 songs on an Android or iOS device that you will record your impressions of while you listen with Digger.  After recording your impressions, you will try filtered autoplay in at least two different listening situations and provide feedback.");
                    jt.out("btpdetdiv", jt.tac2html(
                        [["p", {id:"btpirwrdp"}, "Your testing of Digger is vital, and as a small gesture of thanks you will be sent a $50 gift card for either Bandcamp or Amazon, whichever you prefer.  If you want, you will also have the opportunity to be directly involved in the Digger project, including new feature development."],
                         ["div", {id:"btpixdiv"}]]));
                    if(!stat) {
                        callstat("Checking beta test program status...");
                        const url = app.cb("api/betastat", {sitype:bprgnm});
                        return jt.call("GET", url, null,
                            function (statrets) {
                                callstat("");
                                stat = statrets[0];
                                if(stat.active + stat.complete > progmax) {
                                    jt.out("btpirwrdp", "This beta testing round is now full and all gift cards are spoken for.  If you would like to sign up as a beta tester anyway, that would be immensely appreciated. If there's more budget in the future you'll get advanced notice."); }
                                mgrs.btp.dispCurrStep(); },
                            errf); }
                    if(!acct) {
                        const siid = "hubaccountcontentdiv";  //like main page
                        jt.out("btpixdiv", jt.tac2html(
                            ["div", {id:"hubacctdiv"},
                             [["p", "To continue, sign in."],
                              ["div", {id:siid, cla:"boxedcontentdiv"}]]]));
                        return mgrs.hsi.signIn(siid, function (siacc) {
                            acct = siacc;
                            mgrs.btp.dispCurrStep(); }); }
                    if(!stint) {
                        jt.out("btpixdiv", "");
                        callstat("Fetching your testing info...");
                        const data = jt.objdata(
                            {an:acct.email, at:acct.token, sitype:bprgnm,
                             confcode:app.startParams.confcode});
                        return jt.call("POST", app.dr("/api/betastat"), data,
                            function (stints) {
                                callstat("");
                                stint = stints[0];
                                stint.stdat = stint.stdat || "{}";
                                stint.stdat = JSON.parse(stint.stdat);
                                mgrs.btp.dispCurrStep(); },
                            errf); } } },
            emconf:{  //stint came back without confirmation code
                cmp:function () {
                    return (statvs.slice(1).indexOf(stint.status) >= 0); },
                display:function () {
                    jt.out("btpnavdiv", "Beta testing is expected to take a couple of days, and must be completed within 3 weeks of starting.  To receive a gift card, you will need to provide a non-forwarded U.S. physical address (limit one per household).  To confirm your email and get started, request your beta test invite:");
                    jt.out("btpdetdiv", jt.tac2html(
                        ["a", {href:"#sendInvite",
                               onclick:mdfs("btp.sendInvite")},
                         "Send Invitation"])); } },
            survey:{
                cmp:function () {
                    return mgrs.btq.completed("pretest", stint); },
                display:function () {
                    jt.out("btpnavdiv", "Beta Test Setup Questions");
                    mgrs.btq.survey("pretest", "btpdetdiv", stint,
                                    mgrs.btp.saveStep); } },
            rating:{
                cmp:function () {
                    return (cnts && cnts.ttl >= 50 && cnts.mto >= 4); },
                display:function () {
                    jt.out("btpnavdiv", "Looking forward to listening with Digger! If you have not already installed the " + stint.stdat.pretest.whichplat + " app, click the download link on <a href=\"https:diggerhub.com\">diggerhub</a> to request a promo code.  Thanks for testing!");
                    if(cnts) {
                        jt.out("btpnavdiv", "So far you've described " + over50(cnts.ttl) + "songs from your collection and listened to " + over50(cnts.mto) + " more than once.  After you've listened to at least 50 songs, try autoplay in a couple of different listening situations then come back to this page to complete your beta test.  Thanks for testing!"); }
                    jt.out("btpdetdiv", jt.tac2html(
                        ["a", {href:"#refreshCounts",
                               onclick:mdfs("btp.refreshSongCounts")},
                         "Refresh Song counts"]));
                    if(!cnts) {
                        mgrs.btp.refreshSongCounts(); } } },
            response:{
                cmp:function () {
                    return mgrs.btq.completed("aftertest", stint); },
                display:function () {
                    jt.out("btpnavdiv", "Beta Test Finishing Questions");
                    mgrs.btq.survey("aftertest", "btpdetdiv", stint,
                                    mgrs.btp.saveStep); }},
            thanks:{} };
        function updateCountsFromSongs (fetchedSongs) {
            cnts = {ttl:0, mto:0, songs:fetchedSongs};
            cnts.songs.forEach(function (s) {
                cnts.ttl += 1;
                const mod = parseInt(s.modified.split(";")[1]);
                if(mod > 1) {
                    cnts.mto += 1; } }); }
        function helloLineHTML () {
            const gw = "Thanks for your interest in the Digger Beta Testing Program!";
            const sw = "Welcome back $DIGNAME!";
            if(acct) {
                return sw.replace(/\$DIGNAME/g, acct.firstname); }
            return gw; }
    return {
        refreshSongCounts: function () {
            jt.out("btpdetdiv", "");
            callstat("Refreshing song counts...");
            const data = jt.objdata(
                {an:acct.email, at:acct.token, sitype:bprgnm,
                 action:"songCounts", platform:stint.stdat.pretest.whichplat});
            jt.call("POST", app.dr("/api/betastat"), data,
                function (songs) {
                    callstat("");
                    updateCountsFromSongs(songs);
                    mgrs.btp.dispCurrStep(); },
                errf); },
        sendInvite: function () {
            jt.out("btpdetdiv", "Sending...");
            const data = jt.objdata(
                {an:acct.email, at:acct.token, sitype:bprgnm,
                 action:"sendInvite"});  //text and auth server side
            jt.call("POST", app.dr("/api/betastat"), data,
                function () {
                    jt.out("btpdetdiv",
                           "Invitation sent, check your email."); },
                errf); },
        saveStep: function () {  //stint already updated by caller
            callstat("Saving beta test progress...");
            const data = jt.objdata(
                {an:acct.email, at:acct.token, sitype:bprgnm,
                 action:"save", stdat:JSON.stringify(stint.stdat)});
            jt.call("POST", app.dr("/api/betastat"), data,
                function (stints) {
                    stint = stints[0];
                    stint.stdat = JSON.parse(stint.stdat);
                    callstat("");
                    mgrs.btp.dispCurrStep(); },
                errf); },
        dispCurrStep: function () {
            var step = Object.keys(steps).find((st) => !steps[st].cmp());
            btpdivs.forEach(function (id) { jt.out(id, ""); });
            jt.out("btphellodiv", helloLineHTML());
            steps[step].display(); },
        display: function () {
            window.history.replaceState({}, document.title, "/beta");
            jt.out("sitecontentdiv", jt.tac2html(
                [["div", {id:"logodiv"},
                  ["a", {href:"/"},
                   ["img", {src:"img/appicon.png"}]]],
                 ["div", {id:"btptitlediv"}, "Digger Beta Test"],
                 ["div", {id:"btpcontentdiv"},
                  btpdivs.map((d) => ["div", {id:d}])]]));
            mgrs.btp.dispCurrStep(); }
    };  //end mgrs.btp returned function
    }());


    //The marketing message display manager handles special case displays
    //like promo code redemption.
    mgrs.mmd = (function () {
        function displayContent (html) {
            const contactdiv = jt.byId("contactdiv");
            if(contactdiv) {
                contactdiv.style.display = "none"; }
            jt.out("sitecontentdiv", jt.tac2html(
                [["div", {id:"logodiv"},
                  ["a", {href:"/"},
                   ["img", {src:"img/appicon.png"}]]],
                 ["div", {id:"mmdcontentdiv"},
                  html]])); }
    return {
        iosappstore: function () {
            window.history.replaceState({}, document.title, "/iosappstore");
            if(!app.startParams.code) {
                return displayContent("No App Store code given. Check the link from the email you received."); }
            displayContent(jt.tac2html(
                ["div", {id:"iosappstorediv"},
                 ["To redeem your App Store code for Digger:",
                  ["ol", {cla:"mktmsglist"},
                   [["li", "Open your profile in the App Store"],
                    ["li", "Select \"Redeem Gift Card or Code\""],
                    ["li", "Use your camera to read the boxed code below:"]]],
                  ["div", {cla:"appstorecodebox"},
                   app.startParams.code]]])); }
    };  //end mgrs.mmd returned functions
    }());


    //The download manager handles any extra steps related to downloading
    //the app.
    mgrs.dld = (function () {
        const posdiv = "downloadsdiv";
        const dispdiv = "dloverlaydiv";
        const templates = {
            iosp: "ipem(Request a promotional code) to evaluate Digger at no cost, or help support ongoing development and link(buy Digger for iOS).",
            droidp: "Request a dpem(promotional link) to evaluate Digger at no cost, or help support ongoing development and link(buy Digger for Android).",
            webapp: "Access Digger with any browser while the local Digger server is running. See the $webappdoc description page for details. link(Download Digger)" };
        function iosPromoEmailLink () {
            const emaddr = app.subPlaceholders(null, null, "SUPPEMAIL");
            const subj = "Digger for iOS promo code";
            const body = "Hi,\n\nI'd like to help evaluate Digger for iOS. Please send me a promotional code to get Digger at no cost from the App Store.\n\nThanks,\n";
            const link = "mailto:" + emaddr + "?subject=" + jt.dquotenc(subj) +
                  "&body=" + jt.dquotenc(body);
            return link; }
        function droidPromoEmailLink () {
            const emaddr = app.subPlaceholders(null, null, "SUPPEMAIL");
            const subj = "Digger for Android promo code";
            const body = "Hi,\n\nPI'd like to help evaluate Digger for Android. Please send me a promotional link to get Digger at no cost from Google Play.\n\nThanks,\n";
            const link = "mailto:" + emaddr + "?subject=" + jt.dquotenc(subj) +
                  "&body=" + jt.dquotenc(body);
            return link; }
        function displayOverlay (tid, targ) {
            var txt = templates[tid];
            txt = txt.replace(/link\(([^)]*)\)/, function (ignore, linkt) {
                return jt.tac2html(
                    ["a", {href:targ,
                           onclick:"window.open('" + targ + "');return false"},
                     ["span", {cla:"downloadlinkspan"}, linkt]]); });
            txt = txt.replace(/dpem\(([^)]*)\)/, function (ignore, linkt) {
                return jt.tac2html(
                    ["a", {href:droidPromoEmailLink()}, linkt]); });
            txt = txt.replace(/ipem\(([^)]*)\)/, function (ignore, linkt) {
                return jt.tac2html(
                    ["a", {href:iosPromoEmailLink()}, linkt]); });
            const wdu = "docs/websrvapp.html";
            txt = txt.replace("$webappdoc", jt.tac2html(
                ["a", {href:wdu, 
                       onclick:"window.open('" + wdu + "');return false"},
                 "Webserver App"]));
            txt = jt.tac2html(
                ["div", {id:"dlovrcontdiv"},
                 [["div", {id:"dloverxdiv"},
                   ["a", {href:"#close",
                          onclick:jt.fs("app.login.closeDLOver()")}, "X"]],
                  ["div", {id:"dlovertxtdiv"}, txt]]]);
            const pos = jt.geoPos(jt.byId(posdiv));
            const dd = jt.byId(dispdiv);
            dd.style.display = "block";
            dd.style.left = pos.x + "px";
            dd.style.top = pos.y + "px";
            dd.style.height = pos.h + "px";
            dd.style.width = pos.w + "px";
            jt.out(dispdiv, txt); }
    return {
        closeOverlay: function () {
            jt.out(dispdiv, "");
            jt.byId(dispdiv).style.display = "none"; },
        detail: function (event) {
            if(event && event.target && event.target.href) {
                if(event.target.href.includes("apple")) {
                    displayOverlay("iosp", event.target,
                                   iosPromoEmailLink()); }
                else if(event.target.href.includes("play.google")) {
                    displayOverlay("droidp", event.target,
                                   droidPromoEmailLink()); }
                else { //webapp
                    displayOverlay("webapp", event.target); } }
            return false; }
    };  //end mgrs.dld returned functions
    }());


    //The marquee manager handles headline text in the default display
    mgrs.mrq = (function () {
        const mst = {  //marguee settings
            fis:0.3,   //fade-in seconds
            fos:1.2,   //fade-out seconds
            dts:8};    //text display time seconds
        const mhds = [
            "Autoplay your music collection",
            "Buy an album this week",
            "Record your impressions",
            "Connect to DiggerHub with the app"];
        var idx = 0;
    return {
        nextStatement: function () {
            const md = jt.byId("marqueediv");
            if(!md) { return; }
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
            if(!jt.byId("headertextdiv")) { return; }  //no space to run in
            jt.out("headertextdiv", jt.tac2html(
                ["div", {id:"marqueediv"}, "&nbsp;"]));
            mgrs.mrq.nextStatement(); }
    };  //end mgrs.mrq returned functions
    }());


    //The slides manager handles displaying how the app works
    mgrs.sld = (function () {
        const slides = [8000, 5200, 2200, 4800, 2800];
        const srcp = "docs/slideshow/slide$I.png";
        var idx = 0;
        var tmo = null;
    return {
        nextSlide: function (slideindex) {
            var waitdur = 8000;
            clearTimeout(tmo);
            const previdx = idx;
            if(slideindex >= 0) {
                idx = slideindex; }
            else {
                idx = (idx + 1) % slides.length;
                waitdur = slides[idx]; }
            jt.out("slidepgindspan", jt.tac2html(
                slides.map((ignore /*millis*/, i) =>
                    ["a", {href:"#slide" + i, onclick:mdfs("sld.nextSlide", i)},
                     ["img", {cla:((i === idx)? "sldselimg" : "sldimg"),
                              src:srcp.replace(/\$I/g, i)}]])));
            jt.byId("prevslide").src = srcp.replace(/\$I/g, previdx);
            const currslide = jt.byId("currslide");
            currslide.style.opacity = 0.0;
            setTimeout(function () {
                currslide.src = srcp.replace(/\$I/g, idx);
                currslide.style.opacity = 1.0; }, 500);  //match css transition
            if(slideindex >= 0 && tmo) { //pause on specific slide
                clearTimeout(tmo);
                tmo = null; }
            tmo = setTimeout(mgrs.sld.nextSlide, waitdur); },
        runSlideshow: function () {
            if(!jt.byId("slidesdiv")) { return; }
            jt.out("slidesdiv", jt.tac2html(
                [["div", {id:"slidepgdiv"},
                  ["span", {id:"slidepgindspan"}]],
                 ["div", {id:"slidedispdiv"},
                  [["img", {src:srcp.replace(/\$I/g, 0)}],  //use space
                   ["img", {id:"prevslide", src:srcp.replace(/\$I/g, 0)}],
                   ["img", {id:"currslide", src:srcp.replace(/\$I/g, 0)}]]]]));
            mgrs.sld.nextSlide(0); }
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


    //The general manager handles top level page setup and actions
    mgrs.gen = (function () {
        function adjustReportDisplay () {
            const ricd = jt.byId("reportinnercontentdiv");
            if(ricd && ricd.offsetWidth > 600) {
                ricd.style.display = "table";
                ricd.style.margin = "0px auto"; } }
    return {
        initialize: function () {
            app.svc.dispatch("gen", "initplat", "web");  //doc content retrieval
            const contactdiv = jt.byId("contactdiv");
            if(contactdiv) {
                Array.from(contactdiv.children).forEach(function (a) {
                    jt.on(a, "click", function (event) {
                        jt.evtend(event);
                        const sd = jt.byId("docdispxdiv");
                        if(sd) {
                            sd.scrollIntoView(); }
                        app.displayDoc("hpgoverlaydiv",
                                       event.target.href); }); }); }
            app.overlaydiv = "hpgoverlaydiv";
            if(app.startPath.startsWith("/plink") ||
               app.startPath.startsWith("/listener")) {
                return adjustReportDisplay(); }
            switch(app.startPath) {
            case "/iosappstore": return mgrs.mmd.iosappstore();
            case "/account": return mgrs.had.display();
            case "/beta": return mgrs.btp.display();
            case "/songfinder": return mgrs.sgf.display();
            case "/digger": return app.initDiggerModules();
            default: jt.log("Standard site homepage display"); }
            mgrs.hua.initDisplay();
            //setTimeout(mgrs.mrq.runMarquee, 12000);
            mgrs.sld.runSlideshow(); },
        scrollToTopOfContent: function () {
            const div = jt.byId("sitecontentdiv");
            div.scrollTo({top:0, left:0, behavior:"smooth"}); }
    };  //end mgrs.gen returned functions
    }());


return {
    init: function () { mgrs.gen.initialize(); },
    getAuth: function () { return authobj; },
    dldet: function (event) { return mgrs.dld.detail(event); },
    closeDLOver: function () { return mgrs.dld.closeOverlay(); },
    scrollToTopOfContent: function () { mgrs.gen.scrollToTopOfContent(); },
    dispatch: function (mgrname, fname, ...args) {
        return mgrs[mgrname][fname].apply(app.login, args); }
};  //end of returned functions
}());
