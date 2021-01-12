""" Autogenerated db CRUD and related utilities """
########################################
#
#       D O   N O T   E D I T
#
# This file was written by makeMySQLCRUD.js.  Any changes should be made there.
#
########################################

#pylint: disable=line-too-long
#pylint: disable=too-many-lines
#pylint: disable=trailing-newlines
#pylint: disable=wrong-import-position
#pylint: disable=wrong-import-order
#pylint: disable=invalid-name
#pylint: disable=missing-function-docstring
#pylint: disable=consider-using-in
#pylint: disable=logging-not-lazy
#pylint: disable=inconsistent-return-statements
#pylint: disable=too-many-return-statements
#pylint: disable=too-many-branches
#pylint: disable=too-many-locals
#pylint: disable=unused-argument
import logging
import flask
import re
import datetime
import pickle
import mysql.connector
import py.mconf as mconf

# Notes:
# (1) In general, all processing that might raise a mysql.connector.Error is
# wrapped to raise a ValueError instead, to support callers working at a
# higher level of CRUD abstraction.  The general processing contruct
#    except mysql.connector.Error as e:
#        raise ValueError from e
# is not used for this purpose because it produces an undecorated ValueError
# without the str(e) text, making it harder to track down what the problem
# actually was.  The source can be found from the Error __context__, but
# that is also set when raising a new Error, so the general use here is
#        raise ValueError(str(e) or "No mysql error text")

# Reserved database fields used for every instance:
#  - dsId: a long int, possibly out of range of a javascript integer,
#    possibly non-sequential, uniquely identifying an entity instance.
#    The entity type + dsId uniquely identifies an object in the system.
#  - created: An ISO timestamp when the instance was first written.
#  - modified: An ISO timestamp followed by ';' followed by mod count.
#  - batchconv: Arbitray string for batch database conversion.
dbflds = {"dsId": {"pt": "dbid", "un": True, "dv": 0},
          "created": {"pt": "string", "un": False, "dv": ""},
          "modified": {"pt": "string", "un": False, "dv": ""},
          "batchconv": {"pt": "string", "un": False, "dv": ""}}

entdefs = {
    "DigAcc": {  # Digger Hub access account
        "dsId": {"pt": "dbid", "un": True, "dv": 0},
        "created": {"pt": "string", "un": False, "dv": ""},
        "modified": {"pt": "string", "un": False, "dv": ""},
        "batchconv": {"pt": "string", "un": False, "dv": ""},
        "email": {"pt": "email", "un": True, "dv": ""},
        "phash": {"pt": "string", "un": False, "dv": ""},
        "status": {"pt": "string", "un": False, "dv": ""},
        "actsends": {"pt": "string", "un": False, "dv": ""},
        "actcode": {"pt": "string", "un": False, "dv": ""},
        "lastsync": {"pt": "string", "un": False, "dv": ""},
        "firstname": {"pt": "string", "un": False, "dv": ""},
        "hashtag": {"pt": "UnkownPyType!", "un": True, "dv": ""},
        "kwdefs": {"pt": "string", "un": False, "dv": ""},
        "igfolds": {"pt": "string", "un": False, "dv": ""},
        "settings": {"pt": "string", "un": False, "dv": ""}
    },
    "Song": {  # Rating and play information
        "dsId": {"pt": "dbid", "un": True, "dv": 0},
        "created": {"pt": "string", "un": False, "dv": ""},
        "modified": {"pt": "string", "un": False, "dv": ""},
        "batchconv": {"pt": "string", "un": False, "dv": ""},
        "aid": {"pt": "dbid", "un": False, "dv": 0},
        "path": {"pt": "string", "un": False, "dv": ""},
        "ti": {"pt": "string", "un": False, "dv": ""},
        "ar": {"pt": "string", "un": False, "dv": ""},
        "ab": {"pt": "string", "un": False, "dv": ""},
        "el": {"pt": "int", "un": False, "dv": 0},
        "al": {"pt": "int", "un": False, "dv": 0},
        "kws": {"pt": "string", "un": False, "dv": ""},
        "rv": {"pt": "int", "un": False, "dv": 0},
        "fq": {"pt": "string", "un": False, "dv": ""},
        "lp": {"pt": "string", "un": False, "dv": ""},
        "nt": {"pt": "string", "un": False, "dv": ""}
    }
}


