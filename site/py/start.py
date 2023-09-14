""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring
#pylint: disable=consider-using-from-import
#pylint: disable=wrong-import-order

import logging
import py.util as util
import py.dbacc as dbacc
import io
from PIL import Image, ImageDraw, ImageFont

CACHE_BUST_PARAM = "v=230822"  # Updated via ../../build/cachev.js

INDEXHTML = """
<!doctype html>
<html itemscope="itemscope" itemtype="https://schema.org/WebPage"
      xmlns="https://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="robots" content="noodp" />
  <meta name="description" content="$DESCR" />
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
</div>
$FLOWCONTENTHTML
<div id="contactdiv">
  <a href="docs/manual.html">Manual</a>
  &nbsp; | &nbsp; <a href="docs/terms.html">Terms</a>
  &nbsp; | &nbsp; <a href="docs/privacy.html">Privacy</a>
  &nbsp; | &nbsp; <a href="docs/about.html">About</a>
</div>
"""

REPORTFRAMEHTML = """
<div id="topsectiondiv">
  <div id="logodiv"><a href="https://diggerhub.com">
    <img src="$RELROOTimg/appicon.png"/></a></div>
</div>
<div id="reportoutercontentdiv">
  <div id="reportinnercontentdiv">
    $REPORTHTML
  </div>
</div>
"""

FLOWCONTENTHTML = """

<div id="toptextdiv" class="textcontentdiv boxedcontentdiv">

<p>The next song to play from your collection is the one matching your mood that you haven't heard in a while. </p>

<p>Digger knows which song that is because you told it last time you played it. </p>

</div>


<div class="textcontentdiv">
Digger works alongside your music software and does not modify your song
files.
</div>

<div id="downloadsignincontdiv">
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
  <div id="hubaccountcontentdiv" class="boxedcontentdiv"></div>
</div>

<div class="textsectionspacerdiv"></div>
<div class="textcontentdiv">

<p>Dig into your music. </p>

<p>Digger is a parametric retrieval app for autoplaying songs that match
your listening context.  It prefers what you've least recently heard, and
can fetch across genres, styles, time periods and artists in your music
library.  Whenever the currently playing song grabs you, tune its rating to
reflect your impression and make it easier to find next time.  Open to
anything?  Leave the filters wide open. </p>

<p>Rediscover your music collection.</p>

</div>

<div id="slidesdiv">
  <div id="slidepgdiv">
    <span id="slidepgindspan">
      <img class="sldselimg" src="docs/slideshow/slide0.png"/>
      <img class="sldimg" src="docs/slideshow/slide1.png"/>
      <img class="sldimg" src="docs/slideshow/slide2.png"/>
      <img class="sldimg" src="docs/slideshow/slide3.png"/>
      <img class="sldimg" src="docs/slideshow/slide4.png"/>
    </span>
  </div>
  <div id="slidedispdiv"><img src="docs/slideshow/slide0.png"/></div>
</div>

<div id="headertextdiv">
  <div id="marqueeplaceholderdiv">&nbsp;</div>
</div>

<div id="dloverlaydiv"></div>
"""

def fail404():
    return util.srverr("Page not found", 404)


def replace_and_respond(stinf):
    html = INDEXHTML
    for dcode, value in stinf["replace"].items():
        html = html.replace(dcode, value)
    return util.respond(html)


def song_html(song):
    if not isinstance(song, dict):
        song = util.load_json_or_default(song, {})
    html = "<span class=\"dstispan\" style=\"font-weight:bold;\">"
    html += song["ti"] + "</span> - "
    html += "<span class=\"dsarspan\">" + song["ar"] + "</span> - "
    html += "<span class=\"dsabspan\">" + song.get("ab", "") + "</span>"
    return html


