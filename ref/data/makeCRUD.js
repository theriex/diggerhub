/*jslint node, white, long, unordered */

var ddefs = require("./datadefs");
var srcdir = "../../site/py";
var jsdir = "../../site/public/js/amd";
var dsvdir = "../../../digger/server";
var fs = require("fs");


function avoidBadPropertyNameWarning (obj, method, ...args) {
    return obj[method].apply(obj, args);
}


function writeFileSync (filename, data) {
    return avoidBadPropertyNameWarning(fs, "writeFileSync", filename, data);
}


////////////////////////////////////////
// SQL code (MySQL db)

function sqlType (fd) {
    if(ddefs.fieldIs(fd, "string")) {
        //string (email, isodate, isomod, srchidcsv)
        //MySQL has some native support for email addresses and dates, but
        //any required value checking is done in the service API, not the db.
        return "VARCHAR(256)"; }
    if(ddefs.fieldIs(fd, "text")) {
        //text (json, jsarr, idcsv, isodcsv, gencsv, url)
        //The maximum size of a LONGTEXT is 2^32 = 4,294,967,296 bytes.
        //MySQL has native support for JSON, but rather have that be opaque
        //and not take a hit from the computational overhead.
        return "LONGTEXT"; }
    if(ddefs.fieldIs(fd, "image")) {
        //The maximum size of a LONGBLOB is 2^32 = 4,294,967,296 bytes.
        return "LONGBLOB"; }
    if(ddefs.fieldIs(fd, "dbid")) {
        return "BIGINT"; }
    if(ddefs.fieldIs(fd, "int")) {
        return "INT"; }
}


function reqFlag (fd) {
    if(ddefs.fieldIs(fd, "required")) {
        return " NOT NULL"; }
    return "";
}


function uniqueFlag (fd) {
    if(ddefs.fieldIs(fd, "unique")) {
        return " UNIQUE"; }
    return "";
}


function indexClauses (edef) {
    var idxs = "";
    edef.queries = edef.queries || [];
    edef.queries.forEach(function (query) {
        var idxc = "";
        query.q.forEach(function (idxelem) {
            if(idxc) {
                idxc += ", "; }
            idxc += idxelem.f;
            if(idxelem.dir === "desc") {
                idxc += " DESC"; } });
        idxs += "  INDEX (" + idxc + "),\n"; });
    return idxs;
}


function createDatabaseSQL() {
    var sql = "";
    ddefs.dataDefinitions().forEach(function (edef) {
        sql += "CREATE TABLE " + edef.entity + " (  -- " + edef.descr + "\n";
        sql += "  dsId BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,\n";
        sql += "  created VARCHAR(256) NOT NULL,\n";
        sql += "  modified VARCHAR(256) NOT NULL,\n";
        sql += "  batchconv VARCHAR(256),\n";
        edef.fields.forEach(function (ed) {
            sql += "  " + ed.f + " " + sqlType(ed.d) + reqFlag(ed.d) +
                uniqueFlag(ed.d) + ",\n"; });
        sql += indexClauses(edef);
        sql += "  PRIMARY KEY (dsId)\n";
        sql += ");\n";
        sql += "ALTER TABLE " + edef.entity + " AUTO_INCREMENT = 2020;\n\n"; });
    writeFileSync("createMySQLTables.sql", sql);
}

////////////////////////////////////////
// Python code

function pyTypeForField (fd) {
    if(ddefs.fieldIs(fd.d, "email")) {
        return "email"; }
    if(ddefs.fieldIs(fd.d, "string") || ddefs.fieldIs(fd.d, "text")) {
        return "string"; }
    if(ddefs.fieldIs(fd.d, "image")) {
        return "image"; }
    if(ddefs.fieldIs(fd.d, "int")) {
        return "int"; }
    if(ddefs.fieldIs(fd.d, "dbid")) {
        return "dbid"; }
    return "UnkownPyType!";
}


function defValForPyType (pt) {
    switch(pt) {
    case "email": return "\"\"";
    case "string": return "\"\"";
    case "image": return "None";
    case "int": return "0";
    case "dbid": return "0";
    default: return "\"\""; }
}


function pyboolstr (val) {
    if(val) {
        return "True"; }
    return "False";
}


function entityDefinitions () {
    var pyc = "";
    var definitions = ddefs.dataDefinitions();
    pyc += "entdefs = {\n";
    definitions.forEach(function (edef, eidx) {
        var ecomma = "";
        if(eidx < definitions.length - 1) {
            ecomma = ","; }
        pyc += "    \"" + edef.entity + "\": {  # " + edef.descr + "\n";
        pyc += "        \"dsId\": {\"pt\": \"dbid\", \"un\": True, \"dv\": 0},\n";
        pyc += "        \"created\": {\"pt\": \"string\", \"un\": False, \"dv\": \"\"},\n";
        pyc += "        \"modified\": {\"pt\": \"string\", \"un\": False, \"dv\": \"\"},\n";
        pyc += "        \"batchconv\": {\"pt\": \"string\", \"un\": False, \"dv\": \"\"},\n";
        edef.fields.forEach(function (fd, fidx) {
            var fcomma = "";
            var pytype = pyTypeForField(fd);
            if(fidx < edef.fields.length - 1) {
                fcomma = ","; }
            pyc += "        \"" + fd.f + "\": {" +
                "\"pt\": \"" + pytype + "\", " +
                "\"un\": " + pyboolstr(ddefs.fieldIs(fd.d, "unique")) + ", " +
                "\"dv\": " + defValForPyType(pytype) + "}" +
                fcomma + "\n"; });
        pyc += "    }" + ecomma + "\n"; });
    pyc += "}\n";
    return pyc;
}