entkeys = {
    "DigAcc": ["email", "hashtag"],
    "Song": []
}


cachedefs = {
    "DigAcc": {"minutes": 120, "manualadd": False},
    "Song": {"minutes": 0, "manualadd": False}
}


def timestamp(offset=0):
    now = datetime.datetime.utcnow().replace(microsecond=0)
    return dt2ISO(now + datetime.timedelta(minutes=offset))


def expiration_for_inst(inst):
    if not inst or not inst["dsId"]:
        raise ValueError("Uncacheable instance: " + str(inst))
    cms = cachedefs[inst["dsType"]]
    if not cms or not cms["minutes"]:
        return ""  # not cached, no time to live
    return timestamp(cms["minutes"])


def make_key(dsType, field, value):
    # The value param will always be a string because after retrieving an
    # instance via query, the resulting fields are converted via db2app.
    return dsType + "_" + field + "_" + value


def entkey_vals(inst):
    # dsId key holds the cached instance.  Need img data so pickle.
    instkey = make_key(inst["dsType"], "dsId", inst["dsId"])
    keyvals = [{"key": instkey, "val": pickle.dumps(inst)}]
    # alternate entity keys point to the dsId key
    for field in entkeys[inst["dsType"]]:
        keyvals.append({"key": make_key(inst["dsType"], field, inst[field]),
                        "val": instkey})
    return keyvals


# Avoids repeated calls to the db for the same instance, especially within
# the same call to the webserver.  Used sparingly to avoid chewing memory.
# Time to live can range from zero to whenever in actual runtime use.
class EntityCache():
    """ Special case runtime cache to avoid pounding the db repeatedly """
    entities = {}
    def cache_put(self, inst):
        expir = expiration_for_inst(inst)
        if expir:  # cacheable
            self.cache_remove(inst)  # clear any outdated entries
            kt = inst["dsType"] + "_" + inst["dsId"] + "_cleanup"
            cachekeys = ["TTL_" + expir]
            for keyval in entkey_vals(inst):
                cachekeys.append(keyval["key"])
                self.entities[keyval["key"]] = keyval["val"]
            self.entities[kt] = ",".join(cachekeys)
            # self.log_cache_entries()
    def cache_get(self, entity, field, value):
        instkey = make_key(entity, field, value)
        if instkey not in self.entities:
            return None
        instval = self.entities[instkey]
        if field != "dsId":
            instval = self.entities[instval]
        return pickle.loads(instval)
    def cache_remove(self, inst):
        if inst:
            kt = inst["dsType"] + "_" + inst["dsId"] + "_cleanup"
            cleankeys = self.entities.pop(kt, None)
            if cleankeys:
                for oldkey in cleankeys.split(","):
                    self.entities.pop(oldkey, None)
    def cache_clean(self):
        now = nowISO()
        for key, value in self.entities.items():
            if key.endswith("_cleanup"):
                ttl = value.split(",")[0][4:]
                if ttl < now:
                    kcs = key.split("_")
                    inst = {"dsType": kcs[0], "dsId": kcs[1]}
                    self.cache_remove(inst)
    def log_cache_entries(self):
        txt = "EntityCache entities:\n"
        for key, _ in self.entities.items():
            txt += "    " + key + ": " + str(self.entities[key])[0:74] + "\n"
        logging.info(txt)
        return txt
entcache = EntityCache()


def reqarg(argname, fieldtype="string", required=False):
    argval = flask.request.args.get(argname)  # None if not found
    if not argval:
        argval = flask.request.form.get(argname)  # Ditto
    if required and not argval:
        raise ValueError("Missing required value for " + argname)
    dotidx = fieldtype.find('.')
    if dotidx > 0:
        entity = fieldtype[0:dotidx]
        fieldname = fieldtype[dotidx + 1:]
        fieldtype = entdefs[entity][fieldname]["pt"]
    if fieldtype == "email":
        emaddr = argval or ""
        emaddr = emaddr.lower()
        emaddr = re.sub('%40', '@', emaddr)
        if required and not re.match(r"[^@]+@[^@]+\.[^@]+", emaddr):
            raise ValueError("Invalid " + argname + " value: " + emaddr)
        return emaddr
    # A dbid is an int in the db and a string everywhere else
    if fieldtype in ["dbid", "string", "isodate", "isomod", "srchidcsv", "text",
                     "json", "jsarr", "idcsv", "isodcsv", "gencsv", "url"]:
        return argval or ""
    if fieldtype == "image":
        return argval or None
    if fieldtype == "int":
        argval = argval or 0
        return int(argval)
    raise ValueError("Unknown type " + fieldtype + " for " + argname)