def weekly_top20_page(stinf, sasum):
    months = ["", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    month = months[int(sasum["end"][5:7])]
    moday = month + " " + sasum["end"][8:10]
    html = "<div id=\"reptoplinediv\">" + sasum["digname"] + "</div>\n"
    html += ("<div id=\"reptitlelinediv\">Weekly Top 20 - " +
             "<span class=\"datevalspan\">" + moday + "</span></div>\n")
    html += "<ol>\n"
    for song in util.load_json_or_default(sasum["songs"], []):
        html += "<li>" + song_html(song) + "\n"
    html += "</ol>\n\n"
    # html += "<div id=\"repextrafieldsdiv\">"
    labs = [{"name":"Easiest", "fld":"easiest"},
            {"name":"Hardest", "fld":"hardest"},
            {"name":"Most Chill", "fld":"chillest"},
            {"name":"Most Amped", "fld":"ampest"}]
    for lab in labs:
        html += ("<span class=\"repsummarylabelspan\">" + lab["name"] +
                 ":</span>" + song_html(sasum[lab["fld"]]) + "<br/>")
    html += ("<div id=\"repsongtotaldiv\">" + str(sasum["ttlsongs"]) +
             " songs synchronized to DiggerHub</div>\n")
    stinf["replace"]["$TITLE"] = sasum["digname"] + " Weekly Top 20 " + moday
    stinf["replace"]["$DESCR"] = ("Top 20 songs from " + sasum["digname"] +
                                  " for week ending " + moday)
    stinf["replace"]["$CONTENTHTML"] = REPORTFRAMEHTML
    stinf["replace"]["$REPORTHTML"] = html
    stinf["replace"]["$RELROOT"] = stinf["replace"]["$RDR"]
    diop = stinf["path"].replace("plink", "dio") + "/wt20img.png"
    stinf["replace"]["$SITEPIC"] = "/" + diop
    return replace_and_respond(stinf)


def weekly_top20_image(sasum):
    songs = util.load_json_or_default(sasum["songs"], [])
    songs = songs[0:16]  # limited vertical space
    mtxt = ""
    for idx, song in enumerate(songs):
        mtxt += str(idx + 1) + ". " + song["ti"] + " - " + song["ar"] + "\n"
    mtxt += "..."
    img = Image.open("public/img/ogimg.png")
    draw = ImageDraw.Draw(img)
    # image size may be reduced at least 3x, aim for minimum 10px font size
    draw.font = ImageFont.truetype("Lato-Bold.ttf", 30)
    draw.multiline_text((90, 20), mtxt, (16, 16, 16))
    bbuf = io.BytesIO()
    img.save(bbuf, format="PNG")
    return util.respond(bbuf.getvalue(), mimetype="image/png")


def weekly_top20(stinf, rtype="page"):
    pes = stinf["rawpath"].split("/")
    if len(pes) < 4:
        return fail404()
    digname = pes[2]
    endts = pes[3]
    where = ("WHERE sumtype = \"wt20\"" +
             " AND digname = \"" + digname + "\"" +
             " AND end LIKE(\"" + endts + "%\")" +
             " ORDER BY modified DESC LIMIT 1")
    sasums = dbacc.query_entity("SASum", where)
    if len(sasums) <= 0:
        return fail404()
    sasum = sasums[0]
    if rtype == "image":
        return weekly_top20_image(sasum)
    return weekly_top20_page(stinf, sasum)


def mainpage(stinf):
    stinf["replace"]["$CONTENTHTML"] = CONTENTHTML
    stinf["replace"]["$FLOWCONTENTHTML"] = FLOWCONTENTHTML
    return replace_and_respond(stinf)


# path is everything after the root url slash.  js/css etc need to be found
# relative to the specified path.
def startpage(path, refer):
    reldocroot = path.split("/")[0]  # "" if empty path
    if reldocroot:  # have at least one level of subdirectory specified
        reldocroot = "".join(["../" for elem in path.split("/")])
    stinf = {
        "rawpath": path,
        "path": path.lower(),
        "refer": refer or "",
        "replace": {
            "$SITEPIC": "$RDRimg/appicon.png?" + CACHE_BUST_PARAM,
            "$RDR": reldocroot,
            "$CBPARAM": CACHE_BUST_PARAM,
            "$TITLE": "DiggerHub",
            "$DESCR": "Digger saves your song ratings and plays music from your collection matching what you want to hear. People use Digger to automate their music library."}}
    if stinf["refer"]:
        logging.info("startpage referral: " + refer)
    if not reldocroot or stinf["path"].startswith("iosappstore"):
        return mainpage(stinf)
    # path for dynamic images needs to not contain static directory ident
    if stinf["path"].startswith("dio/wt20/"):
        return weekly_top20(stinf, rtype="image")
    if stinf["path"].startswith("plink/wt20/"):
        return weekly_top20(stinf, rtype="page")
    return fail404()
