/*jslint node, white, fudge */

//Create/verify diggerhub links to the digger source files.
//node makelinks.js
//node makelinks.js delete
//Assumes the digger project is a sibling project of this diggerhub project

var linker = (function () {
    "use strict";

    var fs = require("fs");
    var ws = {linkdirs:["img", "js", "js/amd"]};


    function makeWorkingSetRoots () {
        var dn = __dirname;
        ws.hubr = dn.slice(0, dn.lastIndexOf("/"));
        ws.digr = ws.hubr.slice(0, ws.hubr.lastIndexOf("/") + 1) +
            "digger/docroot/";
        ws.hubr += "/site/public/";
    }


    function jslf (obj, method, ...args) {
        return obj[method].apply(obj, args);
    }


    function checkLink (cmd, relpath, fname) {
        var hfp = ws.hubr + relpath + "/" + fname;
        var dfp = ws.digr + relpath + "/" + fname;
        if(!jslf(fs, "existsSync", hfp)) {
            if(cmd === "create") {
                fs.symlink(dfp, hfp, function (err) {
                    if(err) { throw err; }
                    console.log("created " + hfp); }); }
            else {
                console.log("missing " + hfp); } }
        else {
            if(cmd === "delete") {
                fs.unlink(hfp, function (err) {
                    if(err) { throw err; }
                    console.log("removed " + hfp); }); }
            else {
                console.log(" exists " + hfp); } }
    }


    function traverseLinks (cmd) {
        console.log("Command: " + cmd);
        makeWorkingSetRoots();
        ws.linkdirs.forEach(function (relpath) {
            var dir = ws.digr + relpath;
            var options = {encoding:"utf8", withFileTypes:true};
            fs.readdir(dir, options, function (err, dirents) {
                if(err) { throw err; }
                dirents.forEach(function (dirent) {
                    if(dirent.isFile()) {
                        checkLink(cmd, relpath, dirent.name); } }); }); });
    }


    return {
        run: function () { traverseLinks(process.argv[2] || "create"); }
    };
}());

linker.run();