# "cached fetch by key". Field must be dsId or one of the entkeys.
def cfbk(entity, field, value, required=False):
    if field != 'dsId' and field not in entkeys[entity]:
        raise ValueError(field + " not a unique index for " + entity)
    vstr = str(value)
    ci = entcache.cache_get(entity, field, vstr)
    if ci:
        dblogmsg("CAC", entity, ci)
        return ci
    if entdefs[entity][field]["pt"] not in ["dbid", "int"]:
        vstr = "\"" + vstr + "\""
    objs = query_entity(entity, "WHERE " + field + "=" + vstr + " LIMIT 1")
    if len(objs) > 0:
        inst = objs[0]
        if not cachedefs[inst["dsType"]]["manualadd"]:
            entcache.cache_put(inst)
        return inst
    if required:
        raise ValueError(entity + " " + vstr + " not found.")
    return None


# Get a connection to the database.  May throw mysql.connector.Error
# https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html
def get_mysql_connector():
    cnx = None
    try:
        cnx = mysql.connector.connect(user=mconf.db["u"],
                                      password=mconf.db["p"],
                                      host=mconf.db["h"],
                                      database=mconf.db["d"])
    except Exception as e:
        raise ValueError("Connection failed: " + str(e))
    return cnx


# Given what should be a string value, remove preceding or trailing space.
# If unique is true, then treat values of "null" or "None" as "".
def trim_string_val(val, unique=False):
    val = val or ""
    val = str(val)
    val = val.strip()
    if val and unique:
        lowval = val.lower()
        if lowval in ["null", "none"]:
            val = ""
    return val


# Read the given field from the inst or the default values, then convert it
# from an app value to a db value.  All string values are trimmed since
# preceding or trailing space makes matching horrible and buggy.  The UI can
# add a trailing newline for long text if it wants.
def app2db_fieldval(entity, field, inst):
    if entity:
        pt = entdefs[entity][field]["pt"]
        unique = entdefs[entity][field]["un"]
        val = entdefs[entity][field]["dv"]
    else:
        pt = dbflds[field]["pt"]
        unique = dbflds[field]["un"]
        val = dbflds[field]["dv"]
    if field in inst:
        val = inst[field]
    # convert value based on type and whether the values are unique
    if pt in ["email", "string"]:
        val = val or ""
        val = trim_string_val(val, unique)  # trim all strings. See comment.
        if not val:
            val = None
    elif pt == "image":
        if not val:  # Empty data gets set to null
            val = None
    elif pt == "int":
        val = val or 0
        val = int(val)  # convert possible "0" value
    elif pt == "dbid":
        try:
            val = int(val)  # will fail on "", "null" or other bad values
        except ValueError:
            val = 0
        if unique and not val:  # null vals don't violate UNIQUE constraint
            val = None          # otherwise use 0 as val may be required
    return val


# Read the given field from the inst or the default values, then convert it
# from a db value to an app value.  "app" means the server side module
# calling this module, not the web client.  Image binary values and json
# field values are not decoded, but get safe defaults if NULL.  dbids are
# converted to strings.
def db2app_fieldval(entity, field, inst):
    if entity:
        pt = entdefs[entity][field]["pt"]
        val = entdefs[entity][field]["dv"]
    else:
        pt = dbflds[field]["pt"]
        val = dbflds[field]["dv"]
    if field in inst:
        val = inst[field]
    # convert value based on type
    if pt in ["email", "string"]:
        if not val:  # A null value gets set to the empty string
            val = ""
        val = str(val)  # db interface might have autoconverted to int
    elif pt == "image":
        if not val:  # A null value gets set to the empty string
            val = ""
    elif pt == "int":
        if not val:  # Convert null values to 0
            val = 0
    elif pt == "dbid":
        if not val:  # A zero or null value gets set to falsey empty string
            val = ""
        else:
            val = str(val)
    return val


