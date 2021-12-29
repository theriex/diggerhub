""" General use request processing functions and utilities. """
#pylint: disable=missing-function-docstring
#pylint: disable=invalid-name
#pylint: disable=logging-not-lazy
#pylint: disable=too-many-arguments

import logging
import hmac
import json
from json.decoder import JSONDecodeError
import re
import ssl
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import string
import random
import flask
import py.dbacc as dbacc
import py.mconf as mconf

def version():
    return "v0.9.19"


def srverr(msg, code=400):
    # 400 Bad Request
    # 405 Method Not Allowed
    resp = flask.make_response(msg)
    resp.mimetype = "text/plain"
    resp.status_code = int(code)
    return resp


def serve_value_error(ve, quiet=False):
    if not quiet:
        logging.exception("serve_value_error")
    return srverr(str(ve))


def respond(contentstr, mimetype="text/html"):
    # flask.Response defaults to HTML mimetype, so just returning a string
    # from a flask endpoint will probably work.  Best to route everything
    # through here and set it explicitely just in case
    resp = flask.make_response(contentstr)
    resp.mimetype = mimetype
    return resp


def load_json_or_default(jstxt, dval=None):
    retval = dval
    if jstxt:
        try:
            retval = json.loads(jstxt)
        except JSONDecodeError:
            pass
    return retval


def safe_JSON(obj, audience="public"):  # "private" includes personal info
    if isinstance(obj, dict) and obj.get("dsType"):
        obj = dbacc.visible_fields(obj, audience)
    return json.dumps(obj)


def respJSON(jsontxt, audience="public"):  # "private" includes personal info):
    if isinstance(jsontxt, dict):
        jsontxt = "[" + safe_JSON(jsontxt, audience) + "]"
    elif isinstance(jsontxt, list):
        # list may contain a token or other non-db dict
        jsontxt = [safe_JSON(obj, audience) for obj in jsontxt]
        jsontxt = "[" + ",".join(jsontxt) + "]"
    return respond(jsontxt, mimetype="application/json")


def get_connection_service(svcname):
    cs = dbacc.cfbk("AppService", "name", svcname)
    if not cs:
        # create needed placeholder for administrators to update
        cs = dbacc.write_entity({"dsType": "AppService",
                                 "name": svcname})
    return cs


def make_password_hash(emaddr, pwd, cretime):
    hasher = hmac.new(pwd.encode("utf8"), digestmod="sha512")
    hasher.update((emaddr + "_" + cretime).encode("utf8"))
    return hasher.hexdigest()


def token_for_user(digacc):
    ts = get_connection_service("TokenSvc")
    hasher = hmac.new(ts["csec"].encode("utf8"), digestmod="sha512")
    hasher.update((digacc["email"] + "_" + digacc["phash"]).encode("utf8"))
    token = hasher.hexdigest()
    token = token.replace("+", "-")
    token = token.replace("/", "_")
    token = token.replace("=", ".")
    return token


# No terminating '/' returned.  Caller specifies for clarity.  It is probable
# that flask is running on its own port, with the web server providing proxy
# access to it, so port information is removed.
def site_home():
    url = flask.request.url
    elements = url.split("/")[0:3]
    if ":" in elements[2]:
        elements[2] = elements[2].split(":")[0]  # strip port info
    # replace port for local development.  Makes testing easier.
    if elements[2] in ["127.0.0.1", "localhost"]:
        elements[2] += ":8080"
    return "/".join(elements)


def is_development_server():
    info = {"isdev":False, "why":"No development conditions matched"}
    if flask.has_request_context():
        if re.search(r"\:\d{4}", flask.request.url):
            info["isdev"] = True
            info["why"] = "flask.request.url has a 4 digit port number)"
    # Do not negatively match on the server home directory to determine if
    # development.  May change with the hosting user.
    if info["isdev"]:
        return info
    return False


def secure(func):
    url = flask.request.url
    logging.debug("secure url: " + url)
    if url.startswith('https') or is_development_server():
        return func()
    return srverr("Request must be over https", 405)


