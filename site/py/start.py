""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring

import logging
import py.util as util

CACHE_BUST_PARAM = "v=230214"  # Updated via ../../build/cachev.js

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
<div id="outercontentdiv">
  <div id="homepgcontentdiv">
    <div id="topsectiondiv">
      <div id="logodiv"><img src="img/appicon.png"/></div>
      <div id="hubaccountcontentdiv"></div>
    </div>
    <div id="textcontentdiv">
      <div id="splashdiv">
        <div id="whatisdiggerdiv">
Digger is a music rating and retrieval app for your music collection.  Digger helps you enjoy the music you own.

          <div id="rentvsowndiv">
<table>
<tr><th>Music rental:</th><th>Music ownership:</th></tr>
<tr><td>All you can eat buffet</td><td>Pay as you go</td></tr>
<tr><td>Musicians get a tiny fraction</td><td>Musicians get most of what you pay</td></tr>
<tr><td>Regional restrictions</td><td>Listen wherever</td></tr>
<tr><td>Licensing expires</td><td>Always yours</td></tr>
<tr><td>Suggested songs</td><td>Digger retrieval</td></tr>
</table>
          </div>
        </div>
        <div id="headertextdiv">
          <div id="marqueeplaceholderdiv">Digger <i>Hub</i></div></div>
        <div id="splashblockdiv">
          <div class="platoptdescdiv">&nbsp;</div>
          <div class="downloadsdiv">
            <div><a href="downloads/digger-linux" onclick="app.login.dldet(event);return false">Linux</a></div>
            <div><a href="downloads/Digger.dmg" onclick="app.login.dldet(event);return false">Mac</a></div>
            <div><a href="downloads/digger-win.zip" onclick="app.login.dldet(event);return false">Windows</a><br/>
                 <span>(win8.1+)</span></div>
          </div>
          <div class="downloadsdiv">
            <div><a href="https://github.com/theriex/diggerIOS" onclick="app.login.dldet(event);return false">IOS</a><br/><span>(alpha)</span></div>
            <div><a href="https://play.google.com/store/apps/details?id=com.diggerhub.digger" onclick="app.login.dldet(event);return false">Android</a></div>
          </div>
          <div class="platoptdescdiv">&nbsp;</div>
        </div>
        <div id="moreaboutdiggerdiv">

Digger makes it easy to rate songs so they can be fetched appropriately in a
wide range of situations.  When you are playing music, Digger works like an
automatic playlist, fetching and playing songs matching your listening
context.  Digger helps you get back into your music collection by selecting
good music you haven't played in a while.

        </div>
      </div>
    </div> <!-- textcontentdiv -->
    <div id="slidesdiv"></div>
    <div id="usingdiggerdiv">

There is no substitute for your personal impressions.  Noting what you think
of a song while it is playing might seem daunting at first, but it's a
natural extension to listening, and with every rating personal retrieval
grows as a new capability of your music collection.  Digger gets music
playing based on what you are currently in the mood for, and you've already
described what that might be.

<p>It's called Digger because it digs through the stacks in your library
(oldest first) pulling music appropriate for your listening context across a
balance of artists. </p>

    </div>
    <div id="taglinediv">
      Dig into your music collection.
    </div>
    <div id="localtestdiv" style="display:none">
      <iframe title="test to see if local digger server is running" id="diggerlocaliframe" src="http://localhost:6980/version"></iframe>
    </div>
    <div id="dloverlaydiv"></div>
    <div id="hpgoverlaydiv"></div>
  </div> <!-- homepgcontentdiv -->
</div> <!-- outercontentdiv -->

<div id="contactdiv">
  <a href="docs/manual.html">Manual</a>
  &nbsp; | &nbsp; <a href="docs/terms.html">Terms</a>
  &nbsp; | &nbsp; <a href="docs/privacy.html">Privacy</a>
  &nbsp; | &nbsp; <a href="docs/support.html">Support</a>
</div>

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