function entityKeyFields () {
    var pyc = "";
    var definitions = ddefs.dataDefinitions();
    pyc += "entkeys = {\n";
    definitions.forEach(function (edef, eidx) {
        var ecomma = ""; var keyflds = "";
        if(eidx < definitions.length - 1) {
            ecomma = ","; }
        pyc += "    \"" + edef.entity + "\": [";
        edef.fields.forEach(function (fd) {
            if(ddefs.fieldIs(fd.d, "unique")) {
                if(keyflds) {
                    keyflds += ", "; }
                keyflds += "\"" + fd.f + "\""; } });
        pyc += keyflds + "]" + ecomma + "\n"; });
    pyc += "}\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "cachedefs = {\n";
    definitions.forEach(function (edef, eidx) {
        var ecomma = "";
        var mav = "False";
        if(edef.cache.manualadd) {
            mav = "True"; }
        if(eidx < definitions.length - 1) {
            ecomma = ","; }
        pyc += "    \"" + edef.entity + "\": {\"minutes\": " + 
            edef.cache.minutes + ", \"manualadd\": " + mav + "}" +
            ecomma + "\n"; });
    pyc += "}\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def timestamp(offset=0):\n";
    pyc += "    now = datetime.datetime.utcnow().replace(microsecond=0)\n";
    pyc += "    return dt2ISO(now + datetime.timedelta(minutes=offset))\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def expiration_for_inst(inst):\n";
    pyc += "    if not inst or not inst[\"dsId\"]:\n";
    pyc += "        raise ValueError(\"Uncacheable instance: \" + str(inst))\n";
    pyc += "    cms = cachedefs[inst[\"dsType\"]]\n";
    pyc += "    if not cms or not cms[\"minutes\"]:\n";
    pyc += "        return \"\"  # not cached, no time to live\n";
    pyc += "    return timestamp(cms[\"minutes\"])\n";
    return pyc;
}


function entityCache () {
    var pyc = "";
    pyc += "def make_key(dsType, field, value):\n";
    pyc += "    # The value param will always be a string because after retrieving an\n";
    pyc += "    # instance via query, the resulting fields are converted via db2app.\n";
    pyc += "    return dsType + \"_\" + field + \"_\" + value\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def entkey_vals(inst):\n";
    pyc += "    # dsId key holds the cached instance.  Need img data so pickle.\n";
    pyc += "    instkey = make_key(inst[\"dsType\"], \"dsId\", inst[\"dsId\"])\n";
    pyc += "    keyvals = [{\"key\": instkey, \"val\": pickle.dumps(inst)}]\n";
    pyc += "    # alternate entity keys point to the dsId key\n";
    pyc += "    for field in entkeys[inst[\"dsType\"]]:\n";
    pyc += "        keyvals.append({\"key\": make_key(inst[\"dsType\"], field, inst[field]),\n";
    pyc += "                        \"val\": instkey})\n";
    pyc += "    return keyvals\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "# Avoids repeated calls to the db for the same instance, especially within\n";
    pyc += "# the same call to the webserver.  Used sparingly to avoid chewing memory.\n";
    pyc += "# Time to live can range from zero to whenever in actual runtime use.\n";
    pyc += "class EntityCache():\n";
    pyc += "    \"\"\" Special case runtime cache to avoid pounding the db repeatedly \"\"\"\n";
    pyc += "    entities = {}\n";
    pyc += "    def cache_put(self, inst):\n";
    pyc += "        expir = expiration_for_inst(inst)\n";
    pyc += "        if expir:  # cacheable\n";
    pyc += "            self.cache_remove(inst)  # clear any outdated entries\n";
    pyc += "            kt = inst[\"dsType\"] + \"_\" + inst[\"dsId\"] + \"_cleanup\"\n";
    pyc += "            cachekeys = [\"TTL_\" + expir]\n";
    pyc += "            for keyval in entkey_vals(inst):\n";
    pyc += "                cachekeys.append(keyval[\"key\"])\n";
    pyc += "                self.entities[keyval[\"key\"]] = keyval[\"val\"]\n";
    pyc += "            self.entities[kt] = \",\".join(cachekeys)\n";
    pyc += "            # self.log_cache_entries()\n";
    pyc += "    def cache_get(self, entity, field, value):\n";
    pyc += "        instkey = make_key(entity, field, value)\n";
    pyc += "        if instkey not in self.entities:\n";
    pyc += "            return None\n";
    pyc += "        instval = self.entities[instkey]\n";
    pyc += "        if field != \"dsId\":\n";
    pyc += "            instval = self.entities[instval]\n";
    pyc += "        return pickle.loads(instval)\n";
    pyc += "    def cache_remove(self, inst):\n";
    pyc += "        if inst:\n";
    pyc += "            kt = inst[\"dsType\"] + \"_\" + inst[\"dsId\"] + \"_cleanup\"\n";
    pyc += "            cleankeys = self.entities.pop(kt, None)\n";
    pyc += "            if cleankeys:\n";
    pyc += "                for oldkey in cleankeys.split(\",\"):\n";
    pyc += "                    self.entities.pop(oldkey, None)\n";
    pyc += "    def cache_clean(self):\n";
    pyc += "        now = nowISO()\n";
    pyc += "        keys = list(self.entities.keys())  # hold keys since dict changing\n";
    pyc += "        for key in keys:\n";
    pyc += "            if key.endswith(\"_cleanup\"):\n";
    pyc += "                value = self.entities.get(key, None)\n";
    pyc += "                if value:\n";
    pyc += "                    ttl = value.split(\",\")[0][4:]\n";
    pyc += "                    if ttl < now:\n";
    pyc += "                        kcs = key.split(\"_\")\n";
    pyc += "                        inst = {\"dsType\": kcs[0], \"dsId\": kcs[1]}\n";
    pyc += "                        self.cache_remove(inst)\n";
    pyc += "    def log_cache_entries(self):\n";
    pyc += "        txt = \"EntityCache entities:\\n\"\n";
    pyc += "        for key, _ in self.entities.items():\n";
    pyc += "            txt += \"    \" + key + \": \" + str(self.entities[key])[0:74] + \"\\n\"\n";
    pyc += "        logging.info(txt)\n";
    pyc += "        return txt\n";
    pyc += "entcache = EntityCache()\n";
    return pyc;
}


function helperFunctions () {
    var pyc = "";
    pyc += "def reqarg(argname, fieldtype=\"string\", required=False):\n";
    pyc += "    argval = flask.request.args.get(argname)  # None if not found\n";
    pyc += "    if not argval:\n";
    pyc += "        argval = flask.request.form.get(argname)  # Ditto\n";
    pyc += "    if required and not argval:\n";
    pyc += "        raise ValueError(\"Missing required value for \" + argname)\n";
    pyc += "    dotidx = fieldtype.find('.')\n";
    pyc += "    if dotidx > 0:\n";
    pyc += "        entity = fieldtype[0:dotidx]\n";
    pyc += "        fieldname = fieldtype[dotidx + 1:]\n";
    pyc += "        fieldtype = entdefs[entity][fieldname][\"pt\"]\n";
    pyc += "    if fieldtype == \"email\":\n";
    pyc += "        emaddr = argval or \"\"\n";
    pyc += "        emaddr = emaddr.lower()\n";
    pyc += "        emaddr = re.sub('%40', '@', emaddr)\n";
    pyc += "        if required and not re.match(r\"[^@]+@[^@]+\\.[^@]+\", emaddr):\n";
    pyc += "            raise ValueError(\"Invalid \" + argname + \" value: \" + emaddr)\n";
    pyc += "        return emaddr\n";
    pyc += "    # A dbid is an int in the db and a string everywhere else\n";
    pyc += "    if fieldtype in [\"dbid\", \"string\", \"isodate\", \"isomod\", \"srchidcsv\", \"text\",\n";
    pyc += "                     \"json\", \"jsarr\", \"idcsv\", \"isodcsv\", \"gencsv\", \"url\"]:\n";
    pyc += "        return argval or \"\"\n";
    pyc += "    if fieldtype == \"image\":\n";
    pyc += "        return argval or None\n";
    pyc += "    if fieldtype == \"int\":\n";
    pyc += "        argval = argval or 0\n";
    pyc += "        return int(argval)\n";
    pyc += "    raise ValueError(\"Unknown type \" + fieldtype + \" for \" + argname)\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "# \"cached fetch by key\". Field must be dsId or one of the entkeys.\n";
    pyc += "def cfbk(entity, field, value, required=False):\n";
    pyc += "    if field != 'dsId' and field not in entkeys[entity]:\n";
    pyc += "        raise ValueError(field + \" not a unique index for \" + entity)\n";
    pyc += "    vstr = str(value)\n";
    pyc += "    ci = entcache.cache_get(entity, field, vstr)\n";
    pyc += "    if ci:\n";
    pyc += "        dblogmsg(\"CAC\", entity, ci)\n";
    pyc += "        return ci\n";
    pyc += "    if entdefs[entity][field][\"pt\"] not in [\"dbid\", \"int\"]:\n";
    pyc += "        vstr = \"\\\"\" + vstr + \"\\\"\"\n";
    pyc += "    objs = query_entity(entity, \"WHERE \" + field + \"=\" + vstr + \" LIMIT 1\")\n";
    pyc += "    if len(objs) > 0:\n";
    pyc += "        inst = objs[0]\n";
    pyc += "        if not cachedefs[inst[\"dsType\"]][\"manualadd\"]:\n";
    pyc += "            entcache.cache_put(inst)\n";
    pyc += "        return inst\n";
    pyc += "    if required:\n";
    pyc += "        raise ValueError(entity + \" \" + vstr + \" not found.\")\n";
    pyc += "    return None\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "# Get a connection to the database.  May throw mysql.connector.Error\n";
    pyc += "# https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html\n";
    pyc += "def get_mysql_connector():\n";
    pyc += "    cnx = None\n";
    pyc += "    try:\n";
    pyc += "        cnx = mysql.connector.connect(user=mconf.db[\"u\"],\n";
    pyc += "                                      password=mconf.db[\"p\"],\n";
    pyc += "                                      host=mconf.db[\"h\"],\n";
    pyc += "                                      database=mconf.db[\"d\"])\n";
    pyc += "    except Exception as e:\n";
    pyc += "        raise ValueError(\"Connection failed: \" + str(e))\n";
    pyc += "    return cnx\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "# Given what should be a string value, remove preceding or trailing space.\n";
    pyc += "# If unique is true, then treat values of \"null\" or \"None\" as \"\".\n";
    pyc += "def trim_string_val(val, unique=False):\n";
    pyc += "    val = val or \"\"\n";
    pyc += "    val = str(val)\n";
    pyc += "    val = val.strip()\n";
    pyc += "    if val and unique:\n";
    pyc += "        lowval = val.lower()\n";
    pyc += "        if lowval in [\"null\", \"none\"]:\n";
    pyc += "            val = \"\"\n";
    pyc += "    return val\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "# Read the given field from the inst or the default values, then convert it\n";
    pyc += "# from an app value to a db value.  All string values are trimmed since\n";
    pyc += "# preceding or trailing space makes matching horrible and buggy.  The UI can\n";
    pyc += "# add a trailing newline for long text if it wants.\n";
    pyc += "def app2db_fieldval(entity, field, inst):\n";
    pyc += "    if entity:\n";
    pyc += "        pt = entdefs[entity][field][\"pt\"]\n";
    pyc += "        unique = entdefs[entity][field][\"un\"]\n";
    pyc += "        val = entdefs[entity][field][\"dv\"]\n";
    pyc += "    else:\n";
    pyc += "        pt = dbflds[field][\"pt\"]\n";
    pyc += "        unique = dbflds[field][\"un\"]\n";
    pyc += "        val = dbflds[field][\"dv\"]\n";
    pyc += "    if field in inst:\n";
    pyc += "        val = inst[field]\n";
    pyc += "    # convert value based on type and whether the values are unique\n";
    pyc += "    if pt in [\"email\", \"string\"]:\n";
    pyc += "        val = val or \"\"\n";
    pyc += "        val = trim_string_val(val, unique)  # trim all strings. See comment.\n";
    pyc += "        if not val:\n";
    pyc += "            val = None\n";
    pyc += "    elif pt == \"image\":\n";
    pyc += "        if not val:  # Empty data gets set to null\n";
    pyc += "            val = None\n";
    pyc += "    elif pt == \"int\":\n";
    pyc += "        val = val or 0\n";
    pyc += "        val = int(val)  # convert possible \"0\" value\n";
    pyc += "    elif pt == \"dbid\":\n";
    pyc += "        try:\n";
    pyc += "            val = int(val)  # will fail on \"\", \"null\" or other bad values\n";
    pyc += "        except ValueError:\n";
    pyc += "            val = 0\n";
    pyc += "        if unique and not val:  # null vals don't violate UNIQUE constraint\n";
    pyc += "            val = None          # otherwise use 0 as val may be required\n";
    pyc += "    return val\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "# Read the given field from the inst or the default values, then convert it\n";
    pyc += "# from a db value to an app value.  \"app\" means the server side module\n";
    pyc += "# calling this module, not the web client.  Image binary values and json\n";
    pyc += "# field values are not decoded, but get safe defaults if NULL.  dbids are\n";
    pyc += "# converted to strings.\n";
    pyc += "def db2app_fieldval(entity, field, inst):\n";
    pyc += "    if entity:\n";
    pyc += "        pt = entdefs[entity][field][\"pt\"]\n";
    pyc += "        val = entdefs[entity][field][\"dv\"]\n";
    pyc += "    else:\n";
    pyc += "        pt = dbflds[field][\"pt\"]\n";
    pyc += "        val = dbflds[field][\"dv\"]\n";
    pyc += "    if field in inst:\n";
    pyc += "        val = inst[field]\n";
    pyc += "    # convert value based on type\n";
    pyc += "    if pt in [\"email\", \"string\"]:\n";
    pyc += "        if not val:  # A null value gets set to the empty string\n";
    pyc += "            val = \"\"\n";
    pyc += "        val = str(val)  # db interface might have autoconverted to int\n";
    pyc += "    elif pt == \"image\":\n";
    pyc += "        if not val:  # A null value gets set to the empty string\n";
    pyc += "            val = \"\"\n";
    pyc += "    elif pt == \"int\":\n";
    pyc += "        if not val:  # Convert null values to 0\n";
    pyc += "            val = 0\n";
    pyc += "    elif pt == \"dbid\":\n";
    pyc += "        if not val:  # A zero or null value gets set to falsey empty string\n";
    pyc += "            val = \"\"\n";
    pyc += "        else:\n";
    pyc += "            val = str(val)\n";
    pyc += "    return val\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def ISO2dt(isostr):\n";
    pyc += "    isostr = re.sub(r\"\\.\\d*Z\", \"Z\", isostr)  # remove microsecond if any\n";
    pyc += "    dt = datetime.datetime.utcnow()\n";
    pyc += "    dt = dt.strptime(isostr, \"%Y-%m-%dT%H:%M:%SZ\")\n";
    pyc += "    return dt\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def dt2ISO(dt):\n";
    pyc += "    iso = str(dt.year) + \"-\" + str(dt.month).rjust(2, '0') + \"-\"\n";
    pyc += "    iso += str(dt.day).rjust(2, '0') + \"T\" + str(dt.hour).rjust(2, '0')\n";
    pyc += "    iso += \":\" + str(dt.minute).rjust(2, '0') + \":\"\n";
    pyc += "    iso += str(dt.second).rjust(2, '0') + \"Z\"\n";
    pyc += "    return iso\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def nowISO():\n";
    pyc += "    \"\"\" Return the current time as an ISO string \"\"\"\n";
    pyc += "    return dt2ISO(datetime.datetime.utcnow())\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def initialize_timestamp_fields(fields, vck):\n";
    pyc += "    ts = nowISO()\n";
    pyc += "    if \"created\" not in fields or not fields[\"created\"] or vck != \"override\":\n";
    pyc += "        fields[\"created\"] = ts\n";
    pyc += "    if \"modified\" not in fields or not fields[\"modified\"] or vck != \"override\":\n";
    pyc += "        fields[\"modified\"] = ts + \";1\"\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def verify_timestamp_fields(entity, dsId, fields, vck):\n";
    pyc += "    if vck == \"override\" and \"created\" in fields and \"modified\" in fields:\n";
    pyc += "        return fields # skip query and use specified values\n";
    pyc += "    if not vck or not vck.strip():\n";
    pyc += "        raise ValueError(\"Version check required to update \" + entity +\n";
    pyc += "                         \" \" + str(dsId))\n";
    pyc += "    existing = cfbk(entity, \"dsId\", dsId)\n";
    pyc += "    if not existing:\n";
    pyc += "        raise ValueError(\"Existing \" + entity + \" \" + str(dsId) + \" not found.\")\n";
    pyc += "    if vck != \"override\" and existing[\"modified\"] != vck:\n";
    pyc += "        logging.error(\"verify_timestamp_fields rejecting mod of \" + entity +\n"
    pyc += "                      \" \" + str(dsId) + \". existing: \" + existing[\"modified\"] +\n"
    pyc += "                      \", received: \" + vck + \".\")\n"
    pyc += "        raise ValueError(\"Update error. Outdated data given for \" + entity +\n";
    pyc += "                         \" \" + str(dsId) + \".\")\n";
    pyc += "    if \"created\" not in fields or not fields[\"created\"] or vck != \"override\":\n";
    pyc += "        fields[\"created\"] = existing[\"created\"]\n";
    pyc += "    ver = 1\n";
    pyc += "    mods = existing[\"modified\"].split(\";\")\n";
    pyc += "    if len(mods) > 1:\n";
    pyc += "        ver = int(mods[1]) + 1\n";
    pyc += "    if \"modified\" not in fields or not fields[\"modified\"] or vck != \"override\":\n";
    pyc += "        fields[\"modified\"] = nowISO() + \";\" + str(ver)\n";
    pyc += "    return existing\n";
    return pyc;
}


function writeApp2DB (edef) {
    var pyc = "";
    pyc += "# Convert the given " + edef.entity + " inst dict from app values to db values.  Removes\n";
    pyc += "# the dsType field to avoid trying to write it to the db.\n";
    pyc += "def app2db_" + edef.entity + "(inst, fill=True):\n";
    pyc += "    cnv = {}\n";
    pyc += "    cnv[\"dsId\"] = None\n";
    pyc += "    if \"dsId\" in inst:\n";
    pyc += "        cnv[\"dsId\"] = app2db_fieldval(None, \"dsId\", inst)\n";
    pyc += "    if fill or \"created\" in inst:\n";
    pyc += "        cnv[\"created\"] = app2db_fieldval(None, \"created\", inst)\n";
    pyc += "    if fill or \"modified\" in inst:\n";
    pyc += "        cnv[\"modified\"] = app2db_fieldval(None, \"modified\", inst)\n";
    pyc += "    if fill or \"batchconv\" in inst:\n";
    pyc += "        cnv[\"batchconv\"] = app2db_fieldval(None, \"batchconv\", inst)\n";
    edef.fields.forEach(function (fd) {
        pyc += "    if fill or \"" + fd.f + "\" in inst:\n";
        pyc += "        cnv[\"" + fd.f + "\"] = app2db_fieldval(\"" + edef.entity + "\", \"" + fd.f + "\", inst)\n"; });
    pyc += "    return cnv\n";
    return pyc;
}


function writeDB2App (edef) {
    var pyc = "";
    pyc += "# Convert the given " + edef.entity + " inst dict from db values to app values.  Adds the\n";
    pyc += "# dsType field for general app processing.\n";
    pyc += "def db2app_" + edef.entity + "(inst):\n";
    pyc += "    cnv = {}\n";
    pyc += "    cnv[\"dsType\"] = \"" + edef.entity + "\"\n";
    pyc += "    cnv[\"dsId\"] = db2app_fieldval(None, \"dsId\", inst)\n";
    pyc += "    cnv[\"created\"] = db2app_fieldval(None, \"created\", inst)\n";
    pyc += "    cnv[\"modified\"] = db2app_fieldval(None, \"modified\", inst)\n";
    pyc += "    cnv[\"batchconv\"] = db2app_fieldval(None, \"batchconv\", inst)\n";
    edef.fields.forEach(function (fd) {
        pyc += "    cnv[\"" + fd.f + "\"] = db2app_fieldval(\"" + edef.entity + "\", \"" + fd.f + "\", inst)\n"; });
    pyc += "    return cnv\n";
    return pyc;
}


function app2dbConversions () {
    var pyc = "";
    var definitions = ddefs.dataDefinitions();
    definitions.forEach(function (edef) {
        pyc += writeApp2DB(edef) + "\n\n" + writeDB2App(edef) + "\n\n"; });
    return pyc;
}


function dblogMessager () {
    var pyc = "";
    var lfs = "";
    var definitions = ddefs.dataDefinitions();
    pyc += "def dblogmsg(op, entity, res):\n";
    definitions.forEach(function (edef) {
        if(edef.logflds) {
            if(lfs) {
                lfs += ","; }
            lfs += "\n        \"" + edef.entity + "\": [";
            edef.logflds.forEach(function (logfld, idx) {
                if(idx) {
                    lfs += ", "; }
                lfs += "\"" + logfld + "\""; });
            lfs += "]"; } });
    pyc += "    log_summary_flds = {" + lfs + "}\n";
    pyc += "    if res:\n";
    pyc += "        if op != \"QRY\":  # query is already a list, listify anything else\n";
    pyc += "            res = [res]\n";
    pyc += "        for obj in res:\n";
    pyc += "            msg = \"db\" + op + \" \" + entity + \" \" + obj[\"dsId\"]\n";
    pyc += "            if op in [\"UPD\", \"CAC\"]:\n";
    pyc += "                msg += \" ;\" + obj[\"modified\"].split(\";\")[1]\n";
    pyc += "            if entity in log_summary_flds:\n";
    pyc += "                for field in log_summary_flds[entity]:\n";
    pyc += "                    msg += \" \" + str(obj[field])[0:60]\n";
    pyc += "            logging.info(msg)\n";
    pyc += "    else:  # no res, probably a delete\n";
    pyc += "        logging.info(\"db\" + op + \" \" + entity + \" -no obj details-\")\n";
    return pyc;
}


function writeInsertFunction (edef) {
    var pyc = "";
    pyc += "# Write a new " + edef.entity + " row, using the given field values or defaults.\n";
    pyc += "def insert_new_" + edef.entity + "(cnx, cursor, fields):\n";
    pyc += "    fields = app2db_" + edef.entity + "(fields)\n";
    pyc += "    stmt = (\n";
    pyc += "        \"INSERT INTO " + edef.entity + " (created, modified";
    edef.fields.forEach(function (fd) {
        pyc += ", " + fd.f; });
    pyc += ") \"\n";
    pyc += "        \"VALUES (%(created)s, %(modified)s";
    edef.fields.forEach(function (fd) {
        pyc += ", %(" + fd.f + ")s"; });
    pyc += ")\")\n";
    pyc += "    data = {\n";
    pyc += "        'created': fields.get(\"created\"),\n";
    pyc += "        'modified': fields.get(\"modified\")";
    edef.fields.forEach(function (fd) {
        pyc += ",\n        '" + fd.f + "': fields.get(\"" + fd.f + "\", " +
            "entdefs[\"" + edef.entity + "\"][\"" + fd.f + "\"][\"dv\"])"; });
    pyc += "}\n";
    pyc += "    cursor.execute(stmt, data)\n";
    pyc += "    fields[\"dsId\"] = cursor.lastrowid\n";
    pyc += "    cnx.commit()\n";
    pyc += "    fields = db2app_" + edef.entity + "(fields)\n";
    pyc += "    dblogmsg(\"ADD\", \"" + edef.entity + "\", fields)\n";
    pyc += "    return fields\n";
    return pyc;
}


function writeUpdateFunction (edef) {
    var pyc = "";
    pyc += "# Update the specified " + edef.entity + " row with the given field values.\n";
    pyc += "def update_existing_" + edef.entity + "(context, fields):\n";
    pyc += "    fields = app2db_" + edef.entity + "(fields, fill=False)\n";
    pyc += "    dsId = int(fields[\"dsId\"])  # Verify int value\n";
    pyc += "    stmt = \"\"\n";
    pyc += "    for field in fields:  # only updating the fields passed in\n";
    pyc += "        if stmt:\n";
    pyc += "            stmt += \", \"\n";
    pyc += "        stmt += field + \"=(%(\" + field + \")s)\"\n";
    pyc += "    stmt = \"UPDATE " + edef.entity + " SET \" + stmt + \" WHERE dsId=\" + str(dsId)\n";
    pyc += "    if context[\"vck\"] != \"override\":\n";
    pyc += "        stmt += \" AND modified=\\\"\" + context[\"vck\"] + \"\\\"\"\n";
    pyc += "    data = {}\n";
    pyc += "    for field in fields:\n";
    pyc += "        data[field] = fields[field]\n";
    pyc += "    context[\"cursor\"].execute(stmt, data)\n";
    pyc += "    if context[\"cursor\"].rowcount < 1 and context[\"vck\"] != \"override\":\n";
    pyc += "        logging.error(stmt + \" \" + json.dumps(data))\n";
    pyc += "        entcache.cache_clean()  # out of sync, clear it all\n";
    pyc += "        raise ValueError(\"" + edef.entity + "\" + str(dsId) + \" update received outdated version check value \" + context[\"vck\"] + \".\")\n";
    pyc += "    context[\"cnx\"].commit()\n";
    pyc += "    result = context[\"existing\"]\n";
    pyc += "    for field in fields:\n";
    pyc += "        result[field] = fields[field]\n";
    pyc += "    result = db2app_" + edef.entity + "(result)\n";
    pyc += "    dblogmsg(\"UPD\", \"" + edef.entity + "\", result)\n";
    if(edef.cache.minutes && !edef.cache.manualadd) {
        pyc += "    entcache.cache_put(result)\n"; }
    else {  //make sure there isn't an old copy hanging around
        pyc += "    entcache.cache_remove(result)\n"; }
    pyc += "    return result\n";
    return pyc;
}


function entityWriteFunction () {
    var pyc = "";
    var definitions = ddefs.dataDefinitions();
    definitions.forEach(function (edef) {
        pyc += writeInsertFunction(edef) + "\n\n" +
            writeUpdateFunction(edef) + "\n\n"; });
    pyc += "# Write the given dict/object based on the dsType.  Binary field values must\n";
    pyc += "# be base64.b64encode.  Unspecified fields are set to default values for a\n";
    pyc += "# new instance, and left alone on update.  For update, the verification\n";
    pyc += "# check value must match the modified value of the existing instance.\n";
    pyc += "def write_entity(inst, vck=\"1234-12-12T00:00:00Z\"):\n";
    pyc += "    cnx = get_mysql_connector()\n";
    pyc += "    if not cnx:\n";
    pyc += "        raise ValueError(\"Database connection failed.\")\n";
    pyc += "    try:\n";
    pyc += "        cursor = cnx.cursor()\n";
    pyc += "        try:\n";
    pyc += "            entity = inst.get(\"dsType\", None)\n";
    pyc += "            dsId = inst.get(\"dsId\", 0)\n";
    pyc += "            if dsId:\n";
    pyc += "                existing = verify_timestamp_fields(entity, dsId, inst, vck)\n";
    pyc += "                context = {\"cnx\":cnx, \"cursor\":cursor, \"vck\":vck,\n";
    pyc += "                           \"existing\":existing}\n";
    definitions.forEach(function (edef) {
        pyc += "                if entity == \"" + edef.entity + "\":\n";
        pyc += "                    return update_existing_" + edef.entity + "(context, inst)\n"; });
    pyc += "                raise ValueError(\"Cannot modify unknown entity dsType \" +\n";
    pyc += "                                 str(entity))\n";
    pyc += "            # No existing instance to update.  Insert new.\n";
    pyc += "            initialize_timestamp_fields(inst, vck)\n";
    definitions.forEach(function (edef) {
        pyc += "            if entity == \"" + edef.entity + "\":\n";
        pyc += "                return insert_new_" + edef.entity + "(cnx, cursor, inst)\n"; });
    pyc += "            raise ValueError(\"Cannot create unknown entity dsType \" +\n";
    pyc += "                             str(entity))\n";
    pyc += "        except mysql.connector.Error as e:\n";
    pyc += "            raise ValueError(str(e) or \"No mysql error text\")  # see note 1\n";
    pyc += "        finally:\n";
    pyc += "            cursor.close()\n";
    pyc += "    finally:\n";
    pyc += "        cnx.close()\n";
    return pyc;
}


function entityDeleteFunction () {
    var pyc = "";
    pyc += "def delete_entity(entity, dsId):\n";
    pyc += "    cnx = get_mysql_connector()\n";
    pyc += "    if not cnx:\n";
    pyc += "        raise ValueError(\"Database connection failed.\")\n";
    pyc += "    try:\n";
    pyc += "        cursor = cnx.cursor()\n";
    pyc += "        try:\n";
    pyc += "            stmt = \"DELETE FROM \" + entity + \" WHERE dsId=\" + str(dsId)\n";
    pyc += "            cursor.execute(stmt)\n";
    pyc += "            cnx.commit()\n";
    pyc += "            dblogmsg(\"DEL\", entity + \" \" + str(dsId), None)\n";
    pyc += "            # if cache cleanup is needed that is up to caller\n";
    pyc += "        except mysql.connector.Error as e:\n";
    pyc += "            raise ValueError(str(e) or \"No mysql error text\")  # see note 1\n";
    pyc += "        finally:\n";
    pyc += "            cursor.close()\n";
    pyc += "    finally:\n";
    pyc += "        cnx.close()\n";
    return pyc;
}


function writeQueryFunction (edef) {
    var pyc = ""; var fcsv = ""; var oes = "";
    pyc += "def query_" + edef.entity + "(cnx, cursor, where):\n";
    pyc += "    query = \"SELECT dsId, created, modified, \"\n";
    edef.fields.forEach(function (fd) {
        if(fcsv) {
            fcsv += ", "; }
        fcsv += fd.f; });
    pyc += "    query += \"" + fcsv + "\"\n";
    pyc += "    query += \" FROM " + edef.entity + " \" + where\n";
    pyc += "    cursor.execute(query)\n";
    pyc += "    res = []\n";
    pyc += "    for (dsId, created, modified, " + fcsv + ") in cursor:\n";
    edef.fields.forEach(function (fd) {
        if(oes) {
            oes += ", "; }
        oes += "\"" + fd.f + "\": " + fd.f; });
    pyc += "        inst = {\"dsType\": \"" + edef.entity + "\", \"dsId\": dsId, \"created\": created, \"modified\": modified, " + oes + "}\n";
    pyc += "        inst = db2app_" + edef.entity + "(inst)\n";
    pyc += "        res.append(inst)\n";
    pyc += "    dblogmsg(\"QRY\", \"" + edef.entity + "\", res)\n";
    pyc += "    return res\n";
    return pyc;
}


function entityQueryFunction () {
    var pyc = "";
    var definitions = ddefs.dataDefinitions();
    definitions.forEach(function (edef) {
        pyc += writeQueryFunction(edef) + "\n\n"; });
    pyc += "# Fetch all instances of the specified entity kind for the given WHERE\n";
    pyc += "# clause.  The WHERE clause should include a LIMIT, and should only match on\n";
    pyc += "# indexed fields and/or declared query indexes.  For speed and general\n";
    pyc += "# compatibility, only one inequality operator should be used in the match.\n";
    pyc += "def query_entity(entity, where):\n";
    pyc += "    cnx = get_mysql_connector()\n";
    pyc += "    if not cnx:\n";
    pyc += "        raise ValueError(\"Database connection failed.\")\n";
    pyc += "    try:\n";
    pyc += "        cursor = cnx.cursor()\n";
    pyc += "        try:\n";
    definitions.forEach(function (edef) {
        pyc += "            if entity == \"" + edef.entity + "\":\n";
        pyc += "                return query_" + edef.entity + "(cnx, cursor, where)\n"; });
    pyc += "        except mysql.connector.Error as e:\n";
    pyc += "            raise ValueError(str(e) or \"No mysql error text\")  # see note 1\n";
    pyc += "        finally:\n";
    pyc += "            cursor.close()\n";
    pyc += "    finally:\n";
    pyc += "        cnx.close()\n";
    return pyc;
}


function writeObjFieldFilterFunc (edef) {
    var pyc = "";
    pyc += "def visible_" + edef.entity + "_fields(obj, audience):\n";
    pyc += "    filtobj = {}\n";
    pyc += "    for fld, val in obj.items():\n";
    edef.fields.forEach(function (fd) {
        if(ddefs.fieldIs(fd.d, "admin")) {
            pyc += "        if fld == \"" + fd.f + "\":\n";
            pyc += "            continue\n"; }
        if(ddefs.fieldIs(fd.d, "private")) {
            pyc += "        if fld == \"" + fd.f + "\" and audience != \"private\":\n";
            pyc += "            continue\n"; }
        if(ddefs.fieldIs(fd.d, "image")) {
            pyc += "        if fld == \"" + fd.f + "\":\n";
            pyc += "            if obj[\"" + fd.f + "\"]:\n";
            pyc += "                val = obj[\"dsId\"]\n";
            pyc += "            else:\n";
            pyc += "                val = \"\"\n"; } });
    pyc += "        filtobj[fld] = val\n";
    pyc += "    return filtobj\n";
    pyc += "\n";
    pyc += "\n";
    return pyc;
}


function fieldVisibilityFunction () {
    var pyc = "";
    var definitions = ddefs.dataDefinitions();
    definitions.forEach(function (edef) {
        pyc += writeObjFieldFilterFunc(edef); });
    pyc += "# Return a copied object with only the fields appropriate to the audience.\n";
    pyc += "# Specifying audience=\"private\" includes peronal info.  The given obj is\n";
    pyc += "# assumed to already have been through db2app conversion.  Image fields are\n";
    pyc += "# converted to dsId values for separate download.\n";
    pyc += "def visible_fields(obj, audience=\"public\"):\n";
    definitions.forEach(function (edef) {
        pyc += "    if obj[\"dsType\"] == \"" + edef.entity + "\":\n";
        pyc += "        return visible_" + edef.entity + "_fields(obj, audience)\n"; });
    pyc += "    raise ValueError(\"Unknown object dsType: \" + obj[\"dsType\"])\n";
    return pyc;
}


function appSpecificFunctions () {
    var pyc = "";
    pyc += "# Make a unique key from the ti/ar/ab song fields\n"
    pyc += "def get_song_key(song):\n"
    pyc += "    ti = song[\"ti\"]\n"
    pyc += "    ar = song.get(\"ar\", \"\")\n"
    pyc += "    ab = song.get(\"ab\", \"\")\n"
    pyc += "    srx = re.compile(r\"[\\\s\'\\\"]\")\n"
    pyc += "    skey = re.sub(srx, \"\", ti) + re.sub(srx, \"\", ar) + re.sub(srx, \"\", ab)\n"
    pyc += "    skey = skey.lower()\n"
    pyc += "    return skey\n"
    pyc += "\n"
    pyc += "\n"
    pyc += "# For a given user, count their total songs and how many are streaming\n";
    pyc += "def fetch_song_counts(uid):\n";
    pyc += "    cnx = get_mysql_connector()\n";
    pyc += "    if not cnx:\n";
    pyc += "        raise ValueError(\"Database connection failed.\")\n";
    pyc += "    try:\n";
    pyc += "        cursor = cnx.cursor()\n";
    pyc += "        try:\n";
    pyc += "            query = (\"SELECT COUNT(dsId) AS hubdb\" +\n";
    pyc += "                     \", COUNT(IF(spid LIKE \\\"z:%\\\", 1, NULL)) AS spotify\" +\n";
    pyc += "                     \" FROM (SELECT dsId, spid FROM Song WHERE aid=\" +\n";
    pyc += "                     str(uid) + \" AS usersongs;\")\n";
    pyc += "            cursor.execute(query)\n";
    pyc += "            res = []\n";
    pyc += "            for (hubdb, spotify) in cursor:\n";
    pyc += "                res.append({\"hubdb\":hubdb, \"spotify\":spotify})\n";
    pyc += "            return res\n";
    pyc += "        except mysql.connector.Error as e:\n";
    pyc += "            raise ValueError(str(e) or \"No song fetch error details\")\n";
    pyc += "        finally:\n";
    pyc += "            cursor.close()\n";
    pyc += "    finally:\n";
    pyc += "        cnx.close()\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def collaborate_default_ratings(uid, fid, since=\"1970-01-01T00:00:00Z\",\n";
    pyc += "                                limit=200):\n";
    pyc += "    cnx = get_mysql_connector()\n";
    pyc += "    if not cnx:\n";
    pyc += "        raise ValueError(\"Database connection failed.\")\n";
    pyc += "    try:\n";
    pyc += "        cursor = cnx.cursor()\n";
    pyc += "        try:\n";
    pyc += "            query = (\"SELECT us.dsId as dsId\" +\n";
    pyc += "                     \", us.created as created, us.modified as modified\" +\n";
    pyc += "                     \", us.ti as ti, us.ar as ar, us.ab as ab\" +\n";
    pyc += "                     \", us.path as path\" +\n";
    pyc += "                     \", fs.aid as mfid, fs.created as mfcreated\" +\n";
    pyc += "                     \", fs.el as el, fs.al as al, fs.kws as kws, fs.rv as rv\" +\n";
    pyc += "                     \" FROM Song AS us, Song AS fs\" +\n";
    pyc += "                     \" WHERE us.aid=\" + uid + \" AND fs.aid=\" + fid +\n";
    pyc += "                     \" AND fs.created > \\\"\" + since + \"\\\"\"\n";
    pyc += "                     \" AND ((us.smti=fs.smti AND us.smar=fs.smar) OR \" +\n";
    pyc += "                     \"      (us.spid=fs.spid))\" +\n";
    pyc += "                     \" AND us.el = 49 AND us.al = 49 AND us.kws IS NULL\" +\n";
    pyc += "                     \" AND (fs.el != 49 OR fs.al != 49 OR fs.kws IS NOT NULL)\" +\n";
    pyc += "                     \" ORDER BY fs.created LIMIT \" + str(limit))\n";
    pyc += "            logging.info(\"collab query: \" + query)\n";
    pyc += "            cursor.execute(query)\n";
    pyc += "            res = []\n";
    pyc += "            for (dsId, created, modified, ti, ar, ab, path, mfid, mfcreated,\n";
    pyc += "                 el, al, kws, rv) in cursor:\n";
    pyc += "                res.append({\"dsType\":\"Song\", \"dsId\":str(dsId),\n";
    pyc += "                            \"created\":created, \"modified\":modified,\n";
    pyc += "                            \"ti\":ti, \"ar\":ar, \"ab\":ab, \"path\":path,\n";
    pyc += "                            \"mfid\":str(mfid), \"mfcreated\":mfcreated,\n";
    pyc += "                            \"el\":el, \"al\":al, \"kws\":kws, \"rv\":rv})\n";
    pyc += "            logging.info(\"collab res \" + str(len(res)) + \" Songs\")\n";
    pyc += "            return res\n";
    pyc += "        except mysql.connector.Error as e:\n";
    pyc += "            raise ValueError(str(e) or \"No collab error details\")\n";
    pyc += "        finally:\n";
    pyc += "            cursor.close()\n";
    pyc += "    finally:\n";
    pyc += "        cnx.close()\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "# Count the songs for the given user from the given music fan\n";
    pyc += "def count_contributions(uid, mfid):\n";
    pyc += "    cnx = get_mysql_connector()\n";
    pyc += "    if not cnx:\n";
    pyc += "        raise ValueError(\"Database connection failed.\")\n";
    pyc += "    try:\n";
    pyc += "        cursor = cnx.cursor()\n";
    pyc += "        try:\n";
    pyc += "            query = (\"SELECT COUNT(dsId) AS ccnt\" +\n";
    pyc += "                     \" FROM Song WHERE aid=\" + str(uid) +\n";
    pyc += "                     \" AND srcid=\" + str(mfid))\n";
    pyc += "            cursor.execute(query)\n";
    pyc += "            res = []\n";
    pyc += "            for ccnt in cursor:\n";
    pyc += "                res.append({\"mfid\":mfid, \"ccnt\":ccnt})\n";
    pyc += "            return res\n";
    pyc += "        except mysql.connector.Error as e:\n";
    pyc += "            raise ValueError(str(e) or \"No song fetch error details\")\n";
    pyc += "        finally:\n";
    pyc += "            cursor.close()\n";
    pyc += "    finally:\n";
    pyc += "        cnx.close()\n";
    pyc += "\n";
    pyc += "\n";
    pyc += "def custom_query(sql, resflds):\n";
    pyc += "    cnx = get_mysql_connector()  # MySQLConnection\n";
    pyc += "    if not cnx:\n";
    pyc += "        raise ValueError(\"Database connection failed.\")\n";
    pyc += "    try:\n";
    pyc += "        cursor = cnx.cursor()  # MySQLCursor\n";
    pyc += "        try:\n";
    pyc += "            cursor.execute(sql)\n";
    pyc += "            res = []\n";
    pyc += "            for valtuple in cursor:\n";
    pyc += "                inst = dict(zip(resflds, list(valtuple)))\n";
    pyc += "                res.append(inst)\n";
    pyc += "            return res\n";
    pyc += "        except mysql.connector.Error as e:\n";
    pyc += "            raise ValueError(str(e) or \"No custom_query error details\")\n";
    pyc += "        finally:\n";
    pyc += "            cursor.close()\n";
    pyc += "    finally:\n";
    pyc += "        cnx.close()\n";
    return pyc;
}


function createPythonDBAcc () {
    var pyc = "";
    pyc += "\"\"\" Autogenerated db CRUD and related utilities \"\"\"\n";
    pyc += "########################################\n";
    pyc += "#\n";
    pyc += "#       D O   N O T   E D I T\n";
    pyc += "#\n";
    pyc += "# This file was written by makeCRUD.js.  Any changes should be made there.\n";
    pyc += "#\n";
    pyc += "########################################\n";
    pyc += "\n";
    pyc += "#pylint: disable=line-too-long\n";
    pyc += "#pylint: disable=too-many-lines\n";
    pyc += "#pylint: disable=trailing-newlines\n";
    pyc += "#pylint: disable=wrong-import-position\n";
    pyc += "#pylint: disable=wrong-import-order\n";
    pyc += "#pylint: disable=invalid-name\n";
    pyc += "#pylint: disable=missing-function-docstring\n";
    pyc += "#pylint: disable=consider-using-in\n";
    pyc += "#pylint: disable=logging-not-lazy\n";
    pyc += "#pylint: disable=inconsistent-return-statements\n";
    pyc += "#pylint: disable=too-many-return-statements\n";
    pyc += "#pylint: disable=too-many-branches\n";
    pyc += "#pylint: disable=too-many-locals\n";
    pyc += "#pylint: disable=unused-argument\n";
    pyc += "import logging\n";
    pyc += "import flask\n";
    pyc += "import re\n";
    pyc += "import datetime\n";
    pyc += "import pickle\n";
    pyc += "import json\n";
    pyc += "import mysql.connector\n";
    pyc += "import py.mconf as mconf\n";
    pyc += "\n";
    pyc += "# Notes:\n";
    pyc += "# (1) In general, all processing that might raise a mysql.connector.Error is\n";
    pyc += "# wrapped to raise a ValueError instead, to support callers working at a\n";
    pyc += "# higher level of CRUD abstraction.  The general processing contruct\n";
    pyc += "#    except mysql.connector.Error as e:\n";
    pyc += "#        raise ValueError from e\n";
    pyc += "# is not used for this purpose because it produces an undecorated ValueError\n";
    pyc += "# without the str(e) text, making it harder to track down what the problem\n";
    pyc += "# actually was.  The source can be found from the Error __context__, but\n";
    pyc += "# that is also set when raising a new Error, so the general use here is\n";
    pyc += "#        raise ValueError(str(e) or \"No mysql error text\")\n";
    pyc += "\n";
    pyc += "# Reserved database fields used for every instance:\n";
    pyc += "#  - dsId: a long int, possibly out of range of a javascript integer,\n";
    pyc += "#    possibly non-sequential, uniquely identifying an entity instance.\n";
    pyc += "#    The entity type + dsId uniquely identifies an object in the system.\n";
    pyc += "#  - created: An ISO timestamp when the instance was first written.\n";
    pyc += "#  - modified: An ISO timestamp followed by ';' followed by mod count.\n";
    pyc += "#  - batchconv: Arbitray string for batch database conversion.\n";
    pyc += "dbflds = {\"dsId\": {\"pt\": \"dbid\", \"un\": True, \"dv\": 0},\n";
    pyc += "          \"created\": {\"pt\": \"string\", \"un\": False, \"dv\": \"\"},\n";
    pyc += "          \"modified\": {\"pt\": \"string\", \"un\": False, \"dv\": \"\"},\n";
    pyc += "          \"batchconv\": {\"pt\": \"string\", \"un\": False, \"dv\": \"\"}}\n";
    pyc += "\n";
    pyc += entityDefinitions() + "\n\n";
    pyc += entityKeyFields() + "\n\n";
    pyc += entityCache() + "\n\n";
    pyc += helperFunctions() + "\n\n";
    pyc += app2dbConversions();
    pyc += dblogMessager() + "\n\n";
    pyc += entityWriteFunction() + "\n\n";
    pyc += entityDeleteFunction() + "\n\n";
    pyc += entityQueryFunction() + "\n\n";
    pyc += fieldVisibilityFunction() + "\n\n";
    pyc += appSpecificFunctions() + "\n\n";
    writeFileSync(srcdir + "/dbacc.py", pyc);
}


////////////////////////////////////////
// JavaScript code

function writePersistentTypes () {
    var types = [];
    var definitions = ddefs.dataDefinitions();
    definitions.forEach(function (edef) {
        types.push("\"" + edef.entity + "\""); });
    return "    var persistentTypes = [" + types.join(", ") + "];\n";
}


function writeDeserializeFunction () {
    var definitions = ddefs.dataDefinitions();
    var jsc = "";
    jsc += "    //All json fields are initialized to {} so they can be accessed directly.\n";
    jsc += "    function reconstituteFieldJSONObject (field, obj) {\n";
    jsc += "        if(!obj[field]) {\n";
    jsc += "            obj[field] = {}; }\n";
    jsc += "        else {\n";
    jsc += "            var text = obj[field];\n";
    jsc += "            try {\n";
    jsc += "                obj[field] = JSON.parse(text);\n";
    jsc += "            } catch (e) {\n";
    jsc += "                jt.log(\"reconstituteFieldJSONObject \" + obj.dsType + \" \" +\n";
    jsc += "                       obj.dsId + \" \" + field + \" reset to empty object from \" +\n";
    jsc += "                       text + \" Error: \" + e);\n";
    jsc += "                obj[field] = {};\n";
    jsc += "            } }\n";
    jsc += "    }\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    function reconstituteFieldJSONArray (field, obj) {\n";
    jsc += "        reconstituteFieldJSONObject(field, obj);\n";
    jsc += "        if(!Array.isArray(obj[field])) {\n";
    jsc += "            obj[field] = []; }\n";
    jsc += "    }\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    function deserialize (obj) {\n";
    jsc += "        switch(obj.dsType) {\n";
    definitions.forEach(function (edef) {
        jsc += "        case \"" + edef.entity + "\":\n";
        edef.fields.forEach(function (fd) {
            if(ddefs.fieldIs(fd.d, "json")) {
                jsc += "            reconstituteFieldJSONObject(\"" +
                    fd.f + "\", obj);\n"; }
            else if(ddefs.fieldIs(fd.d, "jsarr")) {
                jsc += "            reconstituteFieldJSONArray(\"" +
                    fd.f + "\", obj);\n"; } });
        jsc += "            break;\n"; });
    jsc += "        }\n";
    jsc += "        return obj;\n";
    jsc += "    }\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    function serialize (obj) {\n";
    jsc += "        switch(obj.dsType) {\n";
    definitions.forEach(function (edef) {
        jsc += "        case \"" + edef.entity + "\":\n";
        edef.fields.forEach(function (fd) {
            if(ddefs.fieldIs(fd.d, "json") || ddefs.fieldIs(fd.d, "jsarr")) {
                jsc += "            obj." + fd.f + " = JSON.stringify(obj." +
                    fd.f + ");\n"; } });
        jsc += "            break;\n"; });
    jsc += "        }\n";
    jsc += "        return obj;\n";
    jsc += "    }\n";
    return jsc;
}


function writeClearPrivilegedFunction () {
    var definitions = ddefs.dataDefinitions();
    var jsc = "";
    jsc += "    function clearPrivilegedFields (obj) {\n";
    jsc += "        switch(obj.dsType) {\n";
    definitions.forEach(function (edef) {
        jsc += "        case \"" + edef.entity + "\":\n";
        edef.fields.forEach(function (fd) {
            if(ddefs.fieldIs(fd.d, "priv")) {  //adm fields never leave server
                jsc += "            obj." + fd.f + " = \"\";\n"; } });
        jsc += "            break;\n"; });
    jsc += "        }\n";
    jsc += "    }\n";
    return jsc;
}


function createJSServerAcc () {
    var jsc = "";
    jsc += "//////////////////////////////////////////////////\n";
    jsc += "//\n";
    jsc += "//     D O   N O T   E D I T\n";
    jsc += "//\n";
    jsc += "// This file was written by makeCRUD.js.  Any changes should be made there.\n";
    jsc += "//\n";
    jsc += "//////////////////////////////////////////////////\n";
    jsc += "// Local object reference cache and server persistence access.  Automatically\n";
    jsc += "// serializes/deserializes JSON fields.\n";
    jsc += "\n";
    jsc += "/*global app, jt, window, console */\n";
    jsc += "\n";
    jsc += "/*jslint browser, white, fudge, long */\n";
    jsc += "\n";
    jsc += "app.refmgr = (function () {\n";
    jsc += "    \"use strict\";\n";
    jsc += "\n";
    jsc += "    var cache = {};\n";
    jsc += "\n";
    jsc += writePersistentTypes() + "\n\n";
    jsc += writeDeserializeFunction() + "\n\n";
    jsc += writeClearPrivilegedFunction() + "\n\n";
    jsc += "return {\n";
    jsc += "\n";
    jsc += "    cached: function (dsType, dsId) {  //Returns the cached obj or null\n";
    jsc += "        if(dsType && dsId && cache[dsType] && cache[dsType][dsId]) {\n";
    jsc += "            return cache[dsType][dsId]; }\n";
    jsc += "        return null; },\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    put: function (obj) {  //obj is already deserialized\n";
    jsc += "        if(!obj) {\n";
    jsc += "            jt.log(\"refmgr.put: Attempt to put null obj\");\n";
    jsc += "            console.trace(); }\n";
    jsc += "        clearPrivilegedFields(obj);  //no sensitive info in cache\n";
    jsc += "        cache[obj.dsType] = cache[obj.dsType] || {};\n";
    jsc += "        cache[obj.dsType][obj.dsId] = obj;\n";
    jsc += "        return obj;\n";
    jsc += "    },\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    getFull: function (dsType, dsId, contf) {\n";
    jsc += "        var obj = app.refmgr.cached(dsType, dsId);\n";
    jsc += "        if(obj) {  //force an async callback for consistent code flow\n";
    jsc += "            return setTimeout(function () { contf(obj); }, 50); }\n";
    jsc += "        if(persistentTypes.indexOf(dsType) < 0) {\n";
    jsc += "            jt.log(\"refmgr.getFull: unknown dsType \" + dsType);\n";
    jsc += "            console.trace(); }\n";
    jsc += "        var url = app.util.dr(\"/api/fetchobj?dt=\" + dsType + \"&di=\" + dsId +\n";
    jsc += "                         jt.ts(\"&cb=\", \"second\"));\n";
    jsc += "        var sem = jt.semaphore(\"refmgr.getFull\" + dsType + dsId);\n";
    jsc += "        if(sem && sem.critsec === \"processing\") {\n";
    jsc += "            setTimeout(function () {\n";
    jsc += "                app.refmgr.getFull(dsType, dsId, contf); }, 200);\n";
    jsc += "            return; }  //try again later, hopefully find cached\n";
    jsc += "        var logpre = \"refmgr.getFull \" + dsType + \" \" + dsId + \" \";\n";
    jsc += "        jt.call(\"GET\", url, null,\n";
    jsc += "                function (objs) {\n";
    jsc += "                    var retobj = null;\n";
    jsc += "                    if(objs.length > 0) {\n";
    jsc += "                        retobj = objs[0];\n";
    jsc += "                        jt.log(logpre + \"cached.\");\n";
    jsc += "                        deserialize(retobj);\n";
    jsc += "                        app.refmgr.put(retobj); }\n";
    jsc += "                    contf(retobj); },\n";
    jsc += "                function (code, errtxt) {\n";
    jsc += "                    jt.log(logpre + code + \": \" + errtxt);\n";
    jsc += "                    contf(null); },\n";
    jsc += "                sem);\n";
    jsc += "    },\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    uncache: function (dsType, dsId) {\n";
    jsc += "        cache[dsType] = cache[dsType] || {};\n";
    jsc += "        cache[dsType][dsId] = null;\n";
    jsc += "    },\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    serverUncache: function (dsType, dsId, contf, errf) {\n";
    jsc += "        app.refmgr.uncache(dsType, dsId);\n";
    jsc += "        var logpre = \"refmgr.serverUncache \" + dsType + \" \" + dsId + \" \";\n";
    jsc += "        var url = app.util.dr(\"/api/uncache?dt=\" + dsType + \"&di=\" + dsId +\n";
    jsc += "                         jt.ts(\"&cb=\", \"second\"));\n";
    jsc += "        jt.call(\"GET\", url, null,\n";
    jsc += "                function () {\n";
    jsc += "                    jt.log(logpre + \"completed.\");\n";
    jsc += "                    if(contf) { contf(); } },\n";
    jsc += "                function (code, errtxt) {\n";
    jsc += "                    jt.log(logpre + \"failed \" + code + \": \" + errtxt);\n";
    jsc += "                    if(errf) { errf(); } },\n";
    jsc += "                jt.semaphore(\"refmgr.serverUncache\" + dsType + dsId));\n";
    jsc += "    },\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    deserialize: function (obj) {\n";
    jsc += "        return deserialize(obj);\n";
    jsc += "    },\n";
    jsc += "\n";
    jsc += "\n";
    jsc += "    postdata: function (obj, skips) {\n";
    jsc += "        serialize(obj);\n";
    jsc += "        var dat = jt.objdata(obj, skips);\n";
    jsc += "        deserialize(obj);\n";
    jsc += "        return dat;\n";
    jsc += "    }\n";
    jsc += "\n";
    jsc += "}; //end of returned functions\n";
    jsc += "}());\n";
    jsc += "\n";
    writeFileSync(jsdir + "/refmgr.js", jsc);
}


////////////////////////////////////////
// Write the files

createDatabaseSQL();
createPythonDBAcc();
createJSServerAcc();
