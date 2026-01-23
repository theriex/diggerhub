""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring
#pylint: disable=consider-using-from-import
#pylint: disable=wrong-import-order
#pylint: disable=too-many-return-statements

import logging
import py.mconf as mconf
import py.util as util
import py.dbacc as dbacc
import io
from PIL import Image, ImageDraw, ImageFont
import json
import datetime

CACHE_BUST_PARAM = "v=260123"  # Updated via ../../build/cachev.js

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
          {name:"prof", desc:"Listener profile info and reports"},
          //svc determines "web" or "loc" run
          {name:"svc", type:"dm", desc:"webapp server interaction calls"},
          //player may redirect to load supporting libraries
          {name:"player", type:"dm", desc:"player panel functions"},
          {name:"top", type:"dm", desc:"top panel functions"},
          {name:"filter", type:"dm", desc:"filter panel functions"},
          {name:"deck", type:"dm", desc:"deck panel functions"}]};
</script>
<script>
  var rundata = "";
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

<div id="toptextdiv" class="textcontentdiv">
<div>
<i>The</i> Hub <i>for</i> Digger <i>Collection Listening</i>
</div>
</div>

<div id="quickdispdiv" class="textcontentdiv">

Digger will continuously select and play all music in your collection
matching your retrieval filters, least recently played first, working from
your own impressions.

</div>

<div id="downloadsdiv" class="boxedcontentdiv">
  <div class="platoptdescdiv">Digger is free on</div>
  <div class="downloadsline">
    <div><a href="downloads/digger-linux" onclick="app.login.dldet(event);return false">Linux</a></div>
    <div><a href="downloads/Digger.dmg" onclick="app.login.dldet(event);return false">Mac</a></div>
    <div><a href="downloads/digger-win.zip" onclick="app.login.dldet(event);return false">Windows</a><br/>
         <span>(win8.1+)</span></div>
  </div>
  <div class="downloadsline">
    <div><a href="https://apps.apple.com/app/id6446126460" onclick="app.login.dldet(event);return false">iOS</a></div>
    <div><a href="https://play.google.com/store/apps/details?id=com.diggerhub.digger" onclick="app.login.dldet(event);return false">Android</a></div>
  </div>
  <div class="platoptdescdiv"></div>
</div>

<div id="joinusdispdiv" class="textcontentdiv">

Listeners use DiggerHub for backup and sync across devices, sharing top songs for the week, bookmarking new music for consideration, collaborating through collections, and whatever other useful fun we come up with. Join us.

</div>

<div id="playfeaturesdiv" class="boxedcontentdiv">
<table>
<tr><td><img class="featureico" src="img/deck.png"/></td><td>Continuous select autoplay from your own music impressions.</td></tr>
<tr><td><img class="featureico" src="img/album.png"/></td><td>Switch to (or from) album listening anytime.</td></tr>
<tr><td><img class="featureico" src="img/search.png"/></td><td>Fast find music by artist, album, title, genre and personal note.</td></tr>
</table>
</div>

<div id="gettingstartedtitlediv" class="textcontentctrdiv">
- Getting started -
</div>

<div class="annoscrdiv">
<div>Select one of your albums to play.</div>
<div class="scrnshotdiv"><img src="docs/screenshots/01SuggAlb.png"/></div>
</div>

<div class="annoscrdiv">
<div>Adjust knobs, keywords, stars and comment to reflect what you feel as you're listening. </div>
<div class="scrnshotdiv"><img src="docs/screenshots/02AlbPlayRating.png"/></div>
</div>

<div class="annoscrdiv">
<div>Filter continuous selection for the music you want to hear.</div>
<div class="scrnshotdiv"><img src="docs/screenshots/03DeckFilters.png"/></div>
</div>

<!--
<div class="annoscrdiv">
<div>Fast find what you want by artist, album, title, comment.</div>
<div class="scrnshotdiv"><img src="docs/screenshots/04Search.png"/></div>
</div>
-->

<div class="textsectionspacerdiv"></div>

<div class="textcontentdiv convocontentdiv"> Digger reaches across genres,
styles, time periods and geography, preferring what you've least recently
heard. 
<a href="#showdownloadlinks"
  onclick="app.login.scrollToTopOfContent();return false">
Dig into your music</a>. </div>

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
    html = ("<span id=\"wtidspan" + str(song["dsId"]) + "\">" +
            "<span class=\"wtarspan\">" + song["ar"] + "</span>" +
            "<span class=\"wtartisepspan\"> - </span>" +
            "<span class=\"wttispan\">" + song["ti"] + "</span>" +
            # album not included, too verbose and not used for search
            "</span>")
    return html


