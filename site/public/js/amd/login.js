/*global app, jt */
/*jslint browser, white, fudge */

app.login = (function () {
    "use strict";

    var initialTopActionHTML = "";  //initial form html kept for sign out
    var authobj = null;  //basically the DigAcc, but may skip some fields


    //manager dispatch function string - shorthand for event defs
    function mdfs (mgrfname, ...args) {
        var pstr = app.paramstr(args);
        mgrfname = mgrfname.split(".");
        var fstr = "app.login.managerDispatch('" + mgrfname[0] + "','" +
            mgrfname[1] + "'" + pstr + ")";
        if(pstr !== ",event") {  //don't return false from event hooks
            fstr = jt.fs(fstr); }
        return fstr;
    }


    //General container for all managers, used for dispatch
    var mgrs = {};


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
                jt.log("mgrs.ap.save success");
            } catch (e) {
                jt.log("mgrs.ap.save exception: " + e); } },
        read: function () {
            var ret = null;
            try {
                ret = jt.cookie(sname);  //ret null if not found
                if(ret) {
                    if(ret.indexOf(delim) < 0) {
                        jt.log("mgrs.ap.read clearing " + ret + ": " +
                               delim + " delimiter not found.");
                        mgrs.ap.clear();
                        ret = null; }
                    else {
                        ret = ret.split(delim);
                        ret[0] = ret[0].replace("%40", "@");
                        if(!jt.isProbablyEmail(ret[0]) || ret[1].length < 20) {
                            jt.log("mgrs.ap.read clearing bad values: " +
                                   ret[0] + ", " + ret[1]);
                            mgrs.ap.clear();
                            ret = null; }
                        else {
                            jt.log("mgrs.ap.read success");
                            ret = {authname:ret[0], authtoken:ret[1]}; } } }
            } catch (e) {
                jt.log("mgrs.ap.read exception: " + e);
                ret = null;
            }
            return ret; },
        clear: function () {
            try {
                jt.cookie(sname, "", -1);
            } catch (e) {
                jt.log("mgrs.ap.clear exception: " + e); } }
    };  //end mgrs.ap returned functions
    }());


    mgrs.act = (function () {
        var authflds = ["an", "at", "email", "emailin", "passin"];
    return {
        updateAuthObjFromResult: function (accntok) {
            authobj = app.refmgr.deserialize(accntok[0]);
            authobj.token = accntok[1];
            mgrs.ap.save(); },
        successfulSignIn: function (result) {
            mgrs.act.updateAuthObjFromResult(result);
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
                 ["div", {id:"tactdiv"}]])); },
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
        updateAccountInfo: function () {
            jt.byId("updaccb").disabled = true;
            var data = jt.objdata(
                {an:authobj.email, at:authobj.token,
                 firstname:jt.byId("firstnamein").value || "NOVAL",
                 hashtag:jt.byId("hashtagin").value || "NOVAL"});
            jt.call("POST", app.dr("/api/updacc"), data,
                    function (result) {
                        mgrs.act.successfulSignIn(result); },
                    function (code, errtxt) {
                        jt.byId("updaccb").disabled = false;
                        jt.out("acctmsglinediv", "Account update failed " +
                               code + ": " + errtxt); },
                    jt.semaphore("login.act.updateAccountInfo")); },
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
            var data = jt.objdata(
                {an:authobj.email, at:authobj.token, updemail:authobj.email,
                 updpassword:jt.byId("pwdin").value});
            jt.call("POST", app.dr("/api/updacc"), data,
                    function (result) {
                        mgrs.act.successfulSignIn(result); },
                    function (code, errtxt) {
                        jt.out("acctmsglinediv", "Password change failed " +
                               code + ": " + errtxt); },
                    jt.semaphore("login.act.changePassword")); },
        acctActivHTML: function () {
            if(authobj.status !== "Pending") { return ""; }
            return jt.tac2html(
                ["a", {href:"#sendactcode", 
                       title:"Email a link to activate this account",
                       onclick:mdfs("act.sendActivationCode")},
                 "Send Activation Code"]); },
        sendActivationCode: function () {
            jt.out("acctactivdiv", "Activation code sent");
            var data = jt.objdata({an:authobj.email, at:authobj.token});
            jt.call("POST", app.dr("/api/mailactcode"), data,
                    function () {
                        jt.log("Activation send completed successfully"); },
                    function (code, errtxt) {
                        jt.out("acctactivdiv", "Send failed " + code + ": " +
                               errtxt); },
                    jt.semaphore("login.act.sendActivationCode")); },
        createNewAccountDisplay: function () {
            jt.out("topactiondiv", jt.tac2html(
                ["div", {id:"tactdiv"},
                 [["div", {cla:"forminline"},
                   [["label", {cla:"forminlab", fo:"emailin"}, "Email"],
                    ["input", {type:"email", cla:"formin", id:"emailin",
                               placeholder:"nospam@example.com"}]]],
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
            var data = jt.objdata(
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
            var data = jt.objdata({email:emaddr});
            jt.call("POST", app.dr("/api/mailpwr"), data,
                    function () {
                        jt.out("acctmsglinediv", "Password reset sent."); },
                    function (code, errtxt) {
                        jt.out("acctactivdiv", "Send failed " + code + ": " +
                               errtxt); },
                    jt.semaphore("login.act.sendResetPasswordLink")); }
    };  //end mgrs.act returned functions
    }());


    function signIn () {
        jt.out("acctmsglinediv", "");  //clear any previous login error
        var sav = mgrs.ap.read() || {};
        var ps = {an:app.startParams.an || sav.authname || "",
                  at:app.startParams.at || sav.authtoken || "",
                  emailin:jt.safeget("emailin", "value") || "",
                  passin:jt.safeget("passin", "value") || "",
                  actcode:app.startParams.actcode || ""};
        if(ps.emailin && !(ps.at || ps.passin)) {
            jt.byId("passin").focus();
            return; }
        if(!((ps.an || ps.emailin) && (ps.at || ps.passin))) {
            return; }  //not trying to sign in (or activate) yet.
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
                    jt.out("acctmsglinediv", errtxt); },
                jt.semaphore("login.signIn"));
    }


    //This works in conjunction with the static undecorated form created by
    //start.py, decorating to provide login without page reload.
    function initialize (restore) {
        if(initialTopActionHTML && !restore) {
            return; }  //login form was already set up, nothing to do.
        if(!initialTopActionHTML) {  //save so it can be restored on logout
            initialTopActionHTML = jt.byId("topactiondiv").innerHTML; }
        if(restore) {
            jt.out("topactiondiv", initialTopActionHTML); }
        //decorate the plain HTML for processing
        jt.out("loginlinksdiv", jt.tac2html(
            [["a", {href:"#newaccount", title:"Create a DiggerHub account",
                    onclick:mdfs("act.createNewAccountDisplay")},
              "join"],
             ["a", {href:"#resetpassword", title:"Email a password reset link",
                    onclick:mdfs("act.sendResetPasswordLink")},
              "reset password"]]));
        jt.on("loginform", "submit", app.login.formSubmit);
        signIn();  //attempt to sign in with cookie.
    }


return {
    init: function (restore) { initialize(restore); },
    formSubmit: function (event) { jt.evtend(event); signIn(); },
    signIn: function () { signIn(); },
    managerDispatch: function (mgrname, fname, ...args) {
        return mgrs[mgrname][fname].apply(app.login, args); }
};  //end of returned functions
}());
