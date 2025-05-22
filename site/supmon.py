""" Check whatever support needs to be monitoring """
#pylint: disable=wrong-import-order
#pylint: disable=wrong-import-position
#pylint: disable=missing-function-docstring
#pylint: disable=logging-not-lazy
#pylint: disable=consider-using-from-import
#pylint: disable=invalid-name
import py.mconf as mconf
import logging
import logging.handlers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(module)s %(asctime)s %(message)s',
    handlers=[logging.handlers.TimedRotatingFileHandler(
        mconf.logsdir + "plg_supmon.log", when='D', backupCount=10)])
import py.util as util
import py.dbacc as dbacc
import datetime
import json


def elapsed_days_since(timestamp):
    diff = datetime.datetime.utcnow() - dbacc.ISO2dt(timestamp)
    return diff.days


def check_active_beta_testers():
    body = ""
    where = ("WHERE sitype LIKE \"beta%\"" +
             " AND (status = \"Active\" OR status = \"Queued\")" +
             " ORDER BY created")
    stis = dbacc.query_entity("StInt", where)
    for sti in stis:
        tsum = ("DigAcc" + str(sti["aid"]) + " " + sti["email"] +
                " status " + sti["status"] + "\n")
        if sti["stdat"]:
            stdat = json.loads(sti["stdat"])
            if stdat["activated"]:
                tsum += "    activated " + stdat["activated"]
                days = elapsed_days_since(stdat["activated"])
                tsum += " (" + str(days) + " days)\n"
            if stdat["aftertest"]:
                tsum += "    *** WAITING FOR GIFTCARD ***\n"
                tsum += "    " + sti["stdat"] + "\n"
        body += tsum
    subj = "beta test activity summary"
    util.send_mail(util.supnm() + "@" + util.domnm(), subj, body,
                   domain=util.domnm())


def run_support_checks():
    check_active_beta_testers()

# run it
run_support_checks()
