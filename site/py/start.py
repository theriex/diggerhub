""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring

import logging
import py.util as util

CACHE_BUST_PARAM = "v=220429"  # Updated via ../../build/cachev.js

INDEXHTML = """
<!doctype html>
<html itemscope="itemscope" itemtype="https://schema.org/WebPage"
      xmlns="https://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="robots" content="noodp" />
  <meta name="description" content="Digger let's you get noise in the room without having to wade through the stacks each time. People use Digger to get back into their music collections." />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="mobile-web-app-capable" content="yes" />
  <link rel="icon" href="$SITEPIC">
  <link rel="image_src" href="$SITEPIC" />
  <meta property="og:image" content="$SITEPIC" />
  <meta property="twitter:image" content="$SITEPIC" />
  <meta itemprop="image" content="$SITEPIC" />
  <title>$TITLE</title>
  <link href="$RDRcss/site.css?$CBPARAM" rel="stylesheet" type="text/css" />
  <link href="$RDRcss/digger.css?$CBPARAM" rel="stylesheet" type="text/css" />
</head>
<body id="bodyid">
<div id="sitebody">

<div id="contactdiv">
  <a href="docs/about.html">About</a>
  &nbsp; | &nbsp; <a href="docs/manual.html">Manual</a>
  &nbsp; | &nbsp; <a href="docs/privacy.html">Privacy</a>
  &nbsp; | &nbsp; <a href="docs/support.html">Support</a>
</div>

<div id="topsectiondiv">
  <div id="logodiv"><img src="img/appicon.png"/></div>
</div>

<div id="outercontentdiv">
  <div id="homepgcontentdiv">
    <div id="textcontentdiv">
      <div id="splashdiv">
        <div id="headertextdiv">Digger <i>Hub</i></div>
        <div id="splashblockdiv">
          <div id="wsadiv">
            Digger
            <a onclick="window.open('docs/websrvapp.html');return false"
               href="docs/websrvapp.html">webserver app</a>
          </div>
          <div id="downloadsdiv">
            <div><a href="downloads/digger-linux">digger-linux</a></div>
            <div><a href="downloads/Digger.dmg">Digger.dmg</a></div>
            <div><a href="downloads/digger-win.zip">digger-win.zip</a><br/>
                 <span>(win8.1+)</span></div>
          </div>
        </div>
      </div>
    </div> <!-- textcontentdiv -->
    <div id="slidesdiv"></div>
    <div id="taglinediv">
      Dig into your music collection.
    </div>
    <div id="localtestdiv" style="display:none">
      <iframe title="test to see if local digger server is running" id="diggerlocaliframe" src="http://localhost:6980/version"></iframe>
    </div>
    <div id="hpgoverlaydiv"></div>
  </div> <!-- homepgcontentdiv -->
</div> <!-- outercontentdiv -->

<script>
  var diggerapp = {
      context:"web",
      modules:[
          {name:"refmgr", desc:"Server data and client cache"},
          {name:"login", desc:"Authentication and account management"},
          //svc determines "web" or "loc" run
          {name:"svc", type:"dm", desc:"webapp server interaction calls"},
          //player may redirect to load supporting libraries
          {name:"player", type:"dm", desc:"player panel functions"},
          {name:"top", type:"dm", desc:"top panel functions"},
          {name:"filter", type:"dm", desc:"filter panel functions"},
          {name:"deck", type:"dm", desc:"deck panel functions"}]};
</script>
<script src="$RDRjs/jtmin.js?$CBPARAM"></script>
<script src="$RDRjs/app.js?$CBPARAM"></script>
<script>
  app.init();
</script>

</div> <!-- sitebody -->
</body>
</html>
"""

# path is everything after the root url slash.
def startpage(path, refer):
    reldocroot = path.split("/")[0]
    if reldocroot:
        reldocroot = "../"
    stinf = {
        "rawpath": path,
        "path": path.lower(),
        "refer": refer or "",
        "replace": {
            "$RDR": reldocroot,
            "$CBPARAM": CACHE_BUST_PARAM,
            "$SITEPIC": "img/appicon.png?" + CACHE_BUST_PARAM,
            "$TITLE": "DiggerHub"}}
    if stinf["refer"]:
        logging.info("startpage referral: " + refer)
    html = INDEXHTML
    for dcode, value in stinf["replace"].items():
        html = html.replace(dcode, value)
    return util.respond(html)
