import nav.db,psycopg

UPDATE_ENTRY = 'update_entry'
# REQ_TRUE: a required field
# REQ_FALSE: not required
# REQ_NONEMPTY: not required, but don't insert empty field
REQ_TRUE = 1
REQ_FALSE = 2
REQ_NONEMPTY = 3

def executeSQL(sqllist):
    connection = nav.db.getConnection('editdb','manage')
    database = connection.cursor()
    for sql in sqllist:
        database.execute(sql)
    connection.commit()
    connection.close()

def executeSQLreturn(sql):
    connection = nav.db.getConnection('editdb','manage')
    database = connection.cursor()
    database.execute(sql)
    return database.fetchall()

def addEntryBulk(data,table):
    sqllist = []
    for row in data:
        sql = 'INSERT INTO ' + table + ' ('
        first = True
        for field,value in row.items():
            if len(value):
                if not first:
                    sql += ','
                sql += field
                first = False
        sql += ') VALUES ('
        first = True
        for field,value in row.items():
            if len(value):    
                if not first:
                    sql += ','
                sql += "'" + value + "'"
                first = False
        sql += ')'
        sqllist.append(sql)
    executeSQL(sqllist)

def addEntry(req,templatebox,table,unique=None):
    # req: request object containing a form
    # templatebox: containing field defenitions
    # table: string with tablename
    # unique: string with unique fieldname
    error = None
    sql = 'INSERT INTO ' + table + ' ('
    first = True
    for field,descr in templatebox.fields.items():
        if req.form.has_key(field):
            if len(req.form[field]):
                if not first:
                    sql += ','
                sql += field
                first = False
    sql += ') VALUES ('
    first = True
    for field,descr in templatebox.fields.items():
        if req.form.has_key(field):
            if len(req.form[field]):    
                if not first:
                    sql += ','
                sql += "'" + req.form[field] + "'"
                first = False
    sql += ')'
    sqllist = [sql]
    try:
        executeSQL(sqllist)
    except psycopg.IntegrityError,e:
        if type(unique) is list:
            error = 'There already exists an entry with '
            first = True
            for field in unique:
                if not first:
                    error += ' and '
                error += field + "='" + req.form[field] + "'"
                first = False
        else:
            error = "There already exists an entry with the value '" + \
                    req.form[unique] + "' for the unique field '" + unique + "'"
    return error

def addEntryFields(fields,table,sequence=None):
    # Add a new entry using the dict fields which contain
    # key,value pairs (used when data from more than two templatexboxes
    # are to be inserted. eg. when inserting a netbox)

    # Sequence is a tuple (idfield,sequencename). If given, get
    # the nextval from sequence and set the idfield to this value
    nextid = None
    if sequence:
        idfield,seq = sequence
        sql = "SELECT nextval('%s')" % (seq,)
        result = executeSQLreturn(sql)
        nextid = str(result[0][0])
        fields[idfield] = nextid

    sql = 'INSERT INTO ' + table + ' ('
    first = True
    for field,value in fields.items():
        if not first:
            sql += ','
        sql += field
        first = False
    sql += ') VALUES ('
    first = True
    for field,value in fields.items():
        if not first:
            sql += ','
        sql += "'" + value + "'"
        first = False
    sql += ')'
    sqllist = [sql]
    executeSQL(sqllist)
    return nextid

def updateEntryFields(fields,table,idfield,updateid):
    sql = 'UPDATE ' + table + ' SET '
    first = True
    for field,value in fields.items():
        if not first:
            sql += ','
        sql += field + "='" + value + "'"
        first = False
    sql += ' WHERE ' + idfield + "='" + updateid + "'"
    sqllist = [sql]
    executeSQL(sqllist)

def updateEntry(req,templatebox,table,idfield,staticid=False,
                unique=None,nonEmpty=None):
    """ 
    Parses the form data in the request object based on the 
    fields defined in the templatebox, and updates the table 
    """
    sqllist = []
    data = []
    error = None
 
    # get the name of one of the fields that should be present
    presentfield = templatebox.fields.keys()[0]

    if type(req.form[presentfield]) is list:
        for i in range(0,len(req.form[presentfield])):
            values = {}
            for field,descr in templatebox.fields.items():
                if req.form.has_key(field):
                    # Don't insert empty strings into fields
                    # where required = REQ_NONEMPTY
                    if len(req.form[field][i]):
                        values[field] = req.form[field][i]
                    else:
                        if descr[1] != REQ_NONEMPTY:
                            values[field] = req.form[field][i]
            # the hidden element UPDATE_ENTRY contains the original ID
            data.append((req.form[UPDATE_ENTRY][i],values))
    else:
        values = {}
        for field,descr in templatebox.fields.items():
            if req.form.has_key(field):
                # Don't insert empty strings into fields
                # where required = REQ_NONEMPTY
                if len(req.form[field]):
                    values[field] = req.form[field]
                else:
                    if descr[1] != REQ_NONEMPTY:
                        values[field] = req.form[field]
        # the hidden element UPDATE_ENTRY contains the original ID
        data.append((req.form[UPDATE_ENTRY],values))

    for i in range(0,len(data)):
        sql = 'UPDATE ' + table + ' SET '
        id,fields = data[i]
        first = True
        for field,value in fields.items():
            if not first:
                sql += ','
            sql += field + ' = ' + "'" + value + "'" 
            first = False
        sql += ' WHERE ' + idfield + "='" + id + "'"
        sqllist.append(sql)
    try:
        executeSQL(sqllist)
    except psycopg.IntegrityError:
        # assume idfield = the unique field
        if type(unique) is list:
            error = 'There already exists an entry with '
            first = True
            for field in unique:
                if not first:
                    error += ' and '
                error += field + "='" + req.form[field] + "'"
                first = False
        else:
            error = "There already exists an entry with the value '" + \
                    req.form[unique] + "' for the unique field '" + unique + "'"
 
    # Make a list of id's. If error is returned then the original
    # id's are still valid, if not error then id's might have changed
    idlist = []
    if error:
        for i in range(0,len(data)):
            id,fields = data[i]
            idlist.append(id)
    elif staticid:
        # id can't be edited by the user, so the ids are the same as
        # we started with
        for i in range(0,len(data)):
            id,fields = data[i]
            idlist.append(id)
    else:
        if type(req.form[idfield]) is list:
            for i in range(0,len(req.form[idfield])):
                idlist.append(req.form[idfield][i])
        else:
            idlist.append(req.form[idfield])

    return idlist,error

def deleteEntry(selected,table,idfield,where=None):
    if where:
        sql = 'DELETE FROM ' + table + ' WHERE ' + where + ' AND '
    else:
        sql = 'DELETE FROM ' + table + ' WHERE '
    first = True
    for id in selected:
        if not first:
            sql += ' OR '
        sql += idfield + "='" + id + "'"
        first = False
    sqllist = [sql]
    executeSQL(sqllist)