# Apparently with some devices/browsers it is possible for the email
# address used for login to arrive encoded.  Decode and lowercase.
def normalize_email(emaddr):
    if emaddr:
        if "%40" in emaddr:
            emaddr = urllib.parse.unquote(emaddr)
        emaddr = emaddr.lower()
    return emaddr


def val_in_csv(val, csv):
    if not csv:
        return False
    val = str(val)
    csv = str(csv)
    if csv == val:
        return True
    if csv.startswith(val + ","):
        return True
    index = csv.find("," + val)
    if index >= 0:
        return True
    return False


def csv_to_list(csv):
    if not csv:
        return []
    csv = str(csv)
    if not csv.strip():  # was all whitespace. treat as empty
        return []
    return csv.split(",")


def first_group_match(expr, text):
    m = re.match(expr, text)
    if m:
        return m.group(1)
    return None


def authenticate():
    emaddr = dbacc.reqarg("an", "DigAcc.email")
    if not emaddr:
        emaddr = dbacc.reqarg("email", "DigAcc.email")
    if not emaddr:
        emaddr = dbacc.reqarg("emailin", "DigAcc.email")
    if not emaddr:
        raise ValueError("'an' or 'email' parameter required")
    emaddr = normalize_email(emaddr)
    digacc = dbacc.cfbk("DigAcc", "email", emaddr)
    if not digacc:
        raise ValueError(emaddr + " not found")
    reqtok = dbacc.reqarg("at", "string")
    if not reqtok:
        reqtok = dbacc.reqarg("token", "string")
    if not reqtok:
        password = dbacc.reqarg("password", "string")
        if not password:
            password = dbacc.reqarg("passin", "string")
        if not password:
            raise ValueError("Access token or password required")
        phash = make_password_hash(emaddr, password, digacc["created"])
        if phash == digacc["phash"]:  # authenticated, rebuild token
            reqtok = token_for_user(digacc)
        else: # failing now due to lack of token, log for analysis if needed
            logging.info(digacc["email"] + " password hash did not match")
            logging.info("  DigAcc[\"phash\"]: " + digacc["phash"])
            logging.info("      Server phash: " + phash)
    srvtok = token_for_user(digacc)
    if reqtok != srvtok:
        logging.info(digacc["email"] + " authenticated token did not match")
        logging.info("  reqtok: " + reqtok)
        logging.info("  srvtok: " + srvtok)
        raise ValueError("Wrong password")
    return digacc, srvtok


def administrator_auth():
    digacc, _ = authenticate()
    cs = get_connection_service("Administrators")
    if not val_in_csv(digacc["dsId"], cs["data"]):
        raise ValueError("Not authorized as admin")


# If the caller is outside of the context of a web request, then the domain
# must be passed in.  The support address must be set up in the hosting env.
def send_mail(emaddr, subj, body, domain=None, sender="support", replyto=""):
    domain = domain or flask.request.url.split("/")[2]
    fromaddr = "@".join([sender, domain])
    emaddr = emaddr or fromaddr
    if is_development_server():
        logging.info("send_mail ignored dev server send to " + emaddr +
                     "\nsubj: " + subj +
                     "\nbody: " + body)
        return
    # On server, so avoid logging anything containing auth info.
    msg = MIMEText(body)
    msg["Subject"] = subj
    msg["From"] = fromaddr
    msg["To"] = emaddr
    if replyto:
        msg.add_header('reply-to', replyto)
    sctx = ssl.create_default_context()  # validate host and certificates
    # 465: secured with SSL. 587: not secured, but supports STARTTLS
    with smtplib.SMTP_SSL(mconf.email["smtp"], 465, context=sctx) as smtp:
        smtp.login(fromaddr, mconf.email[sender])
        smtp.sendmail(fromaddr, emaddr, msg.as_string())


def verify_new_email_valid(emaddr):
    # something @ something . something
    if not re.match(r"[^@]+@[^@]+\.[^@]+", emaddr):
        raise ValueError("Invalid email address: " + emaddr)
    if emaddr == "support@diggerhub.com":
        raise ValueError("Address reserved for default account")
    existing = dbacc.cfbk("DigAcc", "email", emaddr)
    if existing:
        raise ValueError("Email address already used")
    return emaddr


