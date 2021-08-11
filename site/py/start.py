""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring

import logging
import py.util as util

CACHE_BUST_PARAM = "v=210811"  # Updated via ../../build/cachev.js

INDEXHTML = """
<!doctype html>
<html itemscope="itemscope" itemtype="https://schema.org/WebPage"
      xmlns="https://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="robots" content="noodp" />
  <meta name="description" content="Digger is a contextual music retrieval tool for your music library." />
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

<div id="topsectiondiv">
  <div id="logodiv"><img src="img/appicon.png"/></div>
  <!-- login has to be an actual form to enable remembered passwords -->
  <div id="topactiondiv">
    <!-- need a real form for password autosave, no onchange submit. -->
    <form id="loginform" method="post" action="redirlogin">
      <div id="loginparaminputs"></div>
      <div id="loginvisualelementsdiv">
        <div class="onelineformdiv">
          <input type="email" class="lifin" name="emailin" id="emailin"
                 size="16" placeholder="nospam@example.com"/><input
                 type="password" class="lifin" name="passin" id="passin"
                 size="6" placeholder="*password*"/>
          <input value="LogIn" type="submit" class="buttonstyle" id="loginb"/>
        </div>
        <div id="acctmsglinediv"></div>
        <div id="loginbuttonsdiv" class="formbuttonsdiv">
          <div id="loginlinksdiv"></div>
        </div>
      </div> <!-- loginvisualelementsdiv -->
    </form>
  </div>
</div>


<div id="outercontentdiv">
  <div id="textcontentdiv">
    <div id="splashdiv">

<div id="btidiggerdiv">Digger</div>
<div id="btihubdiv">Hub</div>

<div id="splashblockdiv">
<p>Digger spins tracks from your library that match your control settings. Works with:</p>

<div id="fileorstreamchoicediv">
  <a href="#files"><span class="spchspan">Files</span></a>
  or
  <a href="#streaming"><span class="spchspan">Streaming</span></a>
</div>

<div id="tcgdspchfile" style="display:none;">

<p>Download Digger for your platform: </p>

<div id="downloadsdiv">
<a href="downloads/digger-linux">digger-linux</a>
<a href="downloads/Digger.dmg">Digger.dmg</a>
<a href="downloads/digger-win.zip">digger-win.zip</a>
</div>

</div> <!-- diggerfilediv -->

<div id="tcgdspchstrm" style="display:none;">

<p>You <em>must</em> use a Spotify Premium account and authorize Digger for
streaming. <a href="/digger">Launch Digger</a><p>

</div> <!-- diggerstreamingdiv -->
</div> <!-- splashblockdiv -->

    </div> <!-- splashdiv -->
  </div> <!-- textcontentdiv -->
  <div id="vidcontentdiv">
    <video controls src="img/DiggerDemo540HighBQ.mp4" width="300">
      Video unavailable in this browser.</video>
  </div>

  <div id="contactdiv">
    Digger is <a href="https://github.com/theriex/digger#digger">open source</a>
  </div>

  <div id="localtestdiv" style="display:none">
    <iframe title="test to see if local digger server is running" id="diggerlocaliframe" src="http://localhost:6980/version"></iframe>
  </div>

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
