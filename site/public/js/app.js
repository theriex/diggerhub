/*jslint browser, white, fudge */
/*global window jtminjsDecorateWithUtilities */

var app = {};  //Global container for application level funcs and values
var jt = {};   //Global access to general utility methods

(function () {
    "use strict";

    app.modules = [{name:"refmgr", desc:"Server data and client cache"}];


    app.init2 = function () {
        app.amdtimer.load.end = new Date();
        jt.log("window.innerWidth: " + window.innerWidth);
        jt.out("loadstatdiv", "");
    };


    app.init = function () {
        var ox = window.location.href;
        app.docroot = ox.split("/").slice(0, 3).join("/") + "/";
        if(!jtminjsDecorateWithUtilities) { //support lib not loaded yet
            return setTimeout(app.init, 50); }
        jtminjsDecorateWithUtilities(jt);
        var modules = app.modules.map((p) => "js/amd/" + p;);
        jt.out("loadstatdiv", "Loading app modules...");
        app.amdtimer = {};
        app.amdtimer.load = { start: new Date() };
        jt.loadAppModules(app, modules, app.baseurl, app.init2, "?v=210204");
    };

}());
