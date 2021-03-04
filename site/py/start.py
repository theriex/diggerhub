""" Return appropriate start page content """
#pylint: disable=line-too-long
#pylint: disable=logging-not-lazy
#pylint: disable=missing-function-docstring

import logging
import py.util as util

CACHE_BUST_PARAM = "v=210304"  # Updated via ../../build/cachev.js

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

<div id="topsectiondiv">
  <div id="logodiv"><img src="img/appicon.png"/></div>
  <!-- login has to be an actual form to enable remembered passwords -->
  <div id="topactiondiv">
    <form id="loginform" method="post" action="redirlogin">
      <div id="loginparaminputs"></div>
      <div id="loginvisualelementsdiv">
        <div class="onelineformdiv">
          <input type="email" class="lifin" name="emailin" id="emailin"
                 size="20" placeholder="nospam@example.com"/>
          <!-- no onchange submit for password. breaks autoforms on safari -->
          <input type="password" class="lifin" name="passin" id="passin"
                 size="12" placeholder="*password*"/>
          <input value="LogIn" type="submit" class="buttonstyle" id="loginb"/>
        </div>
        <div id="acctmsglinediv"></div>
        <div id="loginbuttonsdiv" class="formbuttonsdiv">
          <div id="loginlinksdiv"/>
        </div>
      </div> <!-- loginvisualelementsdiv -->
    </form>
  </div>
</div>


<div id="outercontentdiv">
  <div id="contentdiv">
    <div id="splashdiv">

<p><b>Digger</b> plays songs from your music library that match your listening
context.  If you've ever wanted to access your music through a mixing panel
instead of searching folders, now you can. </p>

<p>To install, download the
<a href="https://github.com/theriex/digger#digger">open source</a> or one
of the prebuilt executables below. </p>

<div id="downloadsdiv">
<a href="downloads/digger-linux">digger-linux</a>
<a href="downloads/Digger.dmg">Digger.dmg</a>
<a href="downloads/digger-win.exe">digger-win.exe</a>
</div>

<p>Run the Digger music server, then open
<a href="http://localhost:6980"
   onclick="window.open('http://localhost:6980');return false;"/>
localhost:6980</a>. </p>

    </div>
  </div>
</div>

<script src="js/jtmin.js?$CBPARAM"></script>
<script src="js/app.js?$CBPARAM"></script>
<script>
  app.init();
</script>

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