def ISO2dt(isostr):
    isostr = re.sub(r"\.\d*Z", "Z", isostr)  # remove microsecond if any
    dt = datetime.datetime.utcnow()
    dt = dt.strptime(isostr, "%Y-%m-%dT%H:%M:%SZ")
    return dt


def dt2ISO(dt):
    iso = str(dt.year) + "-" + str(dt.month).rjust(2, '0') + "-"
    iso += str(dt.day).rjust(2, '0') + "T" + str(dt.hour).rjust(2, '0')
    iso += ":" + str(dt.minute).rjust(2, '0') + ":"
    iso += str(dt.second).rjust(2, '0') + "Z"
    return iso


def nowISO():
    """ Return the current time as an ISO string """
    return dt2ISO(datetime.datetime.utcnow())


def initialize_timestamp_fields(fields, vck):
    ts = nowISO()
    if "created" not in fields or not fields["created"] or vck != "override":
        fields["created"] = ts
    if "modified" not in fields or not fields["modified"] or vck != "override":
        fields["modified"] = ts + ";1"


def verify_timestamp_fields(entity, dsId, fields, vck):
    if vck == "override" and "created" in fields and "modified" in fields:
        return fields # skip query and use specified values
    if not vck or not vck.strip():
        raise ValueError("Version check required to update " + entity +
                         " " + str(dsId))
    existing = cfbk(entity, "dsId", dsId)
    if not existing:
        raise ValueError("Existing " + entity + " " + str(dsId) + " not found.")
    if vck != "override" and existing["modified"] != vck:
        raise ValueError("Update error. Outdated data given for " + entity +
                         " " + str(dsId) + ".")
    if "created" not in fields or not fields["created"] or vck != "override":
        fields["created"] = existing["created"]
    ver = 1
    mods = existing["modified"].split(";")
    if len(mods) > 1:
        ver = int(mods[1]) + 1
    if "modified" not in fields or not fields["modified"] or vck != "override":
        fields["modified"] = nowISO() + ";" + str(ver)
    return existing


# Convert the given DigAcc inst dict from app values to db values.  Removes
# the dsType field to avoid trying to write it to the db.
def app2db_DigAcc(inst, fill=True):
    cnv = {}
    cnv["dsId"] = None
    if "dsId" in inst:
        cnv["dsId"] = app2db_fieldval(None, "dsId", inst)
    if fill or "created" in inst:
        cnv["created"] = app2db_fieldval(None, "created", inst)
    if fill or "modified" in inst:
        cnv["modified"] = app2db_fieldval(None, "modified", inst)
    if fill or "batchconv" in inst:
        cnv["batchconv"] = app2db_fieldval(None, "batchconv", inst)
    if fill or "email" in inst:
        cnv["email"] = app2db_fieldval("DigAcc", "email", inst)
    if fill or "phash" in inst:
        cnv["phash"] = app2db_fieldval("DigAcc", "phash", inst)
    if fill or "status" in inst:
        cnv["status"] = app2db_fieldval("DigAcc", "status", inst)
    if fill or "actsends" in inst:
        cnv["actsends"] = app2db_fieldval("DigAcc", "actsends", inst)
    if fill or "actcode" in inst:
        cnv["actcode"] = app2db_fieldval("DigAcc", "actcode", inst)
    if fill or "lastsync" in inst:
        cnv["lastsync"] = app2db_fieldval("DigAcc", "lastsync", inst)
    if fill or "firstname" in inst:
        cnv["firstname"] = app2db_fieldval("DigAcc", "firstname", inst)
    if fill or "hashtag" in inst:
        cnv["hashtag"] = app2db_fieldval("DigAcc", "hashtag", inst)
    if fill or "kwdefs" in inst:
        cnv["kwdefs"] = app2db_fieldval("DigAcc", "kwdefs", inst)
    if fill or "igfolds" in inst:
        cnv["igfolds"] = app2db_fieldval("DigAcc", "igfolds", inst)
    if fill or "settings" in inst:
        cnv["settings"] = app2db_fieldval("DigAcc", "settings", inst)
    return cnv