def make_activation_code():
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(30))


def url_for_mail_message():
    returl = dbacc.reqarg("returl", "string")
    if not returl:
        returl = site_home()
    else:
        returl = urllib.parse.unquote(returl)
    return returl


def send_activation_email(digacc, friend=None):
    acturl = (url_for_mail_message() + "?actcode=" + digacc["actcode"] +
              "&an=" + urllib.parse.quote(digacc["email"]) +
              "&at=" + token_for_user(digacc))
    if friend:
        logging.info("Invitation mail -> " + digacc["email"])
        subj = friend["firstname"] + " has invited you to join DiggerHub"
        body = ("Hello " + digacc["firstname"] + ",\n\n" +
                friend["firstname"] + " (" + friend["email"] +
                ") has invited you to join DiggerHub!\n\n" +
                "Use this link to access your account:\n\n" +
                acturl + "\n\n" +
                "Welcome to DiggerHub!\n")
    else:
        logging.info("Activation mail -> " + digacc["email"])
        subj = "DiggerHub account activation link"
        body = ("Use this link to activate your DiggerHub account:\n\n" +
                acturl + "\n\n" +
                "Welcome to DiggerHub!\n")
    send_mail(digacc["email"], subj, body)


def update_email_and_password(digacc, emaddr, pwd, friend=None):
    emaddr = normalize_email(emaddr)
    if pwd and pwd.lower() == "noval":
        pwd = ""
    emchg = emaddr and emaddr != digacc["email"]
    if ((not (emchg or pwd)) and (digacc["email"] != "placeholder")):
        return "nochange"  # not updating credentials so done
    if emaddr and emaddr != digacc["email"] and not pwd:
        raise ValueError("Password required to change email")
    if not pwd or len(pwd) < 6:
        raise ValueError("Password must be at least 6 characters")
    change = "password"
    if emaddr != digacc["email"]:
        change = "email"
        verify_new_email_valid(emaddr)
        digacc["email"] = emaddr
        digacc["status"] = "Pending"  # need to confirm new email address
        digacc["actsends"] = ""       # reset send attempts log
        digacc["actcode"] = make_activation_code()
    # if either email or password changed, always update the phash
    digacc["phash"] = make_password_hash(digacc["email"], pwd,
                                         digacc["created"])
    if digacc["status"] == "Pending":
        send_activation_email(digacc, friend)
    return change


def set_fields_from_reqargs(fields, obj, ftype="string"):
    for fld in fields:
        val = dbacc.reqarg(fld, ftype)
        if not val:
            val = dbacc.reqarg(fld + "in", ftype)
        if val:
            if ftype == "string" and val.lower() == "noval":
                val = ""  # remove any existing value
            obj[fld] = val
    return obj


def eedq(val):  #escape embedded double quotes in value string
    return val.replace("\"", "\\\"")


def fill_missing_fields(fields, src, trg):
    for fld in fields:
        if not trg.get(fld):
            trg[fld] = src.get(fld, "")
    return trg


def update_account_fields(digacc):
    set_fields_from_reqargs(
        ["hubdat", "firstname", "hashtag", "kwdefs", "igfolds", "settings",
         "musfs"],
        digacc)
    if not digacc.get("kwdefs") or digacc["kwdefs"] == "{}":
        digacc["kwdefs"] = json.dumps(dbacc.initial_keywords())


def checkActivationCode(digacc, save=False):
    actcode = dbacc.reqarg("actcode", "string")
    if actcode:
        logging.info(digacc["email"] + " actcode: " + actcode)
        if actcode == digacc["actcode"]:
            digacc["status"] = "Active"
            if save:
                digacc = dbacc.write_entity(digacc, digacc["modified"])
        else:
            logging.info("actcode did not match: " + digacc["actcode"])
    return digacc


