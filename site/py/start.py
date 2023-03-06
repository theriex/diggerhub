""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring

import logging
import py.util as util

CACHE_BUST_PARAM = "v=230306"  # Updated via ../../build/cachev.js

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
<tr><td>Musicians get a tiny fraction</td><td>Musicians get a decent percentage</td></tr>
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

There is no substitute for what you feel.  Digger makes it easy to capture
your impressions as you listen, linking what you feel with the music in your
collection.  Personal music retrieval becomes more powerful With every song
you rate.  Sync your music across multiple devices with DiggerHub.

<h2>Hub Connect</h2>

<p>If you listen to music on more than one device, or if you want to
collaborate on music with friends with other music fans using Digger, you
can sign in on DiggerHub through the app to keep your ratings in sync and
collaborate with others.</p>

<h3>This song is fantastic!</h3>

<p>Click the Digger "share" button to copy the song Title, Artist, Album,
Keywords, Approachability and Energy Level, along with your saved personal
comment.  Send that to anyone any way you like, sharing great music improves
anyone's day and helps them get to know you better. <p>

<h3>Collaboration</h3>

<p>Your impressions let you easily collaborate with friends and fellow music
fans whose tastes you trust. Under the "fans" section of your profile,
you'll find these interactive displays: </p>

<div id="collabdiv">

<h4>Connect</h4>
<img src="docs/collab/connect.png"/>
<p>Find friends and music fans by their Digger name. If you haven't added
any friends yet, and you want to get a feel for how things work, you can
click "Connect Me" to add whoever the hub picks for you. </p>

<h4>Match</h4>
<img src="docs/collab/match.png"/>
<p>See how much music you have in common. If you have songs in your
collection that you haven't rated yet, your friends provide default rating
information you can use for contextual retrieval.  The "rcv" tab shows how
many default ratings you've received.  The "snd" tab shows how many default
ratings they have received from you.  If you remove a friend, their default
ratings are also removed.  When you play a song, any default rating
information for that song becomes yours. </p>

<h4>Messages</h4>
<img src="docs/collab/messages.png"/>
<p>See what your friends have shared recently and get automatic
recommendations from your friends that match your current listening
parameters. </p>

</div>

<p>It's called Digger because it digs through the stacks in your library
(oldest first) pulling music across a balance of artists matching what you
want to hear. </p>

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