# Convert the given DigAcc inst dict from db values to app values.  Adds the
# dsType field for general app processing.
def db2app_DigAcc(inst):
    cnv = {}
    cnv["dsType"] = "DigAcc"
    cnv["dsId"] = db2app_fieldval(None, "dsId", inst)
    cnv["created"] = db2app_fieldval(None, "created", inst)
    cnv["modified"] = db2app_fieldval(None, "modified", inst)
    cnv["batchconv"] = db2app_fieldval(None, "batchconv", inst)
    cnv["email"] = db2app_fieldval("DigAcc", "email", inst)
    cnv["phash"] = db2app_fieldval("DigAcc", "phash", inst)
    cnv["status"] = db2app_fieldval("DigAcc", "status", inst)
    cnv["actsends"] = db2app_fieldval("DigAcc", "actsends", inst)
    cnv["actcode"] = db2app_fieldval("DigAcc", "actcode", inst)
    cnv["lastsync"] = db2app_fieldval("DigAcc", "lastsync", inst)
    cnv["firstname"] = db2app_fieldval("DigAcc", "firstname", inst)
    cnv["hashtag"] = db2app_fieldval("DigAcc", "hashtag", inst)
    cnv["kwdefs"] = db2app_fieldval("DigAcc", "kwdefs", inst)
    cnv["igfolds"] = db2app_fieldval("DigAcc", "igfolds", inst)
    cnv["settings"] = db2app_fieldval("DigAcc", "settings", inst)
    return cnv


# Convert the given Song inst dict from app values to db values.  Removes
# the dsType field to avoid trying to write it to the db.
def app2db_Song(inst, fill=True):
    cnv = {}
    cnv["dsId"] = None
    if "dsId" in inst:
        cnv["dsId"] = app2db_fieldval(None, "dsId", inst)
    if fill or "created" in inst:
        cnv["created"] = app2db_fieldval(None, "created", inst)
    if fill or "modified" in inst:
        cnv["modified"] = app2db_fieldval(None, "modified", inst)
    if fill or "batchconv" in inst:
        cnv["batchconv"] = app2db_fieldval(None, "batchconv", inst)
    if fill or "aid" in inst:
        cnv["aid"] = app2db_fieldval("Song", "aid", inst)
    if fill or "path" in inst:
        cnv["path"] = app2db_fieldval("Song", "path", inst)
    if fill or "ti" in inst:
        cnv["ti"] = app2db_fieldval("Song", "ti", inst)
    if fill or "ar" in inst:
        cnv["ar"] = app2db_fieldval("Song", "ar", inst)
    if fill or "ab" in inst:
        cnv["ab"] = app2db_fieldval("Song", "ab", inst)
    if fill or "el" in inst:
        cnv["el"] = app2db_fieldval("Song", "el", inst)
    if fill or "al" in inst:
        cnv["al"] = app2db_fieldval("Song", "al", inst)
    if fill or "kws" in inst:
        cnv["kws"] = app2db_fieldval("Song", "kws", inst)
    if fill or "rv" in inst:
        cnv["rv"] = app2db_fieldval("Song", "rv", inst)
    if fill or "fq" in inst:
        cnv["fq"] = app2db_fieldval("Song", "fq", inst)
    if fill or "lp" in inst:
        cnv["lp"] = app2db_fieldval("Song", "lp", inst)
    if fill or "nt" in inst:
        cnv["nt"] = app2db_fieldval("Song", "nt", inst)
    return cnv


# Convert the given Song inst dict from db values to app values.  Adds the
# dsType field for general app processing.
def db2app_Song(inst):
    cnv = {}
    cnv["dsType"] = "Song"
    cnv["dsId"] = db2app_fieldval(None, "dsId", inst)
    cnv["created"] = db2app_fieldval(None, "created", inst)
    cnv["modified"] = db2app_fieldval(None, "modified", inst)
    cnv["batchconv"] = db2app_fieldval(None, "batchconv", inst)
    cnv["aid"] = db2app_fieldval("Song", "aid", inst)
    cnv["path"] = db2app_fieldval("Song", "path", inst)
    cnv["ti"] = db2app_fieldval("Song", "ti", inst)
    cnv["ar"] = db2app_fieldval("Song", "ar", inst)
    cnv["ab"] = db2app_fieldval("Song", "ab", inst)
    cnv["el"] = db2app_fieldval("Song", "el", inst)
    cnv["al"] = db2app_fieldval("Song", "al", inst)
    cnv["kws"] = db2app_fieldval("Song", "kws", inst)
    cnv["rv"] = db2app_fieldval("Song", "rv", inst)
    cnv["fq"] = db2app_fieldval("Song", "fq", inst)
    cnv["lp"] = db2app_fieldval("Song", "lp", inst)
    cnv["nt"] = db2app_fieldval("Song", "nt", inst)
    return cnv


