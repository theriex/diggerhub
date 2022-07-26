""" Check the application log for errors. """
#pylint: disable=wrong-import-position
#pylint: disable=wrong-import-order
#pylint: disable=missing-function-docstring
#pylint: disable=invalid-name
import datetime
import os.path
import py.mconf as mconf
import logging
import logging.handlers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(module)s %(asctime)s %(message)s',
    handlers=[logging.handlers.TimedRotatingFileHandler(
        mconf.logsdir + "plg_logcheck.log", when='D', backupCount=10)])
import py.util as util

# Matches the cron job timing setup
TIMEWINDOW = datetime.timedelta(minutes=-60)


def mail_error_notice(txt):
    util.send_mail(None, "DiggerHub logcheck summary", txt,
                   domain=mconf.domain)


def check_line_for_errs(summary, line, markers, skips):
    for marker in markers:
        if marker in line:
            iserr = True
            for skip in skips:
                if skip in line:
                    iserr = False
            if iserr:
                summary[marker] += " " + line


def search_log_file(lfp, srchts, markers, skips):
    """ search the log file path filtering by the search timestamp prefix """
    if not os.path.isfile(lfp):
        txt = "Log file " + lfp + " not found.\n"
    else: # log file exists
        summary = {}
        for marker in markers:
            summary[marker] = ""
        lc = 0
        with open(lfp) as f:
            for line in f.readlines():
                if srchts in line:  # relevant log line
                    lc += 1
                    check_line_for_errs(summary, line, markers, skips)
        txt = "Checked " + str(lc) + " lines from " + lfp + "\n"
        notify = False
        for marker in markers:
            if summary[marker]:
                notify = True
                txt += summary[marker]
        if notify:
            mail_error_notice(txt)
    logging.info(txt)
    return txt


def check_log_file(lfp, tfmt, markers, skips):
    """ figure out log file path and timestamp search prefix, return search """
    toth = datetime.datetime.now().replace(microsecond=0, second=0, minute=0)
    if not toth.hour:  # hour zero, switch to rollover log file if it exists
        rls = (toth + datetime.timedelta(hours=-24)).strftime("%Y-%m-%d")
        if os.path.isfile(lfp + "." + rls):
            lfp = lfp + "." + rls  # rolled over log file path
    toth = toth + TIMEWINDOW  # now top of the previous hour
    srchts = toth.strftime(tfmt)
    result = search_log_file(lfp, srchts, markers, skips)
    return result


def check_log_files():
    appsrch = check_log_file(mconf.logsdir + "plg_application.log",
                             "%Y-%m-%d %H:",
                             ["ERROR", "WARNING", "ValueError"],
                             [])
    errsrch = check_log_file(mconf.errsdir + "error.log",
                             " %b %d %H:",
                             [" [:error] "],
                             ["PCRE limits exceeded"])
    return appsrch + "\n" + errsrch + "\n"


check_log_files()
