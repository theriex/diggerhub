""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring

import logging
import py.util as util

CACHE_BUST_PARAM = "v=230425"  # Updated via ../../build/cachev.js

INDEXHTML = """
<!doctype html>
<html itemscope="itemscope" itemtype="https://schema.org/WebPage"
      xmlns="https://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="robots" content="noodp" />
  <meta name="description" content="Digger saves your music ratings and plays music from your collection matching what you want to hear. People use Digger to automate their music library." />
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
  <div id="sitebodycontentdiv">
    <div id="sitecontentdiv">
      <div id="sitecontentinnerdiv">$CONTENTHTML</div></div>
    <div id="hpgoverlaydiv"></div>
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
</body>
</html>
"""

CONTENTHTML = """
<div id="topsectiondiv">
  <div id="logodiv"><img src="img/appicon.png"/></div>
  <div id="hubaccountcontentdiv"></div>
</div>
$FLOWCONTENTHTML
<div id="contactdiv">
  <a href="docs/manual.html">Manual</a>
  &nbsp; | &nbsp; <a href="docs/terms.html">Terms</a>
  &nbsp; | &nbsp; <a href="docs/privacy.html">Privacy</a>
  &nbsp; | &nbsp; <a href="docs/support.html">Support</a>
</div>
"""

FLOWCONTENTHTML = """

<div class="textcontentdiv boxedcontentdiv">
<p>You've spent years listening to music, and you're going to spend years
more.  Isn't it time you started managing your impressions like you manage
your song files? </p>

<p>Your library doesn't want to sit around waiting for you to select things.
Describe what you want to hear, and record what you think while it's playing.
Your collection will autoplay great music.</p>
</div>

<div id="slidesdiv">
  <div id="slidedispdiv"><img src="docs/slideshow/slide0.png"/></div>
</div>

<div class="textcontentdiv">
Digger works alongside your music software and does not modify your song
files.
</div>

<div id="downloadsdiv" class="boxedcontentdiv">
  <div class="platoptdescdiv">Get Digger for</div>
  <div class="downloadsline">
    <div><a href="downloads/digger-linux" onclick="app.login.dldet(event);return false">Linux</a></div>
    <div><a href="downloads/Digger.dmg" onclick="app.login.dldet(event);return false">Mac</a></div>
    <div><a href="downloads/digger-win.zip" onclick="app.login.dldet(event);return false">Windows</a><br/>
         <span>(win8.1+)</span></div>
  </div>
  <div class="downloadsline">
    <div><a href="https://apps.apple.com/app/id6446126460" onclick="app.login.dldet(event);return false">IOS</a></div>
    <div><a href="https://play.google.com/store/apps/details?id=com.diggerhub.digger" onclick="app.login.dldet(event);return false">Android</a></div>
  </div>
  <div class="platoptdescdiv">&nbsp;</div>
</div>

<div class="textcontentdiv">
<p>To sync your ratings across devices, or collaborate with other music
fans, sign in on DiggerHub through the app.</p>
</div>

<h3>Share</h3>

<div class="textcontentdiv boxedcontentdiv">
<p><em>"This song is amazing!"</em></p>

<p>Share <img class="featureico" src="img/share.png"/> the song
<em>Title</em>, <em>Artist</em>, <em>Album</em>, your <em>Keywords</em>,
<em>Approachability</em> and <em>Energy Level</em>, along with your personal
comment <img class="featureico" src="img/comment.png"/>.  Send to anyone
however you like. </p>
</div>

<h3>Collaborate</h3>

<div class="textcontentdiv">
<p>Your music ratings extend beyond automated retrieval to form a foundation
for detailed interaction with other music fans.</p>
</div>

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

<div class="textcontentdiv">
Just renting your music?  Consider treating yourself to a new album purchase
this week.
</div>

<div id="rentvsowndiv">
<table>
<tr><th>Music rental</th><th><span class="versusspan">vs</span><th>Music ownership</th></tr>
<tr><td>Buffet</td><td></td><td>A la carte</td></tr>
<tr><td>Musicians get a tiny fraction</td><td></td><td>Musicians get a percentage</td></tr>
<tr><td>Regional restrictions</td><td></td><td>Listen wherever</td></tr>
<tr><td>Licensing expires</td><td></td><td>Always yours</td></tr>
<tr><td>Offline?</td><td></td><td>Always available</td></tr>
<tr><td>Suggested songs</td><td></td><td>Digger retrieval</td></tr>
</table>
</div>

<div id="headertextdiv">
  <div id="marqueeplaceholderdiv">Own your impressions.</div>
</div>

<div id="taglinediv">
  Dig into your music collection.
</div>

<div id="dloverlaydiv"></div>
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
            "$TITLE": "DiggerHub",
            "$CONTENTHTML": CONTENTHTML,
            "$FLOWCONTENTHTML": FLOWCONTENTHTML}}
    if stinf["refer"]:
        logging.info("startpage referral: " + refer)
    html = INDEXHTML
    for dcode, value in stinf["replace"].items():
        html = html.replace(dcode, value)
    return util.respond(html)