def dblogmsg(op, entity, res):
    log_summary_flds = {
        "DigAcc": ["email", "firstname"],
        "Song": ["aid", "ti", "ar"]}
    if res:
        if op != "QRY":  # query is already a list, listify anything else
            res = [res]
        for obj in res:
            msg = "db" + op + " " + entity + " " + obj["dsId"]
            if entity in log_summary_flds:
                for field in log_summary_flds[entity]:
                    msg += " " + str(obj[field])[0:60]
            logging.info(msg)
    else:  # no res, probably a delete
        logging.info("db" + op + " " + entity + " -no obj details-")


# Write a new DigAcc row, using the given field values or defaults.
def insert_new_DigAcc(cnx, cursor, fields):
    fields = app2db_DigAcc(fields)
    stmt = (
        "INSERT INTO DigAcc (created, modified, email, phash, status, actsends, actcode, lastsync, firstname, hashtag, kwdefs, igfolds, settings) "
        "VALUES (%(created)s, %(modified)s, %(email)s, %(phash)s, %(status)s, %(actsends)s, %(actcode)s, %(lastsync)s, %(firstname)s, %(hashtag)s, %(kwdefs)s, %(igfolds)s, %(settings)s)")
    data = {
        'created': fields.get("created"),
        'modified': fields.get("modified"),
        'email': fields.get("email", entdefs["DigAcc"]["email"]["dv"]),
        'phash': fields.get("phash", entdefs["DigAcc"]["phash"]["dv"]),
        'status': fields.get("status", entdefs["DigAcc"]["status"]["dv"]),
        'actsends': fields.get("actsends", entdefs["DigAcc"]["actsends"]["dv"]),
        'actcode': fields.get("actcode", entdefs["DigAcc"]["actcode"]["dv"]),
        'lastsync': fields.get("lastsync", entdefs["DigAcc"]["lastsync"]["dv"]),
        'firstname': fields.get("firstname", entdefs["DigAcc"]["firstname"]["dv"]),
        'hashtag': fields.get("hashtag", entdefs["DigAcc"]["hashtag"]["dv"]),
        'kwdefs': fields.get("kwdefs", entdefs["DigAcc"]["kwdefs"]["dv"]),
        'igfolds': fields.get("igfolds", entdefs["DigAcc"]["igfolds"]["dv"]),
        'settings': fields.get("settings", entdefs["DigAcc"]["settings"]["dv"])}
    cursor.execute(stmt, data)
    fields["dsId"] = cursor.lastrowid
    cnx.commit()
    fields = db2app_DigAcc(fields)
    dblogmsg("ADD", "DigAcc", fields)
    return fields


# Update the specified DigAcc row with the given field values.
def update_existing_DigAcc(context, fields):
    fields = app2db_DigAcc(fields, fill=False)
    dsId = int(fields["dsId"])  # Verify int value
    stmt = ""
    for field in fields:  # only updating the fields passed in
        if stmt:
            stmt += ", "
        stmt += field + "=(%(" + field + ")s)"
    stmt = "UPDATE DigAcc SET " + stmt + " WHERE dsId=" + str(dsId)
    if context["vck"] != "override":
        stmt += " AND modified=\"" + context["vck"] + "\""
    data = {}
    for field in fields:
        data[field] = fields[field]
    context["cursor"].execute(stmt, data)
    if context["cursor"].rowcount < 1 and context["vck"] != "override":
        raise ValueError("DigAcc" + str(dsId) + " update received outdated version check value " + context["vck"] + ".")
    context["cnx"].commit()
    result = context["existing"]
    for field in fields:
        result[field] = fields[field]
    result = db2app_DigAcc(result)
    dblogmsg("UPD", "DigAcc", result)
    entcache.cache_put(result)
    return result