def month_and_day_from_dbtimestamp(timestamp):
    months = ["", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    month = months[int(timestamp[5:7])]
    moday = month + " " + timestamp[8:10]
    return moday


def listener_report_page_html(digname, tline, content):
    html = "<div id=\"reptoplinediv\" data-dnm=\"" + digname + "\">" + digname + "</div>\n"
    html += ("<div id=\"repheadingdiv\">\n" +
             "  <div id=\"hubaccountcontentdiv\"></div>\n" +
             "  <div id=\"reptopactiondiv\"></div>\n" +
             "  <div id=\"reptitlelinediv\">" + tline + "</div>\n"
             "</div>")
    html += "<div id=\"reptbodydiv\">" + content + "</div>\n"
    return html


def get_wt20_nav_link(direction, sasum):
    img = "/img/backskip.png"
    td7 = datetime.timedelta(days=7)
    pdt = dbacc.dt2ISO(dbacc.ISO2dt(sasum["end"]) - td7)
    if direction == "next":
        ep7 = dbacc.ISO2dt(sasum["end"]) + td7
        if ep7 > datetime.datetime.utcnow():
            return ""
        img = "/img/skip.png"
        pdt = dbacc.dt2ISO(ep7)
    pdt = pdt[0:10]
    img = "<img src=\"" + img + "\" class=\"pageskipico\"/>"
    return "<a href=\"" + pdt + "\">" + img + "</a>"


def curated_wt20_content(sasum):
    qr8 = util.load_json_or_default(sasum["curate"], {})
    recs = [r for r in qr8.get("rovrs", []) if r.get("recommended", "")]
    if not recs:  # curated with no recommendations is not curated
        return ""
    songs = util.load_json_or_default(sasum["songs"], [])
    html = "<ul class=\"wt20list\">\n"
    for idx, rec in enumerate(qr8["rovrs"]):
        if rec["recommended"]:
            html += ("<li>" + song_html(songs[idx]) + "\n" +
                     "<span class=\"isdntspan\">" + str(rec["text"]) +
                     "</span>\n")
    html += "</ul>\n\n"
    html += ("<div id=\"aelrangediv\"></div>\n" +
             "<div id=\"repsongtotaldiv\"></div>\n")
    return html


def automated_wt20_content(sasum):
    html = "<ul class=\"wt20list\">\n"
    songs = util.load_json_or_default(sasum["songs"], [])
    for song in songs:
        html += "<li>" + song_html(song) + "\n"
    if not songs:
        html += ("<p>All new music this week.<br/>" +
                 "Will recommend as collected.</p>")
    html += "</ul>\n\n"
    html += "<div id=\"aelrangediv\">\n"
    labs = [{"name":"Easiest", "fld":"easiest"},
            {"name":"Hardest", "fld":"hardest"},
            {"name":"Most Chill", "fld":"chillest"},
            {"name":"Most Amped", "fld":"ampest"}]
    for lab in labs:
        if sasum[lab["fld"]]:
            html += ("<span class=\"repsummarylabelspan\">" + lab["name"] +
                     ":</span>" + song_html(sasum[lab["fld"]]) + "<br/>\n")
    html += ("</div>\n<div id=\"repsongtotaldiv\">" + str(sasum["ttlsongs"]) +
             " songs synchronized to <a href=\"https://diggerhub.com\">" +
             "DiggerHub</a></div>\n")
    return html


def weekly_top20_content_html(sasum):
    digname = sasum["digname"]
    mdstart = month_and_day_from_dbtimestamp(sasum["start"])
    mdend = month_and_day_from_dbtimestamp(sasum["end"])
    presentation = "Curated" if sasum["curate"] else "Collected"
    tline = (presentation + " recommendations" +
             " <span id=\"hrtpspan\" class=\"datevalspan\"" +
             " data-plink=\"plink/wt20/" + sasum["digname"] + "/" +
             sasum["end"][0:10] + "\">" +
             mdstart + "-" + mdend +
             "<span>" + get_wt20_nav_link("prev", sasum) + "</span>" +
             "<span>" + get_wt20_nav_link("next", sasum) + "</span>" +
             "</span>")
    html = curated_wt20_content(sasum) or automated_wt20_content(sasum)
    return listener_report_page_html(digname, tline, html)


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
    stinf["replace"]["rundata = \"\""] = "rundata = " + json.dumps(sasum)
    return replace_and_respond(stinf)


def report_background_image():
    wknum = datetime.datetime.today().isocalendar()[1]
    adj = {"red":[0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0],
           "green":[0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2],
           "blue": [1.7,1.6,1.5,1.4,1.3,1.2,1.1,0.9]}
    wka = {key: val[(wknum + 1) % len(val)] for key, val in adj.items()}
    img = Image.open(mconf.rpbgimg).convert("RGB")
    red, green, blue = img.split()
    red = red.point(lambda i: i * wka["red"])
    green = green.point(lambda i: i * wka["green"])
    blue = blue.point(lambda i: i * wka["blue"])
    img = Image.merge('RGB', (red, green, blue))
    return img

def weekly_top20_image(sasum):
    songs = util.load_json_or_default(sasum["songs"], [])
    if sasum["curate"]:
        qr8 = util.load_json_or_default(sasum["curate"], {})
        recs = [r for r in qr8.get("rovrs", []) if r.get("recommended", "")]
        if recs:
            recs = qr8.get("rovrs", [])
            rsgs = []
            for idx, rec in enumerate(qr8["rovrs"]):
                if rec["recommended"]:
                    rsgs.append(songs[idx])
            songs = rsgs
    songs = songs[0:15]  # limited vertical space
    mtxt = "      " + sasum["digname"] + " recs week\n"
    for idx, song in enumerate(songs):
        mtxt += str(idx + 1) + ". " + song["ar"] + " - " + song["ti"] + "\n"
    if not songs:
        mtxt += "All new music this week"
    mtxt += "..."
    img = report_background_image()
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
        endts = endts + "T00:00:00Z"
        stdt = dbacc.ISO2dt(endts) - datetime.timedelta(days=7)
        startts = dbacc.dt2ISO(stdt)
        sasums = [{"aid":0, "digname":digname, "sumtype":"wt20", "songs":[],
                   "easiest":"", "hardest":"", "chillest":"", "ampest":"",
                   "curate":"", "start":startts, "end":endts, "ttlsongs":0}]
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


def acct_by_digname(digname):
    where = "WHERE digname = \"" + digname + "\""
    accts = dbacc.query_entity("DigAcc", where)
    if len(accts) > 0:
        digacc = dbacc.visible_fields(accts[0])
        return digacc
    return ""


def most_recent_songs(digacc):
    if not digacc:
        return ""
    # 5 weeks back ought to be enough for reasonable data
    dback = datetime.datetime.utcnow() - datetime.timedelta(days=35)
    where = ("WHERE aid = " + digacc["dsId"] +
             " AND modified >= \"" + dbacc.dt2ISO(dback) + "\"" +
             " ORDER BY modified DESC")
    songs = dbacc.query_entity("Song", where)
    return songs


def most_recent_bookmarks(digacc):
    if not digacc:
        return ""
    where = ("WHERE aid = " + digacc["dsId"] +
             " AND cs != \"Deleted\"" +
             " ORDER BY modified DESC LIMIT 100")
    bkmks = dbacc.query_entity("Bookmark", where)
    return bkmks


def personal_page_response(stinf, rdo):
    stinf["replace"]["$CONTENTHTML"] = REPORTFRAMEHTML
    stinf["replace"]["$REPORTHTML"] = PERSONALPAGEHTML
    stinf["replace"]["$RELROOT"] = stinf["replace"]["$RDR"]
    stinf["replace"]["$LATESTTOP20"] = ""
    stinf["replace"]["rundata = \"\""] = "rundata = " + json.dumps(rdo)
    return replace_and_respond(stinf)


def listener_page(stinf):
    pes = stinf["rawpath"].split("/")
    if len(pes) < 2:
        return fail404()
    digname = pes[1]
    logging.info("listener_page " + digname + " " + digname)
    digacc = acct_by_digname(digname)
    rdo = {"acct": digacc,
           "songs": most_recent_songs(digacc),
           "bkmks": most_recent_bookmarks(digacc)}
    return personal_page_response(stinf, rdo)


def bookmarks_page(stinf):
    logging.info("bookmarks_page " + stinf["rawpath"])
    digacc = ""
    pes = stinf["rawpath"].split("/")
    if len(pes) == 2:
        digname = pes[1]
        digacc = acct_by_digname(digname)
    rdo = {"acct": digacc,
           "songs": [],
           "bkmks": most_recent_bookmarks(digacc)}
    return personal_page_response(stinf, rdo)


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
    if not reldocroot or (stinf["path"].startswith("iosappstore") or
                          stinf["path"].startswith("beta")):
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
    if stinf["path"].startswith("bookmarks"):
        return bookmarks_page(stinf)
    return fail404()
