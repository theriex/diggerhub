""" Check the application log for errors. """
#pylint: disable=wrong-import-position
#pylint: disable=wrong-import-order
#pylint: disable=missing-function-docstring
#pylint: disable=invalid-name
#pylint: disable=consider-using-from-import
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
import re
import argparse

# Matches the cron job timing setup
TIMEWINDOW = datetime.timedelta(minutes=-60)

def mail_error_notice(txt):
    util.send_mail(None, "DiggerHub logcheck summary", txt,
                   domain=mconf.domain)


def check_line_for_errs(ctx, line, markers, skips):
    for marker in markers:
        if re.search(marker, line):
            iserr = True
            for skip in skips:
                if skip in line:
                    iserr = False
            if iserr:
                ctx["errc"] += 1
                ctx["info"] += line  # includes newline at end


def is_relevant_log_line(lc, srchts, line):
    # If the relevant timestamp is in the line, then it should be checked.
    # If you have checked at least one error line and there is an indented
    # detail line after that matching a search term, then that line should
    # also be checked.
    # print("irll lc " + str(lc) + " " + srchts + " " + line)
    return ((srchts in line) or
            (line.startswith("  ") and lc > 0))


def search_log_file(lfp, srchts, markers, skips, ctx):
    """ search the log file path filtering by the search timestamp prefix """
    ctx["errc"] = 0  # reset any previous count
    if not os.path.isfile(lfp):
        ctx["errc"] += 1
        ctx["info"] += "Log file " + lfp + " not found.\n"
    else: # log file exists
        ctx["info"] += "Checking " + lfp + " lines for \"" + srchts + "\"\n"
        mlc = 0  # matched line count for srchts
        with open(lfp, encoding="utf-8") as f:
            for line in f.readlines():
                if is_relevant_log_line(mlc, srchts, line):
                    mlc += 1
                    check_line_for_errs(ctx, line, markers, skips)
        ctx["info"] += "Finished checking " + lfp + "\n"
        ctx["info"] += str(mlc) + " lines matching \"" + srchts + "\"\n"
        ctx["info"] += str(ctx["errc"]) + " expression matches found.\n"


def check_log_file(lfp, tfmt, markers, skips, ctx):
    """ figure out log file path and timestamp search prefix, return search """
    stm = datetime.datetime.now().replace(microsecond=0, second=0, minute=0)
    stm = stm + TIMEWINDOW  # now top of the previous hour
    if ctx["args"] is not None and ctx["args"].toth is not None:
        stm = stm.replace(hour=ctx["args"].toth)
    if not stm.hour:  # hour zero, switch to rollover log file if it exists
        rls = (stm + datetime.timedelta(hours=-24)).strftime("%Y-%m-%d")
        if os.path.isfile(lfp + "." + rls):
            lfp = lfp + "." + rls  # rolled over log file path
    srchts = stm.strftime(tfmt)
    search_log_file(lfp, srchts, markers, skips, ctx)


def check_log_files():
    clap = argparse.ArgumentParser(description="""
        Search the application and server error logs from the top of the
        current hour or the specified hour.""")
    clap.add_argument("-t", "--toth", help="Hour number 0-23 to search for",
                      type=int)
    clap.add_argument("-p", "--prout", help="Print output to console",
                      action="store_true")
    ctx = {"info":"", "errc":0, "args":clap.parse_args()}
    if ctx["args"] is not None:
        ctx["info"] += "args: " + str(ctx["args"]) + "\n"
    check_log_file(mconf.logsdir + "plg_application.log", "%Y-%m-%d %H:",
                   ["ERROR", "WARNING",
                    r"File \".*\.py\", line \d+", "ValueError",
                    r"hubsync\s\d+.*seconds"],
                   [], ctx)
    check_log_file(mconf.errsdir + "error.log", " %b %d %H:",
                   [" [error] ", "severity"],
                   [], ctx)
    logging.info(ctx["info"])
    if ctx["errc"]:
        if ctx["args"] is not None and ctx["args"].prout:
            print(ctx["info"])
        else:
            mail_error_notice(ctx["info"])


# If an hour number (0-23) is specified as a parameter, then the logs are
# searched based on that hour, otherwise the current top of the hour is used.
check_log_files()