# Write a new Song row, using the given field values or defaults.
def insert_new_Song(cnx, cursor, fields):
    fields = app2db_Song(fields)
    stmt = (
        "INSERT INTO Song (created, modified, aid, path, ti, ar, ab, el, al, kws, rv, fq, lp, nt) "
        "VALUES (%(created)s, %(modified)s, %(aid)s, %(path)s, %(ti)s, %(ar)s, %(ab)s, %(el)s, %(al)s, %(kws)s, %(rv)s, %(fq)s, %(lp)s, %(nt)s)")
    data = {
        'created': fields.get("created"),
        'modified': fields.get("modified"),
        'aid': fields.get("aid", entdefs["Song"]["aid"]["dv"]),
        'path': fields.get("path", entdefs["Song"]["path"]["dv"]),
        'ti': fields.get("ti", entdefs["Song"]["ti"]["dv"]),
        'ar': fields.get("ar", entdefs["Song"]["ar"]["dv"]),
        'ab': fields.get("ab", entdefs["Song"]["ab"]["dv"]),
        'el': fields.get("el", entdefs["Song"]["el"]["dv"]),
        'al': fields.get("al", entdefs["Song"]["al"]["dv"]),
        'kws': fields.get("kws", entdefs["Song"]["kws"]["dv"]),
        'rv': fields.get("rv", entdefs["Song"]["rv"]["dv"]),
        'fq': fields.get("fq", entdefs["Song"]["fq"]["dv"]),
        'lp': fields.get("lp", entdefs["Song"]["lp"]["dv"]),
        'nt': fields.get("nt", entdefs["Song"]["nt"]["dv"])}
    cursor.execute(stmt, data)
    fields["dsId"] = cursor.lastrowid
    cnx.commit()
    fields = db2app_Song(fields)
    dblogmsg("ADD", "Song", fields)
    return fields


# Update the specified Song row with the given field values.
def update_existing_Song(context, fields):
    fields = app2db_Song(fields, fill=False)
    dsId = int(fields["dsId"])  # Verify int value
    stmt = ""
    for field in fields:  # only updating the fields passed in
        if stmt:
            stmt += ", "
        stmt += field + "=(%(" + field + ")s)"
    stmt = "UPDATE Song SET " + stmt + " WHERE dsId=" + str(dsId)
    if context["vck"] != "override":
        stmt += " AND modified=\"" + context["vck"] + "\""
    data = {}
    for field in fields:
        data[field] = fields[field]
    context["cursor"].execute(stmt, data)
    if context["cursor"].rowcount < 1 and context["vck"] != "override":
        raise ValueError("Song" + str(dsId) + " update received outdated version check value " + context["vck"] + ".")
    context["cnx"].commit()
    result = context["existing"]
    for field in fields:
        result[field] = fields[field]
    result = db2app_Song(result)
    dblogmsg("UPD", "Song", result)
    entcache.cache_remove(result)
    return result


# Write the given dict/object based on the dsType.  Binary field values must
# be base64.b64encode.  Unspecified fields are set to default values for a
# new instance, and left alone on update.  For update, the verification
# check value must match the modified value of the existing instance.
def write_entity(inst, vck="1234-12-12T00:00:00Z"):
    cnx = get_mysql_connector()
    if not cnx:
        raise ValueError("Database connection failed.")
    try:
        cursor = cnx.cursor()
        try:
            entity = inst.get("dsType", None)
            dsId = inst.get("dsId", 0)
            if dsId:
                existing = verify_timestamp_fields(entity, dsId, inst, vck)
                context = {"cnx":cnx, "cursor":cursor, "vck":vck,
                           "existing":existing}
                if entity == "DigAcc":
                    return update_existing_DigAcc(context, inst)
                if entity == "Song":
                    return update_existing_Song(context, inst)
                raise ValueError("Cannot modify unknown entity dsType " +
                                 str(entity))
            # No existing instance to update.  Insert new.
            initialize_timestamp_fields(inst, vck)
            if entity == "DigAcc":
                return insert_new_DigAcc(cnx, cursor, inst)
            if entity == "Song":
                return insert_new_Song(cnx, cursor, inst)
            raise ValueError("Cannot create unknown entity dsType " +
                             str(entity))
        except mysql.connector.Error as e:
            raise ValueError(str(e) or "No mysql error text")  # see note 1
        finally:
            cursor.close()
    finally:
        cnx.close()


