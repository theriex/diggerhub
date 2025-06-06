""" Main API switchboard with all entrypoints """
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=wrong-import-position
#pylint: disable=wrong-import-order
#pylint: disable=ungrouped-imports
#pylint: disable=consider-using-from-import
import py.mconf as mconf
import logging
import logging.handlers
# logging may or may not have been set up, depending on environment.
logging.basicConfig(level=logging.INFO)
# Tune logging so it works the way it should, even if set up elsewhere
handler = logging.handlers.TimedRotatingFileHandler(
    mconf.logsdir + "plg_application.log", when='D', backupCount=10)
handler.setFormatter(logging.Formatter(
    '%(levelname)s %(module)s %(asctime)s %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
import flask
import py.util as util
import py.start as start
import py.appdat as appdat


# Create a default entrypoint for the app.
app = flask.Flask(__name__)

######################################################################
#  API:
#

####### Open site endpoints:

@app.route('/api/version')
def appversion():
    return util.version()

@app.route('/api/doctext')
def doctext():  # params: docurl
    return util.doctext()

####### Account actions:

@app.route('/api/newacct', methods=['GET', 'POST'])
def newacct():  # params: firstname, email, password
    return util.secure(util.newacct)

@app.route('/api/updacc', methods=['GET', 'POST'])
def updacc():  # params: auth, DigAcc
    return util.secure(util.updacc)

@app.route('/api/acctok', methods=['GET', 'POST'])
def acctok():  # params: email, password
    return util.secure(util.acctok)

@app.route('/api/mailpwr', methods=['GET', 'POST'])
def mailpwr():  # params: email, returl
    return util.secure(util.mailpwr)

@app.route('/api/emsupp', methods=['GET', 'POST'])
def emsupp():  # params: auth, subj, body
    return util.secure(util.emsupp)

@app.route('/api/deleteme', methods=['GET', 'POST'])
def deleteme():  # params: auth, tzoff
    return util.secure(util.deleteme)

####### Local song data and collaboration actions:

@app.route('/api/hubsync', methods=['GET', 'POST'])
def hubsync():  # params: auth, acct + zero or more songs
    return util.secure(appdat.hubsync)

@app.route('/api/songfetch')
def songfetch():  # params: auth, fvs
    return util.secure(appdat.songfetch)

@app.route('/api/savesongs', methods=['GET', 'POST'])
def savesongs():  # params: auth, songs
    return util.secure(appdat.savesongs)

@app.route('/api/fangrpact', methods=['GET', 'POST'])
def fangrpact():  # params: auth, action, digname
    return util.secure(appdat.fangrpact)

@app.route('/api/fancollab', methods=['GET', 'POST'])
def fancollab():  # params: auth, mfid, ctype
    return util.secure(appdat.fancollab)

@app.route('/api/fanmsg', methods=['GET', 'POST'])
def fanmsg():  # params: auth, action, idcsv
    return util.secure(appdat.fanmsg)

@app.route('/api/musfdat')
def musfdat():  # params: auth, gid, since
    return util.secure(appdat.musfdat)

@app.route('/api/songttls', methods=['GET', 'POST'])
def songttls():  # params: auth
    return util.secure(appdat.songttls)

@app.route('/api/suggdown')
def suggdown():  # params: auth, suggtype
    return util.secure(appdat.suggdown)

@app.route('/api/betastat', methods=['GET', 'POST'])
def betastat():  # params: auth if post
    return appdat.betastat()


####### Spotify song data and collaboration actions:

@app.route('/api/impsptracks', methods=['GET', 'POST'])
def impsptracks():  # params: auth, items
    return util.secure(appdat.impsptracks)

@app.route('/api/spabimp', methods=['GET', 'POST'])
def spabimp():  # params: auth, abinf
    return util.secure(appdat.spabimp)

@app.route('/api/playerr', methods=['GET', 'POST'])
def playerr():  # params: auth, type, spid, error
    return util.secure(appdat.playerr)

@app.route('/api/songtip', methods=['GET', 'POST'])
def songtip():  # params: auth, songid
    return util.secure(appdat.songtip)


####### Bookmark access

@app.route('/api/bookmarks')
def bookmarks():  # params: accid, befiso, collstat, bmrkid
    return appdat.bookmarks()

@app.route('/api/updbmrk', methods=['GET', 'POST'])
def updbmrk():  # params: auth, Bookmark
    return util.secure(appdat.updbmrk)


######################################################################
#  General site access
#

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST'])
def startpage(path):
    if path.startswith("api/bd"):  # leading slash stripped in path match
        return util.secure(lambda: appdat.backdat(path))
    if (path.startswith("api/sa") or   # see top.js hcc.hubSyncEndpoint
        path.startswith("api/pa") or
        path.startswith("api/ua") or
        path.startswith("api/da")) :   # support release version 1.5.3
        return util.secure(lambda: appdat.hubsync(path))
    refer = flask.request.referrer or ""
    return util.secure(lambda: start.startpage(path, refer))


# Hook for calling the app directly using python on the command line, which
# can be useful for unit testing.  In the deployed app, a WSGI browser
# interface like Gunicorn or Passenger serves the app.
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
