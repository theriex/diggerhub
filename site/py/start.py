""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring

import logging
import py.util as util

CACHE_BUST_PARAM = "v=201203"  # Updated via ../../build/cachev.js

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
</head>
<body id="bodyid">

<div id="outercontentdiv">
  <div id="contentdiv">
    <div id="splashdiv">

<p>Digger plays songs from your music library that match your current
listening context.  If you've ever wanted to access your music through a
mixing panel instead of flipping through a list of files, this is for
you. </p>

<p>Digger runs as an <a href="https://github.com/theriex/digger">open
source</a> music server serving up your local music files to your browser.
If you already have node.js, you can download and run the source directly.
Or you can download and run one of these prebuilt packages:</p>

<div id="downloadsdiv"></div>

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
            "$TITLE": "Digger"}}
    if stinf["refer"]:
        logging.info("startpage referral: " + refer)
    if path and not path.startswith("index.htm"):
        logging.info("startpage path " + path + " not known.")
    html = INDEXHTML
    for dcode, value in stinf["replace"].items():
        html = html.replace(dcode, value)
    return util.respond(html)