def delete_entity(entity, dsId):
    cnx = get_mysql_connector()
    if not cnx:
        raise ValueError("Database connection failed.")
    try:
        cursor = cnx.cursor()
        try:
            stmt = "DELETE FROM " + entity + " WHERE dsId=" + str(dsId)
            cursor.execute(stmt)
            cnx.commit()
            dblogmsg("DEL", entity + " " + str(dsId), None)
            # if cache cleanup is needed that is up to caller
        except mysql.connector.Error as e:
            raise ValueError(str(e) or "No mysql error text")  # see note 1
        finally:
            cursor.close()
    finally:
        cnx.close()


def query_DigAcc(cnx, cursor, where):
    query = "SELECT dsId, created, modified, "
    query += "email, phash, status, actsends, actcode, lastsync, firstname, hashtag, kwdefs, igfolds, settings"
    query += " FROM DigAcc " + where
    cursor.execute(query)
    res = []
    for (dsId, created, modified, email, phash, status, actsends, actcode, lastsync, firstname, hashtag, kwdefs, igfolds, settings) in cursor:
        inst = {"dsType": "DigAcc", "dsId": dsId, "created": created, "modified": modified, "email": email, "phash": phash, "status": status, "actsends": actsends, "actcode": actcode, "lastsync": lastsync, "firstname": firstname, "hashtag": hashtag, "kwdefs": kwdefs, "igfolds": igfolds, "settings": settings}
        inst = db2app_DigAcc(inst)
        res.append(inst)
    dblogmsg("QRY", "DigAcc", res)
    return res


def query_Song(cnx, cursor, where):
    query = "SELECT dsId, created, modified, "
    query += "aid, path, ti, ar, ab, el, al, kws, rv, fq, lp, nt"
    query += " FROM Song " + where
    cursor.execute(query)
    res = []
    for (dsId, created, modified, aid, path, ti, ar, ab, el, al, kws, rv, fq, lp, nt) in cursor:
        inst = {"dsType": "Song", "dsId": dsId, "created": created, "modified": modified, "aid": aid, "path": path, "ti": ti, "ar": ar, "ab": ab, "el": el, "al": al, "kws": kws, "rv": rv, "fq": fq, "lp": lp, "nt": nt}
        inst = db2app_Song(inst)
        res.append(inst)
    dblogmsg("QRY", "Song", res)
    return res


# Fetch all instances of the specified entity kind for the given WHERE
# clause.  The WHERE clause should include a LIMIT, and should only match on
# indexed fields and/or declared query indexes.  For speed and general
# compatibility, only one inequality operator should be used in the match.
def query_entity(entity, where):
    cnx = get_mysql_connector()
    if not cnx:
        raise ValueError("Database connection failed.")
    try:
        cursor = cnx.cursor()
        try:
            if entity == "DigAcc":
                return query_DigAcc(cnx, cursor, where)
            if entity == "Song":
                return query_Song(cnx, cursor, where)
        except mysql.connector.Error as e:
            raise ValueError(str(e) or "No mysql error text")  # see note 1
        finally:
            cursor.close()
    finally:
        cnx.close()


def visible_DigAcc_fields(obj, audience):
    filtobj = {}
    for fld, val in obj.items():
        if fld == "email" and audience != "private":
            continue
        if fld == "phash":
            continue
        if fld == "status" and audience != "private":
            continue
        if fld == "actsends":
            continue
        if fld == "actcode":
            continue
        filtobj[fld] = val
    return filtobj


def visible_Song_fields(obj, audience):
    filtobj = {}
    for fld, val in obj.items():
        filtobj[fld] = val
    return filtobj


# Return a copied object with only the fields appropriate to the audience.
# Specifying audience="private" includes peronal info.  The given obj is
# assumed to already have been through db2app conversion.  Image fields are
# converted to dsId values for separate download.
def visible_fields(obj, audience="public"):
    if obj["dsType"] == "DigAcc":
        return visible_DigAcc_fields(obj, audience)
    if obj["dsType"] == "Song":
        return visible_Song_fields(obj, audience)
    raise ValueError("Unknown object dsType: " + obj["dsType"])


