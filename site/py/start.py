""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring
#pylint: disable=consider-using-from-import
#pylint: disable=wrong-import-order

import logging
import py.mconf as mconf
import py.util as util
import py.dbacc as dbacc
import io
from PIL import Image, ImageDraw, ImageFont

CACHE_BUST_PARAM = "v=240427"  # Updated via ../../build/cachev.js

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

PERSONALPAGEHTML = """
<div id="ppgwt20div">
  $LATESTTOP20
</div>
"""

DELETEMEINSTHTML = """

<h1>Deleting Your Data</h1>

<p>Thanks for having trusted your Digger song rating data to DiggerHub.  As
part of keeping that trust, a few steps are required to confirm who you are
and that you really do want to delete all your data: </p>

<ol> 

<li>In the Digger app, while signed in to DiggerHub, choose "me" in the
account headings then choose the "sign out" heading.  In the sign out
display, click the "Delete Me" button and then confirm.

<li>In the Digger app, Change your account name according to the email you
received, then uninstall the app and respond to the email.

<li>Allow a few business days for processing.  You will receive an email
confirming your account, all your song ratings, and any received or sent
messages have all been deleted.

</ol>

<p>After your data has been removed, DiggerHub won't have any remaining data
about you.  If you kept a copy of your data using the Win/Mac/*nix version
of Digger, that data will no longer sync with DiggerHub because the deleted
server IDs won't be found anymore.  Please be absolutely sure you never want
to use your account or ratings again if you choose to delete your data. </p>

<p>If you never joined DiggerHub, all your Digger ratings are stored with
the app, so they are deleted with the app if you uninstall it. </p>

"""

FLOWCONTENTHTML = """

<div id="toptextdiv" class="textcontentdiv boxedcontentdiv">
<div>
Get the player that gets what you want to hear next.
</div>
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
  <div class="platoptdescdiv"></div>
</div>

<div class="annoscrdiv">
<div>Select one of your albums to play.</div>
<img src="docs/screenshots/01SuggAlb.png"/>
</div>

<div class="annoscrdiv">
<div>Adjust knobs, keys, stars, and comment to reflect what you feel.</div>
<img src="docs/screenshots/02AlbPlayRating.png"/>
</div>

<div class="annoscrdiv">
<div>Set the filters for what you want to hear.</div>
<img src="docs/screenshots/03DeckFilters.png"/>
</div>

<div class="annoscrdiv">
<div>Fine tune what's on deck.</div>
<img src="docs/screenshots/04DeckAction.png"/>
</div>

<div id="hubacctdiv">
<div id="featurelistdiv">Digger features: <ul>
<li>Switch between album, autoplay and search anytime.
<li>Describe songs as you listen.
<li>Autoplay what you want to hear.
</ul></div>
<div>Connect to <em>DiggerHub</em> for backup, sync, and
optional rating collaboration. </div>
<div id="hubaccountcontentdiv" class="boxedcontentdiv"></div>
</div>

<div class="textsectionspacerdiv"></div>

<div class="textcontentdiv convocontentdiv"> The Digger Custom Autoplay
Mixer can reach across genres, time periods and artists, preferring
what you've least recently heard.  Rediscover your music collection.  <a
href="#showdownloadlinks" onclick="app.login.scrollToTopOfContent();return
false">Dig into your music</a>. </div>

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


def month_and_day_from_dbtimestamp(timestamp):
    months = ["", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    month = months[int(timestamp[5:7])]
    moday = month + " " + timestamp[8:10]
    return moday


def weekly_top20_content_html(sasum):
    moday = month_and_day_from_dbtimestamp(sasum["end"])
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
             " songs synchronized to <a href=\"https://diggerhub.com\">" +
             "DiggerHub</a></div>\n")
    return html


def weekly_top20_page(stinf, sasum):
    moday = month_and_day_from_dbtimestamp(sasum["end"])
    html = weekly_top20_content_html(sasum)
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
    img = Image.open(mconf.rpbgimg)
    draw = ImageDraw.Draw(img)
    # image size may be reduced at least 3x, aim for minimum 10px font size
    draw.font = ImageFont.truetype(mconf.rpfgfnt, 30)
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


def find_latest_t20_summary(digname):
    where = ("WHERE sumtype = \"wt20\"" +
             " AND digname = \"" + digname + "\"" +
             " ORDER BY end DESC LIMIT 1")
    sasums = dbacc.query_entity("SASum", where)
    if len(sasums) > 0:
        return sasums[0]
    return None


def listener_page(stinf):
    pes = stinf["rawpath"].split("/")
    if len(pes) < 2:
        return fail404()
    digname = pes[1]
    wt20 = "No recent listening info"
    sasum = find_latest_t20_summary(digname)
    logging.info("listener_page " + digname + " " + str(sasum))
    if sasum:
        wt20 = weekly_top20_content_html(sasum)
    stinf["replace"]["$CONTENTHTML"] = REPORTFRAMEHTML
    stinf["replace"]["$REPORTHTML"] = PERSONALPAGEHTML
    stinf["replace"]["$RELROOT"] = stinf["replace"]["$RDR"]
    stinf["replace"]["$LATESTTOP20"] = wt20
    return replace_and_respond(stinf)


def delete_me_instruct(stinf):
    stinf["replace"]["$CONTENTHTML"] = REPORTFRAMEHTML
    stinf["replace"]["$REPORTHTML"] = DELETEMEINSTHTML
    stinf["replace"]["$RELROOT"] = stinf["replace"]["$RDR"]
    return replace_and_respond(stinf)


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
            "$DESCR": "Digger codifies your music impressions into retrieval parameters and personal annotations. People use Digger to automate their digital music collections and collaborate on listening experiences."}}
    if stinf["refer"]:
        logging.info("startpage referral: " + refer)
    if not reldocroot or stinf["path"].startswith("iosappstore"):
        return mainpage(stinf)
    # paths for dynamic links must not start with static content paths
    if stinf["path"].startswith("dio/wt20/"):
        return weekly_top20(stinf, rtype="image")
    if stinf["path"].startswith("plink/wt20/"):
        return weekly_top20(stinf, rtype="page")
    if stinf["path"].startswith("delmeinst"):
        return delete_me_instruct(stinf)
    if stinf["path"].startswith("listener"):
        return listener_page(stinf)
    return fail404()
