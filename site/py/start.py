""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring

import logging
import py.util as util

CACHE_BUST_PARAM = "v=210122"  # Updated via ../../build/cachev.js

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
  <link href="css/site.css?$CBPARAM" rel="stylesheet" type="text/css" />
</head>
<body id="bodyid">

<div id="outercontentdiv">
  <div id="contentdiv">
    <div id="splashdiv">

<p><b>Digger</b> plays songs from your music library that match your listening
context.  If you've ever wanted to access your music through a mixing panel
instead of searching folders, now you can. </p>

<p>To install, download one of the prebuilt executables below.  Or grab the
<a href="https://github.com/theriex/digger#digger">open source</a> and run
that. </p>

<div id="downloadsdiv">
<a href="downloads/digger-linux">digger-linux</a>
<a href="downloads/digger-macos">digger-macos</a>
<a href="downloads/digger-win.exe">digger-win.exe</a>
</div>

<p>Run the Digger music server, then surf to localhost:6980. </p>

    </div>
  </div>
</div>

</body>
</html>
"""

# path is everything after the root url slash.
def startpage(path, refer):
    stinf = {
        "rawpath": path,
        "path": path.lower(),
        "refer": refer or "",
        "replace": {
            "$CBPARAM": CACHE_BUST_PARAM,
            "$SITEPIC": "img/appicon.png?" + CACHE_BUST_PARAM,
            "$TITLE": "DiggerHub"}}
    if stinf["refer"]:
        logging.info("startpage referral: " + refer)
    if path and not path.startswith("index.htm"):
        logging.info("startpage path " + path + " not known.")
    html = INDEXHTML
    for dcode, value in stinf["replace"].items():
        html = html.replace(dcode, value)
    return util.respond(html)
