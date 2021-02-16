/*jslint browser, white, fudge */
/*global window jtminjsDecorateWithUtilities */

var app = {};  //Global container for application level funcs and values
var jt = {};   //Global access to general utility methods

(function () {
    "use strict";

    app.modules = [
        {name:"refmgr", desc:"Server data and client cache"},
        {name:"login", desc:"Authentication and account managerment"}];


    app.init2 = function () {
        app.amdtimer.load.end = new Date();
        jt.log("window.innerWidth: " + window.innerWidth);
        app.startParams = jt.parseParams("String");
        app.login.init();
    };


    app.init = function () {
        var ox = window.location.href;
        if((ox.toLowerCase().indexOf("https:") !== 0) &&
           (ox.search(/:\d080/) < 0)) {  //local dev
            window.location.href = "https:" + ox.slice(ox.indexOf("/"));
            return; }  //stop and let the redirect happen.
        app.docroot = ox.split("/").slice(0, 3).join("/") + "/";
        if(!jtminjsDecorateWithUtilities) { //support lib not loaded yet
            return setTimeout(app.init, 50); }
        jtminjsDecorateWithUtilities(jt);
        var modules = app.modules.map((p) => "js/amd/" + p.name);
        app.amdtimer = {};
        app.amdtimer.load = { start: new Date() };
        jt.loadAppModules(app, modules, app.docroot, app.init2, "?v=210216");
    };


    //Return the argument list as a string of arguments suitable for appending
    //to onwhatever function text.
    app.paramstr = function (args) {
        var ps = "";
        if(args && args.length) {
            ps = args.reduce(function (acc, arg) {
                if((typeof arg === "string") && (arg !== "event")) {
                    arg = "'" + arg + "'"; }
                return acc + "," + arg; }, ""); }
        return ps;
    };


    //app.docroot is initialized with a terminating '/' so it can be
    //concatenated directly with a relative path, but remembering and
    //relying on whether a slash is required is annoying.  Double slashes
    //are usually handled properly but can be a source of confusion, so this
    //strips off any preceding slash in the relpath.
    app.dr = function (relpath) {
        if(relpath.startsWith("/")) {
            relpath = relpath.slice(1); }
        return app.docroot + relpath;
    };

}());