def runtime_decorate_account(digacc):
    """ Add other general reference server info used by client. """
    digacc["hubVersion"] = version()
    digacc["diggerVersion"] = version()
    hubdat = json.loads(digacc.get("hubdat") or "{}")
    spotify = get_connection_service("spotify")
    if not hubdat.get("spa"):
        hubdat["spa"] = {}
    hubdat["spa"]["clikey"] = spotify.get("ckey")  # not confidential
    hubdat["spa"]["returi"] = spotify.get("data")  # auth callback uri
    digacc["hubdat"] = json.dumps(hubdat)


############################################################
## API endpoints:

def newacct():
    try:
        emaddr = dbacc.reqarg("email", "DigAcc.email", required=True)
        emaddr = normalize_email(emaddr)
        verify_new_email_valid(emaddr)
        pwd = dbacc.reqarg("password", "string", required=True)
        dbacc.reqarg("firstname", "DigAcc.firstname", required=True)
        cretime = dbacc.nowISO()
        digacc = {"dsType":"DigAcc", "created":cretime,
                  "email":"placeholder", "phash":"whatever"}
        update_email_and_password(digacc, emaddr, pwd)
        update_account_fields(digacc)
        digacc = dbacc.write_entity(digacc)
        runtime_decorate_account(digacc)
        token = token_for_user(digacc)
    except ValueError as e:
        return serve_value_error(e)
    return respJSON([digacc, token], audience="private")


def acctok():
    try:
        digacc, token = authenticate()
        digacc = checkActivationCode(digacc, save=True)
        runtime_decorate_account(digacc)
    except ValueError as e:
        logging.info("acctok signin failed: " + str(e))
        return serve_value_error(e, quiet=True)
    return respJSON([digacc, token], audience="private")


def mailactcode():
    try:
        digacc, _ = authenticate()
        send_activation_email(digacc)
    except ValueError as e:
        logging.info("mailactcode failed: " + str(e))
        return serve_value_error(e)
    return respJSON("[]")


def mailpwr():
    try:
        subj = "DiggerHub.com account password reset link"
        emaddr = dbacc.reqarg("email", "DigAcc.email", required=True)
        returl = url_for_mail_message()
        body = "You asked to reset your DiggerHub account password.\n\n"
        user = dbacc.cfbk("DigAcc", "email", emaddr)
        if user:
            logging.info("mailpwr sending access link to " + emaddr)
            body += "Use this link to access the settings for your account: "
            body += (returl + "?an=" + urllib.parse.quote(user["email"]) +
                     "&at=" + token_for_user(user) + "\n\n")
        else:
            logging.info("mailpwr no account found for " + emaddr)
            body += "You do not have an account for " + emaddr + ". "
            body += "Either you have not signed up yet, or you used "
            body += "a different email address.  To create an account "
            body += "visit " + returl + "\n\n"
        send_mail(emaddr, subj, body)
    except ValueError as e:
        return serve_value_error(e)
    return respJSON("[]")


def emsupp():
    try:
        digacc, _ = authenticate()
        subj = dbacc.reqarg("subj", "string", required=True)
        subj = urllib.parse.unquote(subj)
        body = dbacc.reqarg("body", "string", required=True)
        body = urllib.parse.unquote(body)
        sendhdr = "From " + digacc["firstname"] + " " + digacc["email"] + "\n"
        sendhdr += "Sent " + dbacc.nowISO()
        body = sendhdr + "\n" + body
        send_mail("support@diggerhub.com", subj, body)
    except ValueError as e:
        logging.info("emsupp failed: " + str(e))
        return serve_value_error(e)
    return respJSON("[]")


def updacc():
    try:
        digacc, token = authenticate()
        emaddr = dbacc.reqarg("updemail", "DigAcc.email") or digacc["email"]
        chg = update_email_and_password(digacc, emaddr,
                                        dbacc.reqarg("updpassword", "string"))
        if chg != "nochange":
            logging.info("Changing " + chg + " for " + digacc["email"])
        update_account_fields(digacc)
        digacc = checkActivationCode(digacc)
        digacc = dbacc.write_entity(digacc, digacc["modified"])
        runtime_decorate_account(digacc)
        token = token_for_user(digacc)    # return possibly updated token
    except ValueError as e:
        return serve_value_error(e)
    return respJSON([digacc, token], audience="private")
