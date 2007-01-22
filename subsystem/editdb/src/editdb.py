# -*- coding: ISO8859-1 -*-
# $Id$
#
# Copyright 2003, 2004 Norwegian University of Science and Technology
#
# This file is part of Network Administration Visualized (NAV)
#
# NAV is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# NAV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NAV; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Authors: Hans J�rgen Hoel <hansjorg@orakel.ntnu.no>
#

#################################################
## Imports

import editTables,nav.Snmp,sys,re,copy,initBox,forgetSQL,nav.web
from nav.db import manage

from mod_python import util,apache
from editdbSQL import *
from socket import gethostbyaddr,gethostbyname,gaierror
from nav.web.serviceHelper import getCheckers,getDescription
from nav.web.selectTree import selectTree,selectTreeLayoutBox
from nav.web.selectTree import simpleSelect,updateSelect

# Temporary fix:
mod = __import__('encodings.utf_8',globals(),locals(),'*')
mod = __import__('encodings.utf_16_be',globals(),locals(),'*')
mod = __import__('encodings.latin_1',globals(),locals(),'*')
mod = __import__('encodings.utf_16',globals(),locals(),'*')

#################################################
## Templates

from nav.web.templates.editdbTemplate import editdbTemplate

#################################################
## Constants

BASEPATH = '/editdb/'
CONFIGFILE = 'editdb.conf'

EDITPATH = [('Home','/'),('Tools','/toolbox'),('Edit database',BASEPATH)]

ADDNEW_ENTRY = 'addnew_entry'
UPDATE_ENTRY = 'update_entry'
IGNORE_BOX = 'ignore_this_box'

# Bulk import images
BULK_IMG_GREEN = '/images/lys/green.png'
BULK_IMG_YELLOW = '/images/lys/yellow.png'
BULK_IMG_RED = '/images/lys/red.png'

# Bulk import status
BULK_STATUS_OK = 1
BULK_STATUS_YELLOW_ERROR = 2
BULK_STATUS_RED_ERROR = 3
# Bulk fieldname for unspecified fields
BULK_UNSPECIFIED_FIELDNAME = 'excess'

# REQ_TRUE: a required field
# REQ_FALSE: not required
# REQ_NONEMPTY: not required, but don't insert empty field into db
REQ_TRUE = 1
REQ_FALSE = 2
REQ_NONEMPTY = 3

# Fieldtypes
FIELD_STRING = 1
FIELD_INTEGER = 2

#################################################
## Functions

def handler(req):
    ''' mod_python handler '''

    path = req.uri
    match = re.search('editdb/(.+)$',path)
    if match:
        request = match.group(1)
        request = request.split('/')
    else:
        request = ""

    # Read configuration file
    #if not globals().has_key('CONFIG_CACHED'):
    readConfig()
    
    # Get form from request object
    keep_blank_values = True
    fieldStorage = util.FieldStorage(req,keep_blank_values)
    
    form = {}
    for field in fieldStorage.list:
        if form.has_key(field.name):
            # This input name already exists
            if type(form[field.name]) is list:
                # and it's already a list, so just append the
                # the new value
                form[field.name].append(str(field.value))
            else:
                # it's a string, so make a list and append the
                # new value to it
                valueList = []
                valueList.append(form[field.name])
                valueList.append(str(field.value))
                form[field.name] = valueList
        else:
            form[field.name] = str(field.value)

    # Check that all input is in the default encoding (utf8)
    unicodeError = False
    try:
        for key,value in form.items():
            if type(value) is list:
                for field in value:
                    unicode_str = field.decode(DEFAULT_ENCODING)
            else:
                unicode_str = value.decode(DEFAULT_ENCODING)
    except UnicodeError:
        # Some of the input values is not in the default encoding
        unicodeError = True
    
    # Set form in request object
    req.form = form

    output = None
    showHelp = False
    if len(request) == 2:
        if request[0] == 'help':
            showHelp = True
            request = []
            
    if not len(request) > 1:
        output = index(req,showHelp)
    else:        
        table = request[0]
        action = request[1]

        if table == 'bulk':
            output = bulkImport(req,action)
        elif pageList.has_key(table):
            output = editPage(req,pageList[table](),request,unicodeError)

    if output:
        req.content_type = "text/html"
        req.write(output)
        return apache.OK
    else:
        return apache.HTTP_NOT_FOUND

def readConfig():
    ''' Reads configuration from editdb.conf and sets global
        variables. '''
    global CONFIG_CACHED,DEFAULT_ENCODING,BULK_TRY_ENCODINGS,\
           CATEGORY_LIST,SPLIT_LIST,SPLIT_OPPOSITE

    config = nav.config.readConfig(CONFIGFILE)
    CONFIG_CACHED = True
    
    DEFAULT_ENCODING = config['default_encoding']
    BULK_TRY_ENCODINGS = eval(config['bulk_try_encodings'])

    # Make list of cable categories
    catlist = eval(config['categories'])
    categories = []
    for cat in catlist:
        categories.append(eval(config[cat]))
    CATEGORY_LIST = categories

    # Make list of splits and dict of opposite splits
    splitlist = eval(config['splits'])
    splits = []
    opposite = {}
    for splitName in splitlist:
        split = eval(config[splitName])
        # id=0, descr=1, opposite=2
        splits.append((split[0],split[1]))
        if split[2]:
            # References another split, set id
            opposite[split[0]] = eval(config[split[2]])[0]
        else:
            opposite[split[0]] = None
    SPLIT_LIST = splits
    SPLIT_OPPOSITE = opposite

def index(req,showHelp=False,status=None):
    ''' Generates the index page (main menu) '''

    # Empty body
    class body:
        ''' Empty struct for template '''
        def __init__(self):
            pass
    
    body.status = status

    body.title = 'Modify seed information for the NAV database'
    body.infotext = 'Here you can add, delete or edit seed information ' +\
                    'that are needed for the NAV database. Keep in mind ' +\
                    'that most of the data in  the NAV database are ' +\
                    'collected automatically by NAV background processes.'
    body.showHelp = showHelp
    body.help = [BASEPATH + 'help/','Show help']
    body.nohelp = [BASEPATH,'Hide help']
    
    body.tables = []
    headings = []
    
    # Table for boxes and services
    rows = [['IP devices',
             'Input seed information on the IP devices you want to ' +\
             'monitor',
            [BASEPATH + 'netbox/edit','Add'],
            [BASEPATH + 'netbox/list','Edit'],
            [BASEPATH + 'bulk/netbox','Bulk import']],
            ['Services',
             'Which services on which servers do you want to monitor?',
            [BASEPATH + 'service/edit','Add'],
            [BASEPATH + 'service/list','Edit'],
            [BASEPATH + 'bulk/service','Bulk import']]]
    body.tables.append(Table('IP devices and services','',headings,rows))

    # Table for rooms and locations 
    rows = [['Room',
             'Register all wiring closets and server rooms that contain ' +\
             'IP devices which NAV monitors',
            [BASEPATH + 'room/edit','Add'],
            [BASEPATH + 'room/list','Edit'],
            [BASEPATH + 'bulk/room','Bulk import']],
            ['Location',
             'Rooms are organised in locations',
            [BASEPATH + 'location/edit','Add'],
            [BASEPATH + 'location/list','Edit'],
            [BASEPATH + 'bulk/location','Bulk import']]]
    body.tables.append(Table('Rooms and locations','',headings,rows))

    # Table org and usage cat
    rows = [['Organisation',
             'Register all organisational units that are relevant. I.e. ' +\
             'all units that have their own subnet/server facilities.',
            [BASEPATH + 'org/edit','Add'],
            [BASEPATH + 'org/list','Edit'],
            [BASEPATH + 'bulk/org','Bulk import']],
            ['Usage categories',
            'NAV encourages a structure in the subnet structure. ' +\
             'Typically a subnet has users from an organisational ' +\
             'unit. In addition this may be subdivided into a ' +\
             'category of users, i.e. students, employees, ' +\
             'administration etc.',
            [BASEPATH + 'usage/edit','Add'],
            [BASEPATH + 'usage/list','Edit'],
            [BASEPATH + 'bulk/usage','Bulk import']]]
    body.tables.append(Table('Organisation and usage categories','',
                             headings,rows))

    # Table for types, products and vendors
    rows = [['Type',
             'The type describes the type of network device, uniquely ' +\
             'described from the SNMP sysobjectID',
            [BASEPATH + 'type/edit','Add'],
            [BASEPATH + 'type/list','Edit'],
            [BASEPATH + 'bulk/type','Bulk import']],
            ['Product',
             'Similar to type, but with focus on the product number and ' +\
             'description. A product may be a type, it may also be a ' +\
             'component (i.e. module) within an equipment type',
            [BASEPATH + 'product/edit','Add'],
            [BASEPATH + 'product/list','Edit'],
            [BASEPATH + 'bulk/product','Bulk import']],
            ['Vendor',
             'Register the vendors that manufacture equipment that are ' +\
             'represented in your network.',
            [BASEPATH + 'vendor/edit','Add'],
            [BASEPATH + 'vendor/list','Edit'],
            [BASEPATH + 'bulk/vendor','Bulk import']],
            ['Snmpoid',
             'Manually add snmpoids (candidates for the cricket collector)',
            [BASEPATH + 'snmpoid/edit','Add'],
            ['',''],
            ['','']],
            ['Subcategory',
             'The main categories of a device are predefined by NAV (i.e. ' +\
             'GW,SW,SRV). You may however create subcategories yourself.',
            [BASEPATH + 'subcat/edit','Add'],
            [BASEPATH + 'subcat/list','Edit'],
            [BASEPATH + 'bulk/subcat','Bulk import']],
]
    body.tables.append(Table('Types, products and vendors','',headings,rows))

    # Table for vlans and special subnets
    rows = [['Vlan',
             'Register the vlan number that are in use (this info may ' +\
             'also be derived automatically from the routers)',
            None,
            [BASEPATH + 'vlan/list','Edit'],
            None],
            ['Prefix',
             'Register special ip prefixes. Typically reserved prefixes ' +\
             'or prefixes that are not directly connected to monitored ' +\
             'routers/firewalls fall into this category',
            [BASEPATH + 'prefix/edit','Add'],
            [BASEPATH + 'prefix/list','Edit'],
            [BASEPATH + 'bulk/prefix','Bulk import']]]
    body.tables.append(Table('Vlans and special subnets','',headings,rows))

    # Table for cabling and patch
    rows = [['Cabling',
             'Here you may document the horizontal cabling system ',
            [BASEPATH + 'cabling/edit','Add'],
            [BASEPATH + 'cabling/list','Edit'],
            [BASEPATH + 'bulk/cabling','Bulk import']],
            ['Patch',
             'Register the cross connects in the wiring closets ',
            [BASEPATH + 'patch/edit','Add'],
            [BASEPATH + 'patch/list','Edit'],
            [BASEPATH + 'bulk/patch','Bulk import']]]
    body.tables.append(Table('Cabling system','',headings,rows))

    # Table for containers (Network load map)
    rows = [['Container',
             'A container is a collection of routers for the traffic map ',
            [BASEPATH + 'container/edit','Add'],
            [BASEPATH + 'container/list','Edit'],
            None],
            ['Routers In Container',
             'Add or remove routers from containers ',
            [BASEPATH + 'ric/edit','Add'],
            [BASEPATH + 'ric/list','Edit'],
            None]]
    body.tables.append(Table('Traffic Map','',headings,rows))



    nameSpace = {'entryList': None, 'editList': None, 'editForm': None, 'body': body}
    template = editdbTemplate(searchList=[nameSpace])
    template.path = [('Home','/'),
                     ('Tools','/toolbox'),
                     ('Edit database',None)]
    return template.respond()


######################
##
## General functions
##
########################

# General function for handling editing
def editPage(req,page,request,unicodeError):
    ''' General handler function for all editpages. Whenever an action
        add, update, list or delete is performed, this function is called. '''

    # Cancel button redirect
    if req.form.has_key(editForm.cnameCancel):
        nav.web.redirect(req,BASEPATH,seeOther=True)
   
    # Make a status object
    status = editdbStatus()

    # Get action from request (url)
    action = request[1] 

    selected = []
    addedId = None
    # Get editid from url if it is present (external links and list links)
    if len(request) > 1:
        if (len(request) == 3) or (len(request) == 4):
            if request[2]:
                selected = [request[2]]

    # Make a list of selected entries from a posted selectlist
    if req.form.has_key(selectList.cnameChk):
        if type(req.form[selectList.cnameChk]) is str:
            # only one selected
            selected = [req.form[selectList.cnameChk]]
        elif type(req.form[selectList.cnameChk]) is list:
            # more than one selected
            for s in req.form[selectList.cnameChk]:
                selected.append(s)

    # Remember entries which we are already editing
    # Used if editing is interrupted by an error
    if req.form.has_key(UPDATE_ENTRY):
        if type(req.form[UPDATE_ENTRY]) is str:
            # only one selected
            selected = [req.form[UPDATE_ENTRY]]
        elif type(req.form[UPDATE_ENTRY]) is list:
            # more than one selected
            for s in req.form[UPDATE_ENTRY]:
                selected.append(s)

    # Disallow adding (for pageVlan)
    if req.form.has_key(selectList.cnameAdd) and hasattr(page,'disallowAdd'):
        status.errors.append(page.disallowAddReason)
        action = 'list'

    # Check if any entries are selected when action is 'edit' or 'delete'
    if action == 'edit':
        if req.form.has_key(selectList.cnameEdit):
            if not selected:
                status.errors.append('No entries selected for editing')
                action = 'list' 
        elif req.form.has_key(selectList.cnameDelete):
            action = 'delete'
            if not selected:
                status.errors.append('No entries selected')
                action = 'list'
        else:
            if not selected:
                action = 'add'

    # Check for unicode errors in input
    if unicodeError:
        status.errors.append('The data you input was sent in a ' +\
                             'non-recognisible encoding. Make sure your '
                             'browser uses automatic character encoding ' +\
                             'or set it to \'' + str(DEFAULT_ENCODING) + '\'.')
        action = 'list'

    # Set 'current path'
    path = page.pathAdd

    templatebox = page.editbox(page)
    # Copy field defintions from the main templatebox (used by add/update)
    page.fields = templatebox.fields

    # Make form object for template
    outputForm = editForm()
    if hasattr(page,'action'):
        outputForm.action = page.action
    else:
        outputForm.action = page.basePath + 'edit/'

    # List definition, get sorting parameter
    sort = None
    if req.form.has_key('sort'):
        sort = req.form['sort']
    listView = page.listDef(req,page,sort)
   
    # Check if the confirm button has been pressed
    if req.form.has_key(outputForm.cnameConfirm):
        missing = templatebox.hasMissing(req)
        if not missing:
            status = templatebox.verifyFields(req,status)
            if not len(status.errors):
                if req.form.has_key(ADDNEW_ENTRY):
                    # add new entry
                    (status,action,outputForm,addedId) = page.add(req,
                                                            outputForm,action)
                elif req.form.has_key(UPDATE_ENTRY):
                    # update entry
                    (status,action,outputForm,selected) = page.update(req,
                                                                     outputForm,
                                                                      selected)
        else:
            status.errors.append("Required field '" + missing + "' missing") 
    # Confirm delete pressed?
    elif req.form.has_key(selectList.cnameDeleteConfirm):
        status = page.delete(selected,status)
        outputForm = None
        selected = None
        action = 'list' 
    
    # Decide what to show 
    if action == 'predefined':
        # Action is predefined by addNetbox() or updateNetbox()
        outputForm.textConfirm = 'Continue'
        outputForm.status = status
        listView = None
    elif action == 'edit':
        path = page.pathEdit
        title = 'Edit '
        if len(selected) > 1:
            title += page.plural
        else:
            title += page.singular
        outputForm.title = title
        outputForm.status = status
        outputForm.textConfirm = 'Update'
        if page.editMultipleAllowed:
            # This page can edit multiple entries at a time
            for s in selected:
                outputForm.add(page.editbox(page,req,s,formData=req.form))
        else:
            # This page can only edit one entry at a time (eg. netbox)
            outputForm.add(page.editbox(page,req,selected[0],formData=req.form))
        # preserve path
        #outputForm.action = page.basePath + 'edit/' + selected[0]
        listView = None
    elif action == 'add':
        path = page.pathAdd
        outputForm.status = status
        outputForm.title = 'Add ' + page.singular
        outputForm.textConfirm = 'Add ' + page.singular
        outputForm.add(page.editbox(page,req,formData=req.form))
        listView = None
    elif action == 'delete':
        path = page.pathDelete
        listView = page.listDef(req,page,sort,selected)
        listView.status = status
        listView.fill(req)
        outputForm = None
    elif action == 'list':
        if addedId:
            listView.selectedId = addedId
        if selected:
            listView.selectedId = selected[0]
        path = page.pathList
        listView.status=status
        listView.fill(req)
        outputForm = None
    elif action == 'redirect':
        # Redirect to main page (snmpoid add)
        return index(req,status=status)

    nameSpace = {'entryList': listView,'editList': None,'editForm': outputForm}
    template = editdbTemplate(searchList=[nameSpace])
    template.path = path
    return template.respond()

def insertNetbox(ip,sysname,catid,roomid,orgid,
                 ro,rw,deviceid,serial,
                 typeid,snmpversion,subcatlist=None,
                 function=None):
    ''' Inserts a netbox into the database. Used by pageNetbox.add(). '''
    if not deviceid:

        # Make new device first
        if len(serial):
            fields = {'serial': serial}
        else:
            # Don't insert an empty serialnumber (as serialnumbers must be
            # unique in the database) (ie. don't insert '' for serial)
            fields = {}
            
        deviceid = addEntryFields(fields,
                                  'device',
                                  ('deviceid','device_deviceid_seq'))

    fields = {'ip': ip,
              'roomid': roomid,
              'deviceid': deviceid,
              'sysname': sysname,
              'catid': catid,
              'orgid': orgid,
              'ro': ro,
              'rw': rw}
    #uptodate = false per default

    # Get prefixid
    query = "SELECT prefixid FROM prefix WHERE '%s'::inet << netaddr" \
            % (fields['ip'],)
    try:
        result = executeSQLreturn(query) 
        fields['prefixid'] = str(result[0][0])
    except:
        pass        

    if typeid:
        fields['typeid'] = typeid

        # Set uptyodate = false
        # This part is done in netbox now. And for a new box this
        # field defaults to 'f'
        #tifields = {'uptodate': 'f'}
        #updateEntryFields(tifields,'type','typeid',typeid)

    if snmpversion:
        # Only use the first char from initbox, can't insert eg. '2c' in
        # this field
        snmpversion = snmpversion[0]
        fields['snmp_version'] = snmpversion

    netboxid = addEntryFields(fields,
                              'netbox',
                              ('netboxid','netbox_netboxid_seq'))
    # If subcatlist and function is given, insert them
    if subcatlist:
        if type(subcatlist) is list:
            for sc in subcatlist:
                fields = {'netboxid': netboxid,
                          'category': sc}
                addEntryFields(fields,'netboxcategory')
        else:
            fields = {'netboxid': netboxid,
                      'category': subcatlist}
            addEntryFields(fields,'netboxcategory')

    if function:
        fields = {'netboxid': netboxid,
                  'key': '',
                  'var': 'function',
                  'val': function}
        addEntryFields(fields,'netboxinfo')


######################
##
## General classes
##
########################

class Table:
    ''' A general class for html tables used by index(). '''
    def __init__(self,title,infotext,headings,rows):
        self.title = title
        self.infotext = infotext
        self.headings = headings
        self.rows = rows

class editdbStatus:
    ''' Struct class which holds two lists (messages and errors). Every 
        form object got an instance of this class and uses it to add 
        messages and errors which is then displayed by the template. '''
    # List of status messages, one line per message
    messages = []
    # List of error messages, one line per message
    errors = []

    def __init__(self):
        self.messages = []
        self.errors = []


class entryListCell:
    ''' Represents a cell (TD) in a selectlist object. '''

    CHECKBOX = 'chk'
    RADIO = 'rad'
    HIDDEN = 'hid'

    def __init__(self,text=None,url=None,buttonType=None,
                 image=None,tooltip=None):
        self.text = text
        self.url = url
        self.buttonType = buttonType
        self.image = image
        self.tooltip = tooltip

## class entryList (rename to selectList)
class entryList:
    ''' Flexible class for making lists of entries which can be selected.
        Used by all 'edit' pages. 
        
        Uses the list definitions defined in every page class.

        descriptionFormat = [(text,forgetSQLfield),(text,...] '''
        
    # Constants
    CNAME_SELECT = 'checkbox_id'
    CNAME_ADD = 'submit_add'
    CNAME_EDIT = 'submit_edit'
    CNAME_DELETE = 'submit_delete'
    CNAME_CONFIRM_DELETE = 'confirm_delete'
    
    # Class variables used by the template
    title = None
    status = None
    body = None
    formMethod = 'post'
    formAction = None
    selectCname = CNAME_SELECT
    buttonsTop = [(CNAME_ADD,'Add new'),
                  (CNAME_EDIT,'Edit selected'),
                  (CNAME_DELETE,'Delete selected')]
    buttonsBottom = buttonsTop
    hideFirstHeading = False  # Don't show first column heading (usually 
                              # the select heading) if True
    buttonTypeOverride = None # override the chosen select button type
                              # used for bulk and delete lists where there
                              # is no checkbox/radiobut., only hidden
    headings = []             # list of cell objects
    rows = []                 # tuples of (sortstring,id,cell object)

    # Variables for filling the list
    tableName = None
    basePath = None                 
    sortBy = None                   # Sort by columnumber
    defaultSortBy = None            # Default columnnumber sorted by
    headingDefinition = None        # list of tuples (heading,show sort link)
    cellDefintion = None            # cellDefinition list
    where = None                    # List of id's (strings)
    sortingOn = True                # Show links for sorting the list

    # SQL filters
    filters = None
    filterConfirm = 'cn_filter'
    filterConfirmText = 'Update list'
    selectedId = None

    def __init__(self,req,struct,sort,deleteWhere=None):
        self.headings = []
        self.rows = []

        if sort:
            sort = int(sort)
        self.sortBy = sort
        self.tableName = struct.tableName
        self.tableIdKey = struct.tableIdKey
        self.basePath = struct.basePath
        self.deleteWhere = deleteWhere
        self.formAction = self.basePath + 'edit/'
        self.filterAction = self.basePath + 'list/'

        if deleteWhere:
            self.buttonTypeOverride = entryListCell.HIDDEN
            self.hideFirstHeading = True
            self.where = deleteWhere
            title = 'Are you sure you want to delete the ' + \
                    'selected '
            if len(deleteWhere) > 1:
                title += struct.plural
            else:
                title += struct.singular
            self.title = title + '?'
            self.sortingOn = False
            self.buttonsTop = None
            self.buttonsBottom = [(self.CNAME_CONFIRM_DELETE,'Delete')]
        else:
            self.title = 'Edit ' + struct.plural
            self.sortingOn = True

    def fill(self,req):
        """ Fill the list with data from the database. """
        
        # No filters if this is a delete list
        if self.deleteWhere:
            self.filters = None
        # Make filters
        if self.filters:
            self.makeFilters(req)

        # Make headings
        i = 0
        for heading,sortlink,sortFunction in self.headingDefinition:
            if self.hideFirstHeading:
                heading = ''
                self.hideFirstHeading = False
            if self.sortBy:
                currentOrder = self.sortBy
            else:
                currentOrder = self.defaultSortBy
            s = i
            if i == currentOrder:
                # Reverse sort?
                s = -i
            url = self.basePath + 'list/?sort=' + str(s)
            if sortlink and self.sortingOn:
                self.headings.append(entryListCell(heading,
                                                    url))
            else:
                self.headings.append(entryListCell(heading,
                                                    None))
            i = i + 1

        # Check filters and decide if we're going to show list
        renderList = True
        filterSettings = []
        if self.filters:
            renderList = False
            for filter in self.filters:
                # filter[10] is selected id in filter
                if filter[10]:
                    # Something is selected, show list
                    renderList = True
                    # filter[6] is tableIdKey
                    filterSettings.append((filter[10],filter[6]))

        # Skip filling if no result from filter
        if renderList:
            # Preparse tooltips, etc.
            for sqlQuery,definition in self.cellDefinition:
                for column in definition:
                    for cell in column:
                        if type(cell) is list:
                            # This cell definition is a list, as opposed to
                            # a tuple, so we must prefetch some data for the
                            # parse function
                            # Must prefetch data for this column
                            for tooltipDef in cell:
                                # There can be one or more defintions per cell
                                sql = tooltipDef[0]
                                # column[2] is reserved for data
                                tooltipDef[2] = executeSQLreturn(sql)

            # Make rows
            reverseSort = False
            if self.sortBy:
                if self.sortBy < 0:
                    self.sortBy = self.sortBy * -1
                    reverseSort = True

            for sqlTuple,definition in self.cellDefinition:
                # Create SQL query from tuple
                columns,tablenames,join,where,orderBy = sqlTuple
                sqlQuery = 'SELECT ' + columns + ' FROM ' + tablenames
                if join:
                    sqlQuery += ' %s ' % (join,)
                if where:
                    sqlQuery += ' WHERE ' + where
                # Add where clause if self.where is present
                if self.where:
                    if not where:
                        # No where defined in sqlTuple, so add it now
                        sqlQuery += ' WHERE '
                    else:
                        # Else, these are additional so add AND
                        sqlQuery += ' AND '
                    first = True
                    sqlQuery += ' ('
                    for id in self.where:
                        if not first:
                            sqlQuery += 'OR'
                        sqlQuery += " %s.%s='%s' " % (self.tableName,
                                                      self.tableIdKey,id)
                        if first:
                            first = False
                    sqlQuery += ') '
                # Add where clause if filterSettings is present
                for filter in filterSettings:
                    if not where:
                        # No where defined in sqlTuple, so add it now
                        sqlQuery += ' WHERE '
                    else:
                        # Else, these are additional so add AND
                        sqlQuery += ' AND '
                    sqlQuery += filter[1] + "='" + filter[0] + "' "
                if orderBy:
                    sqlQuery += ' ORDER BY ' + orderBy                                
                fetched = executeSQLreturn(sqlQuery)
                for row in fetched:
                    id = row[0]
                    cells = []
                    for text,url,buttonType,image,tooltip in definition:
                        if buttonType and self.buttonTypeOverride:
                            buttonType = self.buttonTypeOverride
                        cells.append(entryListCell(self.parse(text,row),
                                                   self.parse(url,row,True),
                                                   buttonType,
                                                   image,
                                                   self.parse(tooltip,row))) 
                    
                    sortKey = None
                    if self.sortBy:
                        sortKey = row[self.sortBy]
                    self.rows.append([sortKey,(id,cells)])
            if self.sortBy:
                if self.headingDefinition[self.sortBy][2]:
                    # Optional compare method
                    self.rows.sort(self.headingDefinition[self.sortBy][2])
                else:
                    self.rows.sort()
                if reverseSort:
                    self.rows.reverse()

    def parse(self,parseString,currentRow,url=False):
        """ Parses format strings used by the list definitions. """
        result = None
        if type(parseString) is int:
            # parseString refers to integer column
            result = [currentRow[parseString]]
        elif type(parseString) is str:
            parseString = parseString.replace('{p}',self.basePath)
            parseString = parseString.replace('{id}',str(currentRow[0]))
            parseString = parseString.replace('{descr}',str(currentRow[1]))
            if parseString.find('SELECT') == 0:
                # This string is a sql query (used by vlan)
                resultString = ''
                sqlresult = executeSQLreturn(parseString)
                for row in sqlresult:
                    for col in row:
                        resultString += col + '<br>'
                result = [resultString]    
            else:
                if url:
                    result = parseString
                else:
                    result = [parseString]
        elif type(parseString) is list:
            result = []
            for tooltipDef in parseString:
                data = tooltipDef[2]
                if data:
                    # There is preparsed data (ie. the sql returned something)
                    result.append(tooltipDef[1][0])
                    # [1][0] = Tooltip (can also be other preparsed data) header
                    for row in data:
                        if currentRow[0] == row[0]:
                            # ID's match
                            result.append(row[1])
        return result        

    def makeFilters(self,req):
        for filter in self.filters:
            text,firstEntry,sqlTuple,idFormat,optionFormat,\
            controlName,tableId,table,fields = filter
           
            optionsList = []
            if firstEntry:
                firstEntry = ([firstEntry[0]],[firstEntry[1]])
                optionsList.append(firstEntry)
            # Make sql
            sql = "SELECT " + sqlTuple[0] + " FROM " + sqlTuple[1] + " "
            if sqlTuple[2]:
                sql += sqlTuple[2] + " "
            if sqlTuple[3]:
                sql += "WHERE " + sqlTuple[3] + " "
            if sqlTuple[4]:
                sql += "ORDER BY " + sqlTuple[4]
            result = executeSQLreturn(sql)
            for row in result:
                id = self.parse(idFormat,row)
                text = self.parse(optionFormat,row)
                optionsList.append((id,text))
            filter.append(optionsList)
            # Selected id
            selected = None
            if self.selectedId:
                entry = table(self.selectedId)
                fieldList = fields.split('.')
                for field in fieldList:
                    entry = getattr(entry,field)
                selected = str(entry) 
            if req.form.has_key(controlName):
                if len(req.form[controlName]):
                    selected = req.form[controlName]
            filter.append(selected)

# Class representing a form, used by the template
class editForm:
    """ Class representing a form element, the main component of every
        edit page. Each form element can have any number of editbox
        objects added to it. """
    
    # For the template
    method = 'post'
    action = None
    title = None
    error = None
    status = None
    backlink = None
    enctype = 'application/x-www-form-urlencoded'

    # Text and controlname
    textConfirm = None
    cnameConfirm = 'form_confirm'
    showConfirm = True

    textCancel = 'Cancel'
    cnameCancel = 'form_cancel'
    showCancel = True
    actionCancel = BASEPATH

    # Only used for netboxes (see template)
    # 'submit_delete' is fetched by the same handler as when deleting multiple
    # entities from a list
    textDelete = 'Delete'
    cnameDelete = 'submit_delete'
    showDelete = True

    # Used by edit netbox in the intermediate
    CNAME_CONTINUE = 'cname_continue'

    # List of editboxes to display
    editboxes = []

    def __init__(self,cnameConfirm=None):
        if cnameConfirm:
            self.cnameConfirm = cnameConfirm
 
        self.editboxes = []

    def add(self,box):
        """ Add an editbox object to this form element. """
        self.editboxes.append(box)

class inputText:
    """ Class representing a textinput html control. """

    type = 'text'
    name = None
    maxlength = None
    
    def __init__(self,value='',size=22,maxlength=None,disabled=False):
        self.value = value
        self.disabled = disabled
        self.size = str(size)
        if maxlength:
            self.maxlength = str(maxlength)

class inputTreeSelect:
    """ Container class for treeselects. Used to get treeselect in the 
        same format as all the other inputs used by the template. """

    type = 'treeselect'
    name = None
    treeselect = None
    disabled = False

    def __init__(self,treeselect):
        self.value = ''
        self.treeselect = treeselect

class inputSelect:
    """ Class representing a select input html control. """

    type = 'select'
    name = None
    
    def __init__(self,options=None,table=None,attribs=None,disabled=False):
        self.value = ''
        self.options = options
        self.attribs = attribs
        self.disabled = disabled

        if table:
            self.options = table.getOptions() 

class inputMultipleSelect:
    """ Class representing a multiple select input html control. """
    type = 'multipleselect'
    name = None
    value = []
    def __init__(self,options=None,table=None,disabled=False):
        self.options = options
        self.disabled = disabled

        if table:
            self.options = table.getOptions() 

class inputFile:
    """ Class representing a file upload input control. """

    type = 'file'
    name = None
    value = ''
    disabled = False
    def __init__(self):
        pass

class inputTextArea:
    """ Class representing a textarea input html control. """

    type = 'textarea'
    name = None

    def __init__(self,rows=20,cols=80):
        self.rows = rows
        self.cols = cols
        self.value = ''
        self.disabled = False

class inputCheckbox:
    """ Class representing a checkbox input html control. """

    type = 'checkbox'
    name = None

    def __init__(self,disabled=False):
        self.value = '0'
        self.disabled = disabled

class inputHidden:
    """ Class representing a hidden input html control. """
    type = 'hidden'
    name = None
    disabled = False

    def __init__(self,value):
        self.value = value


class inputServiceProperties:
    """ Contains a list of inputServiceProperty inputs. 
        (used by pageService) """

    type = 'serviceproperties'
    disabled = False
    
    def __init__(self,propertyList):
        self.propertyList = propertyList

class inputServiceProperty:
    """ Class representing a serviceproperty input box. 
        (used by pageService) """

    type = 'serviceproperty'
    disabled = False

    def __init__(self,title,id,args,optargs,display=True):
        self.title = title
        self.id = id
        self.display = display
        self.args = args
        self.optargs = optargs

class editbox:
    """ Parent class for all the different editboxes which are all added 
        to an editform object. There are normally one editbox per page, but
        for some pages there are more (there are created three editboxes for
        the netbox page for example, editbox(main),editboxserial and
        editboxfunction (which also includes the subcat)). 
        
        The editbox contains field defitions used by the template to render
        the forms and functions to fill the form with data from either the
        database or from a previous http post. """

    boxName = ADDNEW_ENTRY
    boxId = 0

    # Current box number keeps track of the box number when there are
    # more than one editbox in a form. Used by formFill to get correct data
    #currentBoxNumber = 0

    def fill(self):
        """ Fill this form with data from the database (entry = editId). """
        entry = self.table(self.editId)
       
        # Set the name of this box to reflect that we are
        # updating an entry
        self.boxName = UPDATE_ENTRY
        self.boxId = self.editId

        ## TEMPORARY:
        ## check if this is one of the new pages by checking
        ## for three instead of two entries in the desc list
        if len(self.fields[self.fields.keys()[0]]) > 2:
            # Uses psycopg to fill field values
            page = pageList[self.page]

            select = ''
            first = True
            keyNumber = {}
            i = 0
            for key in self.fields.keys():
                keyNumber[key] = i
                i+=1
                if not first:
                    select += ', '
                select += key
                first = False
            tables = page.tableName
            where = page.tableIdKey + "='" + self.editId + "'"
            # For the benefit of pagePrefix (which must select from vlan too)
            if hasattr(self,'additionalSQL'):
                tables += ', vlan'
                where += self.additionalSQL

            sql = "SELECT %s FROM %s WHERE %s" % (select, tables, where)

            result = executeSQLreturn(sql)
            result = result[0]

            for key,desc in self.fields.items():
                value = result[keyNumber[key]]
                if value:
                    desc[0].value = str(value)
        else:
            # Old style filling with forgetsql
            for fieldname,desc in self.fields.items():
                value = getattr(entry,fieldname)
                if value:
                    desc[0].value = str(value)

    def setControlNames(self,controlList=None):
        """ Set controlnames for the inputs to the same as the fieldnames. """
        if not controlList:
            controlList = self.fields

        for fieldname,desc in controlList.items():
            desc[0].name = fieldname

    def verifyFields(self,req,status):
        """ Verify that data entered into fields are of correct type.
            Eg. integers in FIELD_INTEGER fields. """

        for field,desc in self.fields.items():
            if req.form.has_key(field):
                if type(req.form[field]) is list:
                    # Editing several entries
                    for each in req.form[field]:
                        # Do tests here
                        if desc[3] == FIELD_INTEGER:
                            if len(each):
                                try:
                                    int(each)
                                except ValueError:
                                    error = "Invalid integer: '" +\
                                            str(each) + "'"
                                    status.errors.append(error)
                else:
                    # Editing only one field
                    # Do tests here
                    if desc[3] == FIELD_INTEGER:
                        try:
                            if len(req.form[field]):
                                int(req.form[field])
                        except ValueError:
                            error = "Invalid integer: '" + \
                                    str(req.form[field]) + "'"
                            status.errors.append(error)
        return status

    def hasMissing(self,req):
        """ Check if any of the required fields are missing in the req.form
            Returns the name the first missing field, or False
            
            Note: keep_blank_values (mod_python) must be True or empty fields 
                  won't be present in the form  """
        missing = False
        for field,desc in self.fields.items():
            # Keep blank values must be switched on, or else the next line
            # will fail, could be more robust
            if req.form.has_key(field):
                if type(req.form[field]) is list:
                    # the field is a list, several entries have been edited
                    for each in req.form[field]:
                        if desc[1] == REQ_TRUE:
                            # this field is required
                            if not len(each):
                                if len(desc) > 2:
                                    # desc[2] is real fieldname
                                    missing = desc[2]
                                else:
                                    # cryptic fieldname (remove this later)
                                    missing = field
                                break
                else:
                    if desc[1] == REQ_TRUE:
                        # tihs field is required
                        if not len(req.form[field]):
                            if len(desc) > 2:
                                # desc[2] is real fieldname
                                missing = desc[2]
                            else:
                                # cryptic fieldname (remove this later)
                                missing = field
                            break
        return missing

    def addHidden(self,fieldname,value):
        """ Add hidden html input control to the editbox. """
        self.hiddenFields[fieldname] = [inputHidden(value),False]
        self.hiddenFields[fieldname][0].name = fieldname

    def addDisabled(self):
        """ Since fields which are disabled, aren't posted (stupid HTML)
            we must add them as hidden fields.
           
            This only goes for textinputs (?!) so we must also change
            controlnames to avoid getting double values for selects, etc. """

        for fieldname,definition in self.fields.items():
            if definition[0].disabled and (not definition[0].type=='hidden'):
                self.addHidden(fieldname,definition[0].value)
                definition[0].name = definition[0].name + '_disabled'

    def formFill(self,formData):
        """ Fill this editbox with data from the form.

            This is used by intermediate steps (like register serial)
            to remember field values and for refilling a form if an error
            is encountered and the user has to resubmit a form. """

        if not hasattr(editbox,'currentBoxNumber'):
            editbox.currentBoxNumber = 0

        for field,definition in self.fields.items():
            first = True
            numberOfBoxes = None
            if formData.has_key(field):
                if type(formData[field]) is list:
                    # Remember how many editboxes this form has
                    if first:
                        # NB! ASSUMES THAT THE FIRST FIELDNAME IN A FORM
                        # IS NEVER A CHECKBOX (SINCE UNCHECKED CHECCKBOXES
                        # ARE NOT POSTED). IF IT IS, THEN numberOfBoxes
                        # WILL BE ONE LESS THAN IT SHOULD BE FOR EACH
                        # UNCHECKED CHECKBOX
                        numberOfBoxes = len(formData[field])                    
                        first = False

                    # We are editing more than one entry, pick the
                    # right data from the form
                    definition[0].value = formData[field][editbox.currentBoxNumber]
                else:
                    definition[0].value = formData[field]
        # Update class variable currentFormNumber
        if numberOfBoxes:
            editbox.currentBoxNumber +=1
            if editbox.currentBoxNumber == numberOfBoxes:
                # Reset the currentFormNumber class instance
                # Since it is a class instance, it will be common
                # to all editbox instances for all requests, that's
                # why it has to be reset
                editbox.currentBoxNumber = 0

class editboxHiddenOrMessage(editbox):
    """ This editbox can display a message and contain hidden inputs. """
    page = 'hiddenormessage'

    def __init__(self,message=None):
        self.hiddenFields = {}
        self.message = message

        # The editboxNetbox has UPDATE_ENTRY (which holds the id) or ADDNEW, 
        # don't need to repeat it here (so setting boxname to IGNORE_BOX) 
        self.boxName = IGNORE_BOX


class editdbPage:
    """ The main editing class. Every edit page inherits from this class.

        Contains functions for adding, updating and describing entries.
        Default functions can be overriden by children to do more specific
        handling of adding or updating.

        The children of this class contains all the information needed
        for handling the different tables.

         class editdbPage
                 |+-- class listDef
                 |+-- class editbox
                 |+-- (optionally more editboxes)
        
                 |+-- def add
                 |+-- def update
                 |+-- def delete
                 |+-- def describe
    """


    def add(self,req,outputForm,action):
        """ Called when 'Add' is clicked on an edit page.

            Takes the formdata from the request object and inserts
            an entry in the database.

            This is the general function used by almost all the edit
            pages. Some of the edit page classes overrides this function
            for more control over the adding (eg. the netbox page).

            req: request object containing a form
            outputForm: form with editboxes
                        manipulated directly by eg. editNetbox.add() """

        error = None
        status = editdbStatus()

        # Get database connection
        connection = nav.db.getConnection('editdb','manage')
        database = connection.cursor()
       
        id = None
        nextId = None 
        if self.sequence:
            # Get next id from sequence, will need this id to reload
            # entry when making a description of the inserted row
            # In the case that sequence=None, idfield is already
            # present in the field data
            sql = "SELECT nextval('%s')" % (self.sequence,)
            database.execute(sql)
            result = database.fetchall()
            nextId = str(result[0][0])

        sql = 'INSERT INTO ' + self.tableName + ' ('
        first = True
        for field,descr in self.fields.items():
            if req.form.has_key(field):
                if len(req.form[field]):
                    if not first:
                        sql += ','
                    sql += field
                    first = False
        # Add the idfield if we have queried the sequence
        if nextId:
            sql += "," + self.tableIdKey
        sql += ') VALUES ('
        first = True
        for field,descr in self.fields.items():
            if req.form.has_key(field):
                if len(req.form[field]):    
                    if not first:
                        sql += ','
                    sql += "'" + req.form[field] + "'"
                    first = False
        # Add the id value if we have queried the sequence
        if nextId:
            sql += ",'" + nextId + "'"
        sql += ')'
        try:
            database.execute(sql)
            connection.commit()
        except (psycopg.IntegrityError,psycopg.ProgrammingError),e:
            # Earlier versions of psycopg always returned IntegrityError
            if type(self.unique) is list:
                error = 'There already exists an entry with '
                first = True
                for field in self.unique:
                    if not first:
                        error += ' and '
                    error += field + "='" + req.form[field] + "'"
                    first = False
            else:
                error = "There already exists an entry with the value '" + \
                        req.form[self.unique] + "' for the unique field '" +\
                        self.unique + "'"
        if error:
            status.errors.append(error)
        else:
            if self.sequence:
                id = nextId
            else:
                id = req.form[self.tableIdKey]
            entry = self.table(id)
            message = 'Added ' + self.singular + ': ' + self.describe(entry)
            status.messages.append(message)
            action = 'list'
        return (status,action,outputForm,id)

      
    def update(self,req,outputForm,selected):
        """ Updates one or more entries in the database. Takes data
            from form in request object. Overriden by some subclasses 
            such as pageNetbox. """

        status = editdbStatus()
        sqllist = []
        data = []
        error = None
     
        # Get the name of one of the fields that should be present
        presentfield = self.fields.keys()[0]

        # Use this field to check if there are multiple
        # editboxes (multiple entries edited)
        if type(req.form[presentfield]) is list:
            for i in range(0,len(req.form[presentfield])):
                values = {}
                for field,descr in self.fields.items():
                    # Special case: checkboxes are not posted if
                    # they are not selected. Check if the field
                    # is present with "req.form[field][i] and
                    # catch the indexError exception if it's not
                    # present.
                    try:
                        req.form[field][i]
                        # Don't insert empty strings into fields
                        # where required = REQ_NONEMPTY
                        if len(req.form[field][i]):
                            values[field] = req.form[field][i]
                        else:
                            if descr[1] != REQ_NONEMPTY:
                                values[field] = req.form[field][i]
                            else:
                                # Insert NULL instead
                                values[field] = None
                    except (KeyError,IndexError):
                        # Field not present (ie. unchecked checkbox)
                        # Insert NULL
                        values[field] = None
                # The hidden element UPDATE_ENTRY contains the original ID
                data.append((req.form[UPDATE_ENTRY][i],values))
        else:
            values = {}
            for field,descr in self.fields.items():
                try:
                    req.form[field]
                    if len(req.form[field]):
                        values[field] = req.form[field]
                    else:
                        # Don't insert empty strings into fields
                        # where required = REQ_NONEMPTY
                        if descr[1] != REQ_NONEMPTY:
                            values[field] = req.form[field]
                        else:
                            # Insert NULL instead
                            values[field] = None
                except KeyError:
                    # Field not present (ie. ie unchecked checkbox)
                    values[field] = None
            # The hidden element UPDATE_ENTRY contains the original ID
            data.append((req.form[UPDATE_ENTRY],values))

        for i in range(0,len(data)):
            sql = 'UPDATE ' + self.tableName + ' SET '
            id,fields = data[i]
            first = True
            for field,value in fields.items():
                if not first:
                    sql += ','
                if value:
                    sql += field + "='" + value + "'" 
                else:
                    sql += field + '=NULL'
                first = False
            sql += ' WHERE ' + self.tableIdKey + "='" + id + "'"
            try:
                executeSQL([sql])
            except psycopg.IntegrityError:
                # Assumes tableIdKey = the unique field
                if type(self.unique) is list:
                    error = 'There already exists an entry with '
                    first = True
                    for field in self.unique:
                        if not first:
                            error += ' and '
                        error += field + "='" + req.form[field][i] + "'"
                        first = False
                    status.errors.append(error)
                else:
                    error = "There already exists an entry with the value '" + \
                            req.form[self.unique][i] + \
                            "' for the unique field '" + self.unique + "'"
                    status.errors.append(error)
         
        # Make a list of id's. If error is returned then the original
        # id's are still valid, if-not error then id's might have changed
        idlist = []
        if error:
            for i in range(0,len(data)):
                id,fields = data[i]
                idlist.append(id)
        elif not self.editIdAllowed:
            # Id can't be edited by the user, so the ids are the same as
            # we started with
            for i in range(0,len(data)):
                id,fields = data[i]
                idlist.append(id)
        else:
            if type(req.form[self.tableIdKey]) is list:
                for i in range(0,len(req.form[self.tableIdKey])):
                    idlist.append(req.form[self.tableIdKey][i])
            else:
                idlist.append(req.form[self.tableIdKey])

        action = 'list'
        if error:
            action = 'edit'
        else:
            # All entries updated without error, make list to displayed
            # in the status header
            for entry in idlist:
                message = "Updated " + self.singular + ": "
                message += self.describe(entry)
                status.messages.append(message)

        return (status,action,outputForm,selected)
 
    def describe(self,id):
        """ Gives a textual description of a database entry.
            Used when adding, deleting and updating entries to tell the user
            exactly what entries were altered (useful when the id field 
            of the table only contains a numerical key).

            If the edit page class contains a descriptionFormat it 
            is used. Otherwise it falls back to using the id field
            passed to the function.

            Remember to only use NOT NULL fields when writing descrFormats
            to avoid malformed descriptions. """
 
        description = ''
        
        try:
            entry = self.table(id)
  
            if hasattr(self,'descriptionFormat'):
                # Use the description format for this page to make a
                # nicely formatted description of a database entry
                for part in self.descriptionFormat:
                    (string,field) = part
                    fieldData = ''
                    if field:
                        # Get data from a db field
                        field = field.split('.')
            
                        if len(field) > 1:
                            tempentry = entry
                            i=0
                            for f in field:
                                #if i==1:
                                #    raise(repr(tempentry)+':'+f)
                                i+=1
                                tempentry = getattr(tempentry,f)
                                if type(tempentry) is str:
                                    # Got the field we're after
                                    break
                            fieldData = tempentry
                        else:
                            fieldData = getattr(entry,field[0])

                    description += string + str(fieldData)
            else:
                # Vanilla description (only the id field)
                description = "'" + id +"'" 
        except forgetSQL.NotFound:
            # No such id in this table
            pass
        return description

    def delete(self,idList,status):
        for id in idList:
            try:
                deletedName = self.describe(id)
                deleteEntry([id],self.tableName,self.tableIdKey)
                status.messages.append("Deleted %s: %s" % \
                                           (self.singular,deletedName))
            except psycopg.IntegrityError:
                # Got integrity error while deleting, must check what
                # dependencies are blocking.  But firstly, we roll back the
                # failed transaction.
                rollbackSQL()

                error = "Error while deleting %s '%s': " % (self.singular,
                                                            deletedName)
                errorState = False
                for (table,other,key,url) in self.dependencies:
                    where = "%s='%s'" % (key,str(id))
                    if table.getAll(where):
                        errorState = True
                        # UGLY.. HTML
                        error += "referenced in "  + \
                                 "one or more %s " % (other,) + \
                                 "<a href=\"%s%s\">" % (url,id) + \
                                 "(view report)</a>." 
                        break
                if not errorState:
                    # There are no dependencies or couldn't find reference.
                    # Give general error
                    error += '%s is referenced in another table' % (self.name,)
                status.errors.append(error) 
        return status

        
class pageCabling(editdbPage):
    """ Describes editing of the cabling table. """
    
    basePath = BASEPATH + 'cabling/'
    table = nav.db.manage.Cabling
    pageName = 'cabling'
    tableName = 'cabling'
    tableIdKey = 'cablingid'
    sequence = 'cabling_cablingid_seq'
    editMultipleAllowed = True
    editIdAllowed = False

    # Unique fields (for errormessages from add/update)
    unique = ['roomid','jack']

    # Nouns
    singular = 'cabling'
    plural = 'cablings'

    # Delete dependencies
    dependencies = [(nav.db.manage.Patch,
                     'patches',
                     'cablingid',
                     '/report/netbox/?roomid=')]

    # Description format used by describe(id)
    # Example: room 021 (descr) to jack 123, building, office
    descriptionFormat = [('\'jack ','jack'),
                         (', ','targetroom'),
                         (', ','building'),
                         ('\' to room \'','room.roomid'),
                         (', ','room.location.locationid'),
                         ('\'',None)]

    pathAdd = EDITPATH + [('Cabling',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Cabling',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Cabling',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Cabling',False)]

    class listDef(entryList):
        """ Describes the format of the list view of cablings. """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # List filters
            self.filters = [['Show cablings in room ',
                            ('','Select a room'),
                            ('roomid,descr',
                             'room',
                             None,
                             '((SELECT count(*) FROM cabling WHERE ' +\
                             'cabling.roomid=room.roomid) > 0)',
                             'room.roomid'),
                             '{id}',
                             '{id} ({descr})',
                             'flt_room',
                             'roomid',
                             nav.db.manage.Cabling,
                             'room.roomid']]

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Room',True,None),
                                      ('Jack',True,None),
                                      ('Building',True,None),
                                      ('Target room',True,None),
                                      ('Category',True,None),
                                      ('Description',True,None)]

            self.cellDefinition = [(('cablingid,roomid,jack,' + \
                                     'building,targetroom,category,descr',
                                     'cabling',
                                     None,
                                     None,
                                     'roomid,jack'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None),
                                     (3,None,None,None,None),
                                     (4,None,None,None,None),
                                     (5,None,None,None,None),
                                     (6,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing cabling entries.
            The template uses this field information to draw the form. """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            self.hiddenFields = {}
            if editId:
                # Preserve the selected id
                self.addHidden(selectList.cnameChk,editId)
                self.editId = editId
     
            r = [(None,'Select a room')]
            for room in nav.db.manage.Room.getAllIterator(orderBy='roomid'):
                loc = nav.db.manage.Location(room.location).descr
                r.append((room.roomid,room.roomid + ' (' + loc + ':' + \
                          str(room.descr) + ')'))

            # Field definitions {field name: [input object, required]}
            f = {'roomid': [inputSelect(options=r),REQ_TRUE,'Room',
                            FIELD_STRING],
                 'jack': [inputText(),REQ_TRUE,'Jack',FIELD_STRING],
                 'building': [inputText(),REQ_TRUE,'Building',FIELD_STRING],
                 'targetroom': [inputText(),REQ_TRUE,'Target room',
                                FIELD_STRING],
                 'descr': [inputText(),REQ_FALSE,'Description',FIELD_STRING],
                 'category': [inputSelect(options=CATEGORY_LIST),REQ_TRUE,
                              'Category',FIELD_STRING]}

            self.fields = f
            self.setControlNames()

            # This box is for editing existing with id = editId
            if editId:
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData)

class pageContainer(editdbPage):
    """ Describes editing of containers (vp_netbox_grp_info). """
    
    basePath = BASEPATH + 'container/'
    table = nav.db.manage.Vp_netbox_grp_info
    pageName = 'container'
    tableName = 'vp_netbox_grp_info'
    tableIdKey = 'vp_netbox_grp_infoid'
    sequence = 'vp_netbox_grp_info_vp_netbox_grp_infoid_seq'
    editMultipleAllowed = True
    editIdAllowed = False

    # Unique fields (for errormessages from add/update)
    unique = None

    # Nouns
    singular = 'container'
    plural = 'containers'

    # Delete dependencies
    dependencies = []

    # Description format used by describe(id)
    # Example: room 021 (descr) to jack 123, building, office
    descriptionFormat = [('','name')]

    pathAdd = EDITPATH + [('Container',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Container',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Container',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Container',False)]

    class listDef(entryList):
        """ Describes the format of the list view of containers. """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Name',True,None)]

            self.cellDefinition = [(('vp_netbox_grp_infoid,name',
                                     'vp_netbox_grp_info',
                                     None,
                                     None,
                                     'name'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing vendor entries.
            The template uses this field information to display the form. """
    
        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            # Field definitions {field name: [input object, required]}
            f = {'name': [inputText(),REQ_TRUE,'Name',FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData)
            
class pageLocation(editdbPage):
    """ Describes editing of the location table. """
    
    basePath = BASEPATH + 'location/'
    table = nav.db.manage.Location
    pageName = 'location'
    tableName = 'location'
    tableIdKey = 'locationid'
    sequence = None
    editMultipleAllowed = True
    editIdAllowed = True

    # Description format used by describe(id)
    descriptionFormat = [('','locationid')]

    # Unique fields (for errormessages from add/update)
    unique = 'locationid'

    # Nouns
    singular = 'location'
    plural = 'locations'

    # Delete dependencies
    dependencies = [(nav.db.manage.Room,
                     'rooms',
                     'locationid',
                     '/report/room/?locationid=')]

    pathAdd = EDITPATH + [('Location',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Location',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Location',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Location',False)]

    class listDef(entryList):
        """ Describes location list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Location Id',True,None),
                                      ('Description',True,None)]

            self.cellDefinition = [(('locationid,locationid,descr',
                                     'location',
                                     None,
                                     None,
                                     'locationid'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing location entries.
            The template uses this field information to draw the form. """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table

            self.hiddenFields = {}

            disabled = False
            if editId:
                disabled = True

            f = {'locationid': [inputText(disabled=disabled,
                                maxlength=30),REQ_TRUE,'Location Id',
                                FIELD_STRING],
                 'descr': [inputText(),REQ_TRUE,'Description',
                           FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()
            
            if formData:
                self.formFill(formData)

            if disabled:
                self.addDisabled()



class pageNetbox(editdbPage):
    """ Describes editing of the netbox table """

    basePath = BASEPATH + 'netbox/'
    table = nav.db.manage.Netbox
    pageName = 'netbox'
    tableName = 'netbox'
    tableIdKey = 'netboxid'
    sequence = 'netbox_netboxid_seq'
    editMultipleAllowed = False
    editIdAllowed = True

    # Nouns
    singular = 'IP device'
    plural = 'IP devices'

    # Delete dependencies
    dependencies = []

    # Description format used by describe(id)
    descriptionFormat = [('','sysname')]

    pathAdd = EDITPATH + [('IP devices',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('IP devices',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('IP devices',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('IP devices',False)]

    class listDef(entryList):
        """ Describes the format of the list view of netboxes. """

        def ipCompare(self,ip1,ip2):
            """ Function for comparing two ip's. Used for sorting the
                netbox list. """

            # ip1[0] and ip2[0] are the sort parameter
            ip1 = ip1[0].split('.')
            ip2 = ip2[0].split('.')
            r = 0
            try:
                for i in range(0,4):
                    r = cmp(int(ip1[i]),int(ip2[i]))
                    if r != 0:
                        break
            except:
                r = 0
            return r

        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            # 1 = roomid
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Room',True,None),
                                      ('Sysname',True,None),
                                      ('IP',True,self.ipCompare),
                                      ('Category',True,None),
                                      ('Organisation',True,None),
                                      ('RO',True,None),
                                      ('RW',True,None),
                                      ('Type',True,None),
                                      ('Serial',True,None)]

            subcatTooltip = [['SELECT n.netboxid, nc.category ' + \
                             'FROM netbox n, netboxcategory nc ' + \
                             'WHERE nc.netboxid=n.netboxid',
                             ('Subcategories:','{$1}'),None],
                             ['SELECT netboxid,val FROM netboxinfo ' + \
                             'WHERE var=\'function\'',
                             ('Function:','{$1}'),None]]


            self.cellDefinition = [(('netboxid,roomid,sysname,ip,' + \
                                     'catid,orgid,ro,rw,type.typename,' + \
                                     'device.serial',
                                     'netbox',
                                     'LEFT JOIN type ON ' + \
                                     'netbox.typeid=type.typeid LEFT JOIN ' +\
                                     'device ON ' + \
                                     'netbox.deviceid=device.deviceid',
                                     None,
                                     'roomid,sysname'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,None,None,None,None),
                                     (2,'{p}edit/{id}',None,None,None),
                                     (3,None,None,None,None),
                                     (4,None,None,None,subcatTooltip),
                                     (5,None,None,None,None),
                                     (6,None,None,None,None),
                                     (7,None,None,None,None),
                                     (8,None,None,None,None),
                                     (9,None,None,None,None)])]


    class editbox(editbox):
        """ This is the first editbox on the edit netbox page. It asks
            for ip,ro,rw,cat,org and room. """    
        def __init__(self,page,req=None,editId=None,formData=None,
                     disabled=False):
            self.editId = editId
            self.page = page.pageName
            self.table = page.table
            self.hiddenFields = {}
            if editId:
                # Preserve the selected id
                self.addHidden(selectList.cnameChk,editId)
                self.sysname = manage.Netbox(editId).sysname
                self.editId = editId
                self.path = EDITPATH + [('IP devices','/editdb/netbox/list'),
                                        ('Edit',False)]
            else:
                self.path = EDITPATH + [('IP devices','/editdb/netbox/list'),
                                        ('Add',False)]
     
            o = [(None,'Select an organisation')]
            for org in manage.Org.getAllIterator(orderBy='orgid'):
                o.append((org.orgid,org.orgid + ' (' + str(org.descr) + ')'))

            r = [(None,'Select a room')]
            for room in manage.Room.getAllIterator(orderBy='roomid'):
                loc = manage.Location(room.location).descr
                r.append((room.roomid,room.roomid + ' (' + str(loc) + ':' + \
                          str(room.descr) + ')'))

            c = [(None,'Select a category')]
            for cat in manage.Cat.getAllIterator(orderBy='catid'):
                c.append((cat.catid,cat.catid + ' (' + str(cat.descr) + ')'))

            # Field definitions {field name: [input object, required]}
            f = {'ip': [inputText(disabled=disabled),REQ_TRUE,'IP or hostname',
                        FIELD_STRING],
                 'catid': [inputSelect(options=c,disabled=disabled),REQ_TRUE,
                           'Category',FIELD_STRING],
                 'orgid': [inputSelect(options=o,disabled=disabled),REQ_TRUE,
                           'Organisation',FIELD_STRING],
                 'roomid': [inputSelect(options=r,disabled=disabled),REQ_TRUE,
                           'Room',FIELD_STRING],
                 'ro': [inputText(disabled=disabled),REQ_FALSE,
                        'RO community',FIELD_STRING],
                 'rw': [inputText(disabled=disabled),REQ_FALSE,
                        'RW community',FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                # This box is for editing an existing netbox with id = editId
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData)

            if disabled:
                self.addDisabled()

    class editboxSerial(editbox):
        """ This editbox for inputing serials (or showing a serial if 
            it was found by snmp). """
        page = 'netboxserial'

        def __init__(self,gotRo,serial='',sysname=None,typeid=None,
                     snmpversion=None,formData=None,editSerial=False):
            self.hiddenFields = {}
            # Set info fields
            self.sysname = sysname
            if typeid:
                self.typename = manage.Type(typeid).typename
            else:
                self.typename = 'n/a'
            if snmpversion:
                self.snmpversion = snmpversion
            else:
                self.snmpversion = 'n/a'

            disabled = False
            self.help = None
            if gotRo:
                # RO was specified, so the box has been queried by SNMP
                if serial:
                    # It returned a serialnumber
                    disabled = True
                    self.help = 'Serialnumber retrieved by SNMP.'
                else:
                    self.help = 'Unable to retrieve serialnumber for this ' + \
                                'device by SNMP. ' + \
                                'Enter a serialnumber (optional).'
            else:
                if serial:
                    # Serial was entered manually
                    self.help = ''
                    disabled = True
                else:   
                    self.help = 'Enter a serialnumber (optional).'

            # If editSerial = True, override help text and always enable editing
            if editSerial:
                disabled = False
                # Should be some help text here
                self.help = ''

            self.fields = {'serial': [inputText(value=serial,disabled=disabled),
                                      REQ_FALSE,'Serialnumber',FIELD_STRING]}
            self.setControlNames()

            self.addHidden('sysname',sysname)
            self.addHidden('typeid',typeid)
            self.addHidden('snmpversion',snmpversion)

            if formData:
                self.formFill(formData)

            if disabled:
                self.addDisabled()
            
            # The editboxNetbox has UPDATE_ENTRY (which holds the id) or ADDNEW, 
            # don't need to repeat it here 
            self.boxName = IGNORE_BOX

    class editboxCategory(editbox):
        """ This editbox is for editing function and subcategories. """
        page = 'netboxcategory'

        def __init__(self,catid,editId=None,showHelp=True):
            self.hiddenFields = {}
            subcategories = False
            if len(manage.Subcat.getAll(where="catid='" + catid + "'")):
                subcategories = True

            self.help = None
            if editId:
                self.editId = editId
            elif showHelp:
                # Only show help if we're adding a new box
                if subcategories:
                    self.help = 'You can select one or more subcategories ' +\
                                'for IP devices with the selected category. ' +\
                                'You can also add an optional description ' +\
                                'of the function of this box.'
                else:
                    self.help = 'You can add an optional description of the '+\
                                'function of this IP device.'

            o = []
            for subcat in manage.Subcat.getAllIterator(where="catid='" + \
                                                           catid + "'"):
                o.append((subcat.subcatid,subcat.subcatid + ' (' + \
                          subcat.descr + ')'))
            if editId:
                if subcategories:
                    self.fields = {'subcat': \
                                  [inputMultipleSelect(options=o),REQ_FALSE,
                                   'Subcategory',FIELD_STRING],
                                  'function': [inputText(size=40),REQ_FALSE,
                                               'Function',FIELD_STRING]}
                else:
                    self.fields = {'function': [inputText(size=40),REQ_FALSE,
                                                'Function',FIELD_STRING]}
            else:
                if subcategories:
                    self.fields = {'subcat': [inputMultipleSelect(options=o),
                                             REQ_FALSE,'Subcategory',
                                             FIELD_STRING],
                                   'function': [inputText(size=40),REQ_FALSE,
                                                'Function',FIELD_STRING]}
                else:
                    self.fields = {'function': [inputText(size=40),REQ_FALSE,
                                                'Function',FIELD_STRING]}
     
            self.setControlNames()

            if editId:
                # Get selected netboxcategories
                sql = "SELECT category FROM netboxcategory WHERE " +\
                      "netboxid='%s'" \
                % (editId,)
                res = executeSQLreturn(sql)
                selected = []
                for s in res:
                   selected.append(s[0])
                   if subcategories:
                       # A subcat field is present for this box with this cat
                       self.fields['subcat'][0].value = selected

                # Get var 'function' from netboxinfo
                sql = "SELECT val FROM netboxinfo WHERE netboxid='%s' " \
                      % (editId,) + \
                      "AND var='function'"
                res = executeSQLreturn(sql)
                if res:
                    self.fields['function'][0].value = res[0][0]
            
            # The editboxNetbox has UPDATE_ENTRY (which holds the id), 
            # don't need to repeat it here 
            self.boxName = IGNORE_BOX

    # Overrides default add function
    def add(self,req,templateform,action):
        """ Adds a netbox. Overrides the default add function. """
        ADD_TYPE_URL = BASEPATH + 'type/edit/'
        STEP_1 = 1
        STEP_2 = 2
        CNAME_STEP = 'step' 
        # Step0: ask for ip,ro,rw,catid,org,room
        # Step1: ask for serial (and sysname,snmpversion and typeid)
        #        and ask for subcategory and function
        # Step2: add the box
        message = "Got SNMP response, but can't find type in " + \
                  "database. You must <a href=\"" + ADD_TYPE_URL + \
                  "?sysobjectid=%s\" " + \
                  "target=\"_blank\">add the " + \
                  "type</a>  before proceeding (a new window will " + \
                  "open, when the new type is added, press " + \
                  "Continue to proceed)."

        box = None
        error = None
        status = editdbStatus()
        action = 'predefined'
        form = req.form
        templateform.title = 'Add IP device'

        # Add editbox with hidden values for step (and deviceid)
        editboxHidden = editboxHiddenOrMessage()
        templateform.add(editboxHidden)
        # What step are we in?
        step = STEP_1
        if form.has_key(CNAME_STEP):
            step = int(form[CNAME_STEP])
        nextStep = step + 1

        if step == STEP_1:
            # Look up sysname in DNS
            result = re.match('^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})',
                              form['ip'])
            ip = form['ip']
            if result:
                # This is an IP
                try:
                    sysname = gethostbyaddr(ip)[0]
                except:
                    sysname = ip
            else:
                # Not an IP, possibly a hostname
                try:
                    ip = gethostbyname(form['ip'])
                    sysname = form['ip']
                except:
                    error = 'Invalid IP or hostname'

            # 'ip' should be numerical ip now
            editboxHidden.addHidden('hiddenIP',str(ip))

            # Check if sysname or ip is already present in db
            if not error:
                where = "ip = '" + ip + "'"
                box = manage.Netbox.getAll(where)
                if box:
                    box = box[0]
                    error = 'IP already exists in database (' + box.sysname + ')' 
                else:
                    # If IP isn't duplicate, check sysname
                    where = "sysname = '" + sysname + "'"
                    box = manage.Netbox.getAll(where)
                    if box:
                        error = 'Sysname ' + sysname + ' (' + box[0].ip + \
                                ') already exists in database'

            if error:
                status.errors.append(error)
                templateform.add(pageNetbox.editbox(pageNetbox,formData=form))
                return (status,action,templateform,None)

            if manage.Cat(form['catid']).req_snmp == True:
                # SNMP required by the selected category
                if len(form['ro']):
                    # RO specified, check SNMP
                    box = None
                    try:
                        box = initBox.Box(ip,form['ro'])
                    except nav.Snmp.TimeOutException:
                        # No SNMP response
                        status.errors.append('No SNMP response, check RO ' +\
                                             'community')
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            formData=form))
                        return (status,action,templateform,None)
                    except Exception, e:
                        # Other error (no route to host for example)
                        status.errors.append('Error: ' + str(sys.exc_info()[0]) + \
                                             ': ' + str(sys.exc_info()[1]))
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            formData=form))
                        return (status,action,templateform,None)
         
                    box.getDeviceId()
                    templateform.add(pageNetbox.editbox(pageNetbox,
                                                        formData=form,
                                                          disabled=True))
                    if box.typeid:
                        # Got type (required for these categories)
                        templateform.add(pageNetbox.editboxSerial(
                                         gotRo=True,
                                         serial=box.serial,
                                         sysname=sysname,
                                         typeid=box.typeid,
                                         snmpversion=box.snmpversion))

                        templateform.add(pageNetbox.editboxCategory(
                                         req.form['catid']))

                    else:
                        # Couldn't find type, ask user to add
                        # (type is required for this category)
                        message = message % (box.sysobjectid,)
                        templateform.add(editboxHiddenOrMessage(message))
                        nextStep = STEP_1
                else:
                    # RO blank, return error
                    status.errors.append('Category ' + form['catid'] + \
                                         ' requires an RO community')
                    templateform.add(pageNetbox.editbox(pageNetbox,
                                                        formData=form))
                    nextStep = STEP_1
            else:
                # SNMP not required by cat
                message = "Got SNMP response, but can't find type in " + \
                          "database. Type is not required for this " +\
                          "category, but if you want you can "+\
                          "<a href=\"" + ADD_TYPE_URL + \
                          "?sysobjectid=%s\" " + \
                          "target=\"_blank\">" + \
                          "add this type to the database</a>. " +\
                          "After adding the type, start the registration " +\
                          "again to set correct type on this IP device."

                if len(form['ro']):
                    # RO specified, check SNMP anyway
                    box = None
                    try:
                        box = initBox.Box(ip,form['ro'])
                    except nav.Snmp.TimeOutException:
                        status.errors.append('No SNMP response, check RO community')
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            formData=form))
                        return (status,action,templateform,None)
                    except Exception, e:
                        # Other error (no route to host for example)
                        status.errors.append('Error: ' + str(sys.exc_info()[0]) + \
                                             ': ' + str(sys.exc_info()[1]))
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            formData=form))
                        return (status,action,templateform,None)

                    box.getDeviceId()
                    templateform.add(pageNetbox.editbox(pageNetbox,
                                                        formData=form,
                                                        disabled=True))
                    if not box.typeid:
                        # Unknown type. Type is not required,
                        # but ask if user wants to add type anyway.
                        message = message % (box.sysobjectid,)
                        templateform.add(editboxHiddenOrMessage(message))

                    templateform.add(pageNetbox.editboxSerial(gotRo=True,
                                     serial=box.serial,
                                     sysname=sysname,
                                     typeid=box.typeid,
                                     snmpversion=box.snmpversion))

                    templateform.add(pageNetbox.editboxCategory(
                                     req.form['catid']))
                else:
                    # RO blank, don't check SNMP, ask for serial
                    # and subcat+function
                    templateform.add(pageNetbox.editbox(pageNetbox,
                                                        formData=form,
                                                        disabled=True))
                    templateform.add(pageNetbox.editboxSerial(gotRo=False,
                                                         sysname=sysname))
                    templateform.add(pageNetbox.editboxCategory(
                                                req.form['catid']))
                    nextStep = STEP_2
        if step == STEP_2:
            # If we have serial, check if the device is already
            # present in the databse
            deviceId = None
            serial = req.form['serial']
            if len(serial):
                # Any devices in the database with this serial?
                where = "serial = '" + str(serial) + "'"
                device = manage.Device.getAll(where)
                if device:
                    # Found a device with this serial
                    deviceId = str(device[0].deviceid)
                    # Must check if there already is a box with this serial
                    where = "deviceid = '" + deviceId + "'"
                    box = manage.Netbox.getAll(where)
                    if box:
                        # A box with this serial already exists
                        # in the database. Ask for serial again.
                        box = box[0]
                        status.errors.append('An IP device (' + box.sysname + \
                                             ') with the serial \'' +\
                                             str(serial) +\
                                             '\' already exists.')
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            formData=form,
                                                            disabled=True))
                        templateform.showConfirm = True
                        templateform.add(pageNetbox.editboxSerial(
                                                      gotRo=False,
                                                      sysname=
                                                      req.form['sysname']))
                        templateform.add(pageNetbox.editboxCategory(
                                                      req.form['catid']))
                        # Ask for serial again. Must "refresh" hidden values.
                        nextStep = STEP_2
                        editboxHidden.addHidden(CNAME_STEP,nextStep)
                        editboxHidden.addHidden('hiddenIP',form['hiddenIP'])
                        return (status,action,templateform,None)
                else:
                    # Not found, make new device
                    deviceId = None

            # Get selected subcategories
            subcatlist = None
            if form.has_key('subcat'):
                subcatlist = form['subcat']
            # Get function
            function = None
            if form.has_key('function'):
                function = form['function']
            # Get typeid and snmpversion (from hidden inputs)
            typeId = None
            if form.has_key('typeid'):
                typeId = form['typeid']
            snmpversion = None
            if form.has_key('snmpversion'):
                snmpversion = form['snmpversion']
            # Get sysname (from hidden input)
            sysname = req.form['sysname']

            # Insert netbox
            # hiddenIP contains numerical ip after dns lookup
            # (in case user entered a hostname in the ip field)
            insertNetbox(form['hiddenIP'],form['sysname'],
                         form['catid'],form['roomid'],
                         form['orgid'],form['ro'],
                         form['rw'],deviceId,
                         form['serial'],typeId,
                         snmpversion,subcatlist,
                         function)
            action = 'list'
            status.messages.append('Added IP device: ' + form['sysname'] + ' (' + \
                                   req.form['hiddenIP'] + ')')
        if not step == STEP_2: 
            # Unless this is the last step, set the nextStep
            editboxHidden.addHidden(CNAME_STEP,nextStep) 
        return (status,action,templateform,None)

    # Overloads default update function
    def update(self,req,templateform,selected):
        """ Updates a netbox, overrides the default update function. """
        selected = selected[0]
        ADD_TYPE_URL = BASEPATH + 'type/edit/'
        STEP_1 = 1
        STEP_2 = 2
        CNAME_STEP = 'step' 
        # Step0: ask for ip,ro,rw,catid,org,room
        # Step1: ask for serial (and sysname,snmpversion and typeid)
        #        ask for subcategory and function
        # Step2: update the box
        message = "Got SNMP response, but can't find type in " + \
                  "database. You must <a href=\"" + ADD_TYPE_URL + \
                  "?sysobjectid=%s\" " + \
                  "target=\"_blank\">add the " + \
                  "type</a>  before proceeding (a new window will " + \
                  "open, when the new type is added, press " + \
                  "Continue to proceed)."

        box = None
        error = None
        status = editdbStatus()
        action = 'predefined'
        form = req.form
        templateform.title = 'Edit IP device'
        # Preserve the URL
        templateform.action = BASEPATH + 'netbox/edit/' + selected

        # Add editbox with hidden values for step (and deviceid)
        editboxHidden = editboxHiddenOrMessage()
        templateform.add(editboxHidden)
        # What step are we in?
        step = STEP_1
        if form.has_key(CNAME_STEP):
            step = int(form[CNAME_STEP])
        nextStep = step + 1

        oldBox = editTables.editdbNetbox(selected)

        if step == STEP_1:
            # Look up sysname in DNS, it might have changed
            # since the box was initially added
            result = re.match('^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})',
                              form['ip'])
            ip = form['ip']
            if result:
                # This is an IP
                try:
                    sysname = gethostbyaddr(ip)[0]
                except:
                    sysname = ip
            else:
                # Not an IP, possibly a hostname
                try:
                    ip = gethostbyname(form['ip'])
                    sysname = form['ip']
                except:
                    error = 'Invalid IP or hostname'

            # 'ip' should be numerical ip now
            editboxHidden.addHidden('hiddenIP',str(ip))

            # Check if (edited) ip is already present in db
            #if (oldBox.ip != form['ip'])
            if oldBox.ip != ip and (not error):
                # If IP differs from the old, check for uniqueness
                where = "ip = '" + ip + "'"
                box = manage.Netbox.getAll(where)
                if box:
                    error = 'IP already exists in database'
                if oldBox.sysname != sysname and not error:
                    # If IP isn't duplicate, check if (new) sysname is unique
                    where = "sysname = '" + sysname + "'"
                    box = manage.Netbox.getAll(where)
                    if box:
                        error = 'Sysname ' + sysname + ' (' + box[0].ip + \
                                ') already exists in database'
            if error:
                status.errors.append(error)
                templateform.add(pageNetbox.editbox(pageNetbox,
                                                    editId=selected,
                                                      formData=form))
                return (status,action,templateform,selected)

            if manage.Cat(form['catid']).req_snmp == True:
                # SNMP required by this category
                if len(form['ro']):
                    # RO specified, check SNMP
                    box = None
                    try:
                        box = initBox.Box(form['ip'],form['ro'])
                    except nav.Snmp.TimeOutException:
                        # No SNMP answer
                        status.errors.append('No SNMP response, check ' +\
                                             'RO community')
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            editId=selected,
                                                            formData=form))
                        return (status,action,templateform,selected)
                    except Exception, e:
                        # Other error (no route to host for example)
                        status.errors.append('Error: '+str(sys.exc_info()[0])+\
                                             ': ' + str(sys.exc_info()[1]))
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            editId=selected,
                                                            formData=form))
                        return (status,action,templateform,selected)
         
                    box.getDeviceId()
                    templateform.add(pageNetbox.editbox(pageNetbox,
                                                        editId=selected,
                                                        formData=form,
                                                        disabled=True))

                    if box.typeid:
                        # Got type
                        if box.serial:
                            serial = box.serial
                        else:
                            serial = oldBox.device.serial
                        templateform.add(pageNetbox.editboxSerial(
                                         gotRo=True,
                                         serial=serial,
                                         sysname=sysname,
                                         typeid=box.typeid,
                                         snmpversion=box.snmpversion,
                                         editSerial=False))

                        # Show subcategory/function editbox 
                        # If category has changed, then don't 
                        # load the old subcatinfo
                        if oldBox.catid != form['catid']:
                            templateform.add(pageNetbox.editboxCategory(
                                                          req.form['catid'],
                                                          showHelp=False))
                        else:
                            templateform.add(pageNetbox.editboxCategory(
                                                          req.form['catid'],
                                                          selected))
                    else:
                        # Couldn't find type, ask user to add
                        message = message % (box.sysobjectid,)
                        templateform.add(editboxHiddenOrMessage(message))
                else:
                    # RO blank, return error
                    status.errors.append('Category ' + form['catid'] + \
                                         ' requires a RO community')
                    templateform.add(pageNetbox.editbox(pageNetbox,
                                                        editId=selected,
                                                        formData=form))
                    nextStep = STEP_1
            else:
                # SNMP not required by cat
                message = "Got SNMP response, but can't find type in " + \
                          "database. Type is not required for this " +\
                          "category, but if you want you can "+\
                          "<a href=\"" + ADD_TYPE_URL + \
                          "?sysobjectid=%s\" " + \
                          "target=\"_blank\">" + \
                          "add this type to the database</a>. " +\
                          "After adding the type, start the registration " +\
                          "again to set correct type on IP device."

                if len(form['ro']):
                    # RO specified, check SNMP anyway
                    box = None
                    try:
                        box = initBox.Box(form['ip'],form['ro'])
                    except nav.Snmp.TimeOutException:
                        status.errors.append('Error: ' + str(sys.exc_info()[0]) + \
                                             ': ' + str(sys.exc_info()[1]))
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            editId=selected,
                                                            formData=form))
                        return (status,action,templateform,selected)
                    except Exception, e:
                        # Other error (no route to host for example)
                        status.errors.append('Error: '+str(sys.exc_info()[0])+\
                                             ': ' + str(sys.exc_info()[1]))
                        templateform.add(pageNetbox.editbox(pageNetbox,
                                                            editId=selected,
                                                            formData=form))
                        return (status,action,templateform,selected)

                    box.getDeviceId()
                    templateform.add(pageNetbox.editbox(pageNetbox,
                                                        editId=selected,
                                                        formData=form,
                                                        disabled=True))
                    if not box.typeid:
                        # Unknown type. Type is not required,
                        # but ask if user wants to add type anyway.
                        message = message % (box.sysobjectid,)
                        templateform.add(editboxHiddenOrMessage(message))
                        
                    if box.serial:
                        serial = box.serial
                    else:
                        serial = oldBox.device.serial
                
                    templateform.add(pageNetbox.editboxSerial(gotRo=True,
                                     serial=serial,
                                     sysname=sysname,
                                     typeid=box.typeid,
                                     snmpversion=box.snmpversion,
                                     editSerial=False))

                    # Show subcategory/function editbox 
                    # If category has changed, then don't 
                    # load the old subcatinfo
                    if oldBox.catid != form['catid']:
                        templateform.add(pageNetbox.editboxCategory(
                                                      req.form['catid'],
                                                      showHelp=False))
                    else:
                        templateform.add(pageNetbox.editboxCategory(
                                                      req.form['catid'],
                                                      selected))
                else:
                    # RO blank, don't check SNMP, ask for serial
                    templateform.add(pageNetbox.editbox(pageNetbox,
                                                        editId=selected,
                                                        formData=form,
                                                        disabled=True))
                    serial = oldBox.device.serial
                    templateform.add(pageNetbox.editboxSerial(gotRo=False,
                                                         serial = serial,
                                                         sysname=sysname,
                                                         editSerial=True))

                    # Show subcategory/function editbox 
                    # If category has changed, then don't 
                    # load the old subcatinfo
                    if oldBox.catid != form['catid']:
                        templateform.add(pageNetbox.editboxCategory(
                                                      req.form['catid'],
                                                      showHelp=False))
                    else:
                        templateform.add(pageNetbox.editboxCategory(
                                                      req.form['catid'],
                                                      selected))
                    nextStep = STEP_2
        if step == STEP_2:
            # Always use the old serial
            serial = oldBox.device.serial
                
            # If the serial was changed we have to check if it's unique
            if box:
                # Got serial by SNMP?
                newSerial = box.serial
            else:
                newSerial = form['serial']

            if len(newSerial):
                deviceId = None
                if serial != newSerial:
                    # Any other devices in the database with this serial?
                    where = "serial = '" + str(newSerial) + "'"
                    device = manage.Device.getAll(where)
                    if device:
                        # Found a device with this serial
                        deviceId = str(device[0].deviceid)
                        # Must check if there already is a box with this serial
                        where = "deviceid = '" + deviceId + "'"
                        box = manage.Netbox.getAll(where)
                        if box:
                            # A box with this serial already exists
                            # in the database. Ask for serial again.
                            box = box[0]
                            status.errors.append('An IP device (' + box.sysname + \
                                                 ') with the serial \'' +\
                                                 str(serial) +\
                                                 '\' already exists.')
                            templateform.add(pageNetbox.editbox(pageNetbox,
                                                                formData=form,
                                                                disabled=True))
                            templateform.showConfirm = True
                            templateform.add(pageNetbox.editboxSerial(
                                                          gotRo=False,
                                                          sysname=
                                                          req.form['sysname']))
                            templateform.add(pageNetbox.editboxCategory(
                                                          req.form['catid']))
                            # Ask for serial again. Must "refresh" hidden values.
                            nextStep = STEP_2
                            editboxHidden.addHidden(CNAME_STEP,nextStep)
                            editboxHidden.addHidden('hiddenIP',form['hiddenIP'])

                            #templateform.add(editboxHiddenOrMessage(message))
                            return (status,action,templateform,selected)
            else:
                # No serial, make new device
                deviceId = None

            # Get selected subcats, function, type and snmpversion
            subcatlist = None
            if form.has_key('subcat'):
                subcatlist = form['subcat']
                if not type(subcatlist) is list:
                    subcatlist = [subcatlist]
            function = None
            if form.has_key('function'):
                function = req.form['function']
            typeId = None
            if form.has_key('typeid'):
                typeId = req.form['typeid']
            snmpversion = None
            if form.has_key('snmpversion'):
                snmpversion = form['snmpversion']
                # Only use first char of snmpversion, don't insert things like
                # '2c'
                if len(snmpversion):
                    snmpversion = snmpversion[0]

            # Update netbox
            fields = {'ip': form['hiddenIP'],
                      'sysname': form['sysname'],
                      'catid': form['catid'],
                      'roomid': form['roomid'],
                      'orgid': form['orgid'],
                      'ro': form['ro'],
                      'rw': form['rw']}

            # Set type if initbox found it
            if typeId:
                fields['typeid'] = typeId

            # Update deviceid if it has changed (ie. if serial
            # was updated and a device with this serial already
            # existed in the database
            if deviceId:
                fields['deviceid'] = deviceId

            # Get prefixid
            query = "SELECT prefixid FROM prefix WHERE '%s'::inet << netaddr" \
                    % (fields['ip'],)
            try:
                result = executeSQLreturn(query) 
                fields['prefixid'] = str(result[0][0])
            except:
                pass        

            # Set netbox.uptodate = false (to make gdd update this device)
            fields['uptodate'] = 'f'
            # Update netbox
            updateEntryFields(fields,'netbox','netboxid',selected)

            # Update device (unless the serial was found in an already
            # existing device)
            if not deviceId:
                if len(form['serial']) and \
                   (form['serial']!=oldBox.device.serial):
                    # Set new serial, if it has changed
                    fields = {'serial': form['serial']}
                    deviceId = str(oldBox.device.deviceid)
                    updateEntryFields(fields,'device','deviceid',deviceId)

            # Remove old subcat and function entries
            netboxId = oldBox.netboxid
            deleteEntry([netboxId],'netboxcategory','netboxid')
            deleteEntry([netboxId],'netboxinfo','netboxid')

            # If subcatlist and function is given, insert them
            if subcatlist:
                for sc in subcatlist:
                    fields = {'netboxid': netboxId,
                              'category': sc}
                    addEntryFields(fields,'netboxcategory')

            if function:
                fields = {'netboxid': netboxId,
                          'key': '',
                          'var': 'function',
                          'val': function}
                addEntryFields(fields,'netboxinfo')

            action = 'list'
            status.messages.append('Updated IP device ' + form['sysname'] + ' (' + \
                                   form['ip'] + ')')

        if not step == STEP_2: 
            # Unless this is the last step, set the nextStep
            editboxHidden.addHidden(CNAME_STEP,nextStep) 
        return (status,action,templateform,selected)

class pageOrg(editdbPage):
    """ Describes editing of the org table. """
    
    basePath = BASEPATH + 'org/'
    table = nav.db.manage.Org
    pageName = 'org'
    tableName = 'org'
    tableIdKey = 'orgid'
    sequence = None
    editMultipleAllowed = True
    editIdAllowed = True

    # Description format used by describe(id)
    # Example: room 021 (descr) to jack 123, building, office
    descriptionFormat = [('','orgid')]

    # Unique fields (for errormessages from add/update)
    unique = 'orgid'

    # Nouns
    singular = 'organisation'
    plural = 'organisations'

    # Delete dependencies
    dependencies = [(manage.Org,
                    'organisations',
                    'parent',
                    '/report/org/?parent='),
                    (manage.Netbox,
                    'boxes',
                    'orgid',
                    '/report/netbox/?orgid=')]

    pathAdd = EDITPATH + [('Organisation',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Organisation',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Organisation',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Organisation',False)]

    class listDef(entryList):
        """ Describes org list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Organisation',True,None),
                                      ('Parent',True,None),
                                      ('Description',True,None),
                                      ('Optional 1',True,None),
                                      ('Optional 2',True,None),
                                      ('Optional 3',True,None)]

            self.cellDefinition = [(('orgid,orgid,parent,descr,opt1,opt2,opt3',
                                     'org',
                                     None,
                                     None,
                                     'orgid'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None),
                                     (3,None,None,None,None),
                                     (4,None,None,None,None),
                                     (5,None,None,None,None),
                                     (6,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing org entries.
            The template uses this field information to draw the form. """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            # Field definitions {field name: [input object, required]}
            o = [('','No parent')]

            for org in self.table.getAllIterator(orderBy='orgid'):
                o.append((org.orgid,org.orgid + \
                          ' (' + str(org.descr) + ')'))

            f = {'orgid': [inputText(maxlength=30),REQ_TRUE,'Organisation',
                           FIELD_STRING],
                 'parent': [inputSelect(options=o),REQ_NONEMPTY,'Parent',
                            FIELD_STRING],
                 'descr': [inputText(),REQ_FALSE,'Description',FIELD_STRING],
                 'opt1': [inputText(),REQ_FALSE,'Optional 1',FIELD_STRING],
                 'opt2': [inputText(),REQ_FALSE,'Optional 2',FIELD_STRING],
                 'opt3': [inputText(),REQ_FALSE,'Optional 3',FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData)


class pagePatch(editdbPage):
    """ Describes editing of the patch table. """
    
    basePath = BASEPATH + 'patch/'
    table = nav.db.manage.Patch
    pageName = 'patch'
    tableName = 'patch'
    tableIdKey = 'patchid'
    sequence = 'patch_patchid_seq'
    editMultipleAllowed = False
    editIdAllowed = False

    # Set action which makes browser jump to the first
    # selectTree layoutbox. Makes editing easier on screens
    # with low y resolution.
    action = basePath + 'edit/#top'

    # Unique fields (for errormessages from add/update)
    # Set to none since this page checks this in it's own 
    # add/update functions
    unique = None

    # Nouns
    singular = 'patch'
    plural = 'patches'

    # Delete dependencies
    dependencies = []

    # Description format used by describe(id)
    # Example: from netbox,module x,port y to jack z,room,building,location
    descriptionFormat = [('from \'','cabling.jack'),
                         (', ','cabling.targetroom'),
                         (', ','cabling.building'),
                         (', ','cabling.room.location.locationid'),
                         ('\' to switch \'','swport.module.netbox.sysname'),
                         (', module ','swport.module.module'),
                         (', port ','swport.port'),
                         ('\'',None)]

    pathAdd = EDITPATH + [('Patch',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Patch',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Patch',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Patch',False)]

    class listDef(entryList):
        """ Describes patch list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # List filters
            self.filters = [['Show patches in room ',
                            ('','Select a room'),
                            ('roomid,descr',
                             'room',
                             None,
                             '((SELECT count(*) FROM patch,cabling WHERE ' +\
                             'patch.cablingid=cabling.cablingid AND ' +\
                             'cabling.roomid=room.roomid) > 0)',
                             'room.roomid'),
                             '{id}',
                             '{id} ({descr})',
                             'flt_room',
                             'cabling.roomid',
                             nav.db.manage.Patch,
                             'cabling.room.roomid']]

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Switch',True,None),
                                      ('Module',True,None),
                                      ('Port',True,None),
                                      ('Room',True,None),
                                      ('Jack',True,None),
                                      ('Split',True,None)]

            self.cellDefinition = [(('patch.patchid,netbox.sysname,' +\
                                     'module.module,swport.port,' +\
                                     'room.roomid,cabling.jack,patch.split',
                                     'patch,cabling,room,netbox,swport,module',
                                     None,
                                     'patch.cablingid=cabling.cablingid ' +\
                                     'AND cabling.roomid=room.roomid AND ' +\
                                     'patch.swportid=swport.swportid AND ' +\
                                     'swport.moduleid=module.moduleid AND ' +\
                                     'module.netboxid=netbox.netboxid',
                                     'room.locationid,room.roomid,' +\
                                     'netbox.sysname,module.module,' +\
                                     'swport.port'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None),
                                     (3,None,None,None,None),
                                     (4,None,None,None,None),
                                     (5,None,None,None,None),
                                     (6,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing patch entries.
            The template uses this field information to display the form. 
            This box uses the selectTree classes and updates itself
            instead of using editdbPage.formFill(). """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            self.hiddenFields = {}

            # Set the name of this boxname to reflect that we are
            # updating an entry
            if editId:
                self.boxName = UPDATE_ENTRY
                self.boxId = editId
                self.addHidden(UPDATE_ENTRY,editId)

            selectedSwport = []
            selectedModule = []
            selectedSwitch = []
            selectedJack = []
            selectedRoom = []
            selectedLocation = []
            split = None
            addRoom = []
            addJack = []
            addSwport = []
            if editId:
                # Preserve the selected id
                self.addHidden(selectList.cnameChk,editId)
                patch = self.table(editId)
                selectedSwport = [patch.swport.swportid]
                selectedModule = [patch.swport.module.moduleid]
                selectedSwitch = [patch.swport.module.netbox.netboxid]
                selectedJack = [patch.cabling.cablingid]
                selectedRoom = [patch.cabling.room.roomid]
                selectedLocation = [patch.cabling.room.location.locationid]
                split = patch.split
                # Entries which must be added manually since the sql
                # excludes them (not to be shown while adding, but must
                # be shown while editing since they are selected)
                addRoom = [(patch.cabling.room.location.locationid,
                            patch.cabling.room.roomid,
                            patch.cabling.room.roomid + ' (' +\
                            patch.cabling.room.descr + ')',
                            True)]
                addJack = [(patch.cabling.room.roomid,
                            str(patch.cabling.cablingid),
                            patch.cabling.jack,
                            True)]
                addSwport = [(str(patch.swport.module.moduleid),
                              str(patch.swport.swportid),
                              str(patch.swport.port),
                              True)]
  
            self.help = 'Add or update a patch by selecting a jack and a ' +\
                        'switchport. Optionally select a split. Only rooms '+\
                        'with at least one switch and at least one available '+\
                        'jack are listed. Available jacks have either '+\
                        'no patch or at most one splitted patch connected.'

            if req:
                select1 = simpleSelect('Location',
                                       'cn_loc',
                                       ('locationid,descr',
                                        'location',
                                        None,
                                        None,
                                        'locationid'),
                                        selectedLocation,
                                        optionFormat='$1 ($2)',
                                        selectMultiple=False,
                                        multipleHeight=8)

                # SQL (where) for selecting rooms
                # Only selects rooms which have one or more boxes of 
                # category EDGE,SW or GSW and where there are "available" 
                # jacks. Available means a jack which isn't already in 
                # use by a patch, or a jack which is use by one patch
                # but is splitted.
                roomSQL = """((SELECT count(*) FROM cabling WHERE cabling.roomid=room.roomid AND (((SELECT count(*) FROM patch WHERE patch.cablingid=cabling.cablingid AND patch.split='no') = 0) AND ((SELECT count(*) FROM patch WHERE patch.cablingid=cabling.cablingid AND patch.split!='no')) < 2)) > 0) AND ((SELECT count(*) FROM netbox WHERE roomid=room.roomid AND (netbox.catid='SW' OR netbox.catid='GSW' OR netbox.catid='EDGE')) > 0)"""

                select2 = updateSelect(select1,
                                       'locationid',
                                       'Room',
                                       'cn_room',
                                       ('roomid,descr',
                                        'room',
                                        None,
                                        roomSQL,
                                        'roomid'),
                                        selectedRoom,
                                        addRoom,
                                        optionFormat='$1 ($2)',
                                        selectMultiple=False,
                                        multipleHeight=8)

                # SQL (where) for selecting jacks
                # Selects "available" jacks. Available means a jack which isn't
                # already in use by a patch, or a jack which is use by one 
                # patch but is splitted.
                jackSQL = """(((SELECT count(*) FROM patch WHERE patch.cablingid=cabling.cablingid AND patch.split='no') = 0) AND ((SELECT count(*) FROM patch WHERE patch.cablingid=cabling.cablingid AND patch.split!='no') < 2))"""

                select3 = updateSelect(select2,
                                       'roomid',
                                       'Jack',
                                       'cn_jack',
                                       ('cablingid,jack',
                                        'cabling',
                                        None,
                                        jackSQL,
                                        'jack'),
                                        selectedJack,
                                        addJack,
                                        optgroupFormat='Room $1',
                                        setOnChange=True,
                                        selectMultiple=False,
                                        multipleHeight=8)

                whereSwitch = "(catid='EDGE' or catid='SW' or catid='GSW')"
                select4 = updateSelect(select2,
                                       'roomid',
                                       'Switch',
                                       'cn_switch',
                                       ('netboxid,sysname',
                                        'netbox',
                                        None,
                                        whereSwitch,
                                        'sysname'),
                                        selectedSwitch,
                                        optgroupFormat='Room $1',
                                        selectMultiple=False,
                                        multipleHeight=8)

                select5 = updateSelect(select4,
                                       'netboxid',
                                       'Module',
                                       'cn_module',
                                       ('moduleid,module',
                                        'module',
                                       None,
                                       None,
                                       'module'),
                                       selectedModule,
                                       optgroupFormat='$2',
                                       selectMultiple=False,
                                       multipleHeight=8)

                # Don't show swports that are already in use
                swportSQL = "((SELECT count(*) FROM patch WHERE patch.swportid=swport.swportid) < 1)"

                select6 = updateSelect(select5,
                                       'moduleid',
                                       'Port',
                                       'cn_swport',
                                       ('swportid,port',
                                        'swport',
                                        None,
                                        swportSQL,
                                        'port'),
                                        selectedSwport,
                                        addSwport,
                                        optgroupFormat='Module $2',
                                        setOnChange=False,
                                        selectMultiple=False,
                                        multipleHeight=8)

                st = selectTree()
                st.addSelect(select1)
                st.addSelect(select2)
                st.addSelect(select3)
                st.addSelect(select4)
                st.addSelect(select5)
                st.addSelect(select6)
                st.update(req.form)

                lb = selectTreeLayoutBox(htmlId='top')
                lb.addSelect(select1)
                lb.addSelect(select2)
                lb.addSelect(select3)

                lb2 = selectTreeLayoutBox()
                lb2.addSelect(select4)
                lb2.addSelect(select5)
                lb2.addSelect(select6)

                # Check if the selected jack is already used in a patch
                # (ie. a split). In that case, set the split select to
                # the same value in this form
                if req.form.has_key('cn_jack'):
                    if len(req.form['cn_jack']):
                        where = "cablingid='" + req.form['cn_jack'] + "'"
                        patch = nav.db.manage.Patch.getAll(where)
                        if patch:
                            # Already exists a patch with this jack, it must
                            # be splitted, select the same split in this form
                            patch = patch[0]
                            split = SPLIT_OPPOSITE[patch.split]

                # Remember split from form (overrides split from other patch)
                if req.form.has_key('split'):
                    if req.form['split'] != 'no':
                        split = req.form['split']

            else:
                lb = None
                lb2 = None


            # Field definitions {field name: [input object, required]}
            f = {'box1': [inputTreeSelect(treeselect=lb),
                            REQ_FALSE,'Room',FIELD_STRING],
                 'box2': [inputTreeSelect(treeselect=lb2),
                             REQ_FALSE,'Switch port',FIELD_STRING],
                 'split': [inputSelect(options=SPLIT_LIST),REQ_FALSE,
                           'Split',FIELD_STRING]}

            if split:
                f['split'][0].value = split

            self.fields = f
            self.setControlNames()

    def add(self,req,templateForm,action):
            """ Adds patch entries. Overrides the default add function. """
            error = None
            status = editdbStatus()

            split = None
            cablingid = None
            swportid = None
            if req.form.has_key('split'):
                split = req.form['split']
            else:
                error = "Missing required field 'Split'"
            if req.form.has_key('cn_jack'):
                cablingid = req.form['cn_jack']
            else:
                error = "Missing required field 'Jack'"
            if req.form.has_key('cn_swport'):
                swportid = req.form['cn_swport']
            else:
                error = "Missing required field 'Port'"

            if not error:
                # Check if the selected jack already belongs to a patch
                where = "cablingid='" + cablingid + "'"
                otherPatch = nav.db.manage.Patch.getAll(where)
                if otherPatch:
                    # Already exists a patch with this jack, it must
                    # be splitted, if split is changed then do something
                    otherPatch = otherPatch[0]
                    otherSplit = otherPatch.split

                    if SPLIT_OPPOSITE[split] != otherSplit:
                        # Splits are different, either update split on the
                        # other entry, or delete it if this split='no'
                        otherPatchId = str(otherPatch.patchid)
                        # SPLIT_LIST[0][0] is default entry id
                        if split == SPLIT_LIST[0][0]:
                            # Delete other entry
                            deleteEntry([otherPatchId],'patch','patchid')
                        else:
                            # Update other entry
                            fields = {'split': SPLIT_OPPOSITE[split]}
                            updateEntryFields(fields,self.tableName,
                                              self.tableIdKey,otherPatchId)

                fields = {'cablingid': cablingid,
                          'swportid': swportid,
                          'split': split}

                try:
                    patchId = addEntryFields(fields,self.tableName,
                                             (self.tableIdKey,self.sequence))
                    action = 'list'
                except psycopg.IntegrityError,e:
                    error = 'There already exists a patch from this jack ' +\
                            'to that port'

            if error:
                status.errors.append(error)
            else:
                message = 'Added patch: ' + self.describe(patchId)
                status.messages.append(message)
                action = 'list'
            return (status,action,templateForm,patchId)

    def update(self,req,outputForm,selected):
        """ Updates patch entries. Overrides the default update function. """

        status = editdbStatus()
        error = None
        action = 'edit'

        split = None
        cablingid = None
        swportid = None
        if req.form.has_key('split'):
            split = req.form['split']
        else:
            error = "Missing required field 'Split'"
        if req.form.has_key('cn_jack'):
            cablingid = req.form['cn_jack']
        else:
            error = "Missing required field 'Jack'"
        if req.form.has_key('cn_swport'):
            swportid = req.form['cn_swport']
        else:
            error = "Missing required field 'Port'"

        if not error:
            # Check if the selected jack belongs to another patch
            where = "cablingid='" + cablingid + "' AND NOT patchid='" +\
                    selected[0] + "'"
            otherPatch = nav.db.manage.Patch.getAll(where)
            if otherPatch:
                # Already exists a patch with this jack
                otherPatch = otherPatch[0]
                #otherSplit = otherPatch.split

                # Update other split
                otherPatchId = str(otherPatch.patchid)
                # SPLIT_LIST[0][0] is default entry id
                if split == SPLIT_LIST[0][0]:
                    # Delete other entry
                    deleteEntry([otherPatchId],'patch','patchid')
                else:
                    # Update other entry
                    fields = {'split': SPLIT_OPPOSITE[split]}
                    updateEntryFields(fields,self.tableName,self.tableIdKey,
                                      otherPatchId)

            fields = {'cablingid': cablingid,
                      'swportid': swportid,
                      'split': split}

            try:
                updateEntryFields(fields,self.tableName,self.tableIdKey,
                                  selected[0])
                action = 'list'
            except psycopg.IntegrityError,e:
                error = 'There already exists a patch from this swport ' +\
                        'to that jack'
                action = 'edit'
        if error:
            status.errors.append(error)
        else:
            message = 'Updated patch: ' + self.describe(selected[0])
            status.messages.append(message)
            action = 'list'
 
        return (status,action,outputForm,selected)
 

class pagePrefix(editdbPage):
    """ Describes editing of the prefix table for nettypes of 'static'
        'reserved' or 'scope'. """

    basePath = BASEPATH + 'prefix/'
    table = nav.db.manage.Prefix
    pageName = 'prefix'
    tableName = 'prefix'
    tableIdKey = 'prefixid'
    sequence = 'prefix_prefixid_seq'
    editMultipleAllowed = False
    editIdAllowed = False

    # Description format used by describe(id)
    descriptionFormat = [('','netaddr'),
                         (', ','vlan.nettype')]

    # Unique fields (for errormessages from add/update)
    unique = 'netaddr'

    # Nouns
    singular = 'prefix'
    plural = 'prefixes'

    # Delete dependencies
    dependencies = []

    pathAdd = EDITPATH + [('Prefix',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Prefix',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Prefix',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Prefix',False)]

    class listDef(entryList):
        """ Describes prefix list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Prefix/mask',True,None),
                                      ('Nettype',True,None),
                                      ('Org',True,None),
                                      ('Netident',True,None),
                                      ('Usage',True,None),
                                      ('Description',True,None),
                                      ('Vlan',True,None)]

            where = "(vlan.nettype in (SELECT nettypeid " + \
                    "                  FROM nettype " + \
                    "                  WHERE edit='t'))"

            self.cellDefinition = [(('prefix.prefixid,netaddr,vlan.nettype,' +\
                                     'vlan.orgid,vlan.netident,vlan.usageid,' +\
                                     'vlan.description,vlan.vlan',
                                     'prefix,vlan',
                                     None,
                                     'prefix.vlanid=vlan.vlanid AND ' + where,
                                     'prefix.netaddr,nettype'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None),
                                     (3,None,None,None,None),
                                     (4,None,None,None,None),
                                     (5,None,None,None,None),
                                     (6,None,None,None,None),
                                     (7,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing patch entries.
            The template uses this field information to display the form. """
           
        # must get most of the fields from the vlan table
        additionalSQL = ' AND prefix.vlanid=vlan.vlanid'

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table

            nettypes = [('static','static'),
                        ('reserved','reserved'),
                        ('scope','scope')]

            orgs = [('','No organisation')]
            for o in nav.db.manage.Org.getAllIterator(orderBy='orgid'):
                orgs.append((o.orgid,o.orgid + ' (' + str(o.descr) + ')'))

            usageids = [('','No usage')]
            for usage in manage.Usage.getAllIterator(orderBy='usageid'):
                usageids.append((usage.usageid,usage.usageid + ' (' + \
                                usage.descr + ')'))

            # Field definitions {field name: [input object, required]}
            f = {'netaddr': [inputText(),REQ_TRUE,'Prefix/mask (cidr)',
                             FIELD_STRING],
                 'vlan.nettype': [inputSelect(options=nettypes),REQ_TRUE,
                                  'Network type',FIELD_STRING],
                 'vlan.orgid': [inputSelect(options=orgs),REQ_NONEMPTY,
                                'Organisation',FIELD_STRING],
                 'vlan.netident': [inputText(),REQ_FALSE,'Netident',
                                   FIELD_STRING],
                 'vlan.description': [inputText(),REQ_FALSE,'Description',
                                      FIELD_STRING],
                 'vlan.vlan': [inputText(size=5),REQ_NONEMPTY,'Vlan',
                               FIELD_INTEGER],
                 'vlan.usageid': [inputSelect(options=usageids),REQ_NONEMPTY,
                                  'Usage',FIELD_STRING]}
                 
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill() 
            if formData:
                self.formFill(formData)

    def add(self,req,templateForm,action):
        """ Adds prefix entries. Overrides the default add function. """
        error = None
        status = editdbStatus()

        data = {'nettype': req.form['vlan.nettype'],
                'description': req.form['vlan.description'],
                'netaddr': req.form['netaddr'],
                'netident': req.form['vlan.netident'],
                'vlan': req.form['vlan.vlan']}

        if len(req.form['vlan.orgid']):
            data['orgid'] = req.form['vlan.orgid']
        if len(req.form['vlan.usageid']):
            data['usageid'] = req.form['vlan.usageid']

        error = self.insertPrefix(data)
        if not error:
            action = 'list'
            status.messages.append('Added prefix')
        else:
            action = 'add'
            status.errors.append(error)
        return (status,action,templateForm,None)

    def insertPrefix(self,data):
        """ Inserts prefixes into the database. Used by pagePrefix.add() """
        error = None

        # Add new vlan
        fields = {'nettype': data['nettype']}

        if data.has_key('orgid'):
            if len(data['orgid']):
                fields['orgid'] = data['orgid']
        if data.has_key('usageid'):
            if len(data['usageid']):
                fields['usageid'] = data['usageid']
        if len(data['description']):
            fields['description'] = data['description']
        if len(data['vlan']):
            fields['vlan'] = data['vlan']
        if len(data['netident']):
            fields['netident'] = data['netident']

        vlanid = addEntryFields(fields,
                                'vlan',
                                ('vlanid','vlan_vlanid_seq'))
        # Add new prefix
        fields = {'netaddr': data['netaddr'],
                  'vlanid': vlanid}
        try:
            addEntryFields(fields,'prefix')
        except psycopg.ProgrammingError:
            # Invalid cidr
            error = 'Invalid CIDR'
            # Remove vlan entry
            deleteEntry([vlanid],'vlan','vlanid')
        except psycopg.IntegrityError:
            # Already existing cidr
            error = 'Prefix already exists in database'
            deleteEntry([vlanid],'vlan','vlanid')
        return error

    def update(self,req,templateform,selected):
        """ Updates prefix entries. Overrides the default update function.  """
        error = None
        status = editdbStatus()
        formdata = {}
        idlist = []
        if type(req.form[UPDATE_ENTRY]) is list:
            # editing several entries
            for i in range(0,len(req.form[UPDATE_ENTRY])):
                entry = {}
                editid = req.form[UPDATE_ENTRY][i]
                idlist.append(editid)
                entry['netaddr'] = req.form['netaddr'][i]
                entry['description'] = req.form['vlan.description'][i]
                entry['netident'] = req.form['vlan.netident'][i]
                entry['orgid'] = req.form['vlan.orgid'][i]
                entry['usageid'] = req.form['vlan.usageid'][i]
                entry['nettype'] = req.form['vlan.nettype'][i]
                entry['vlan'] = req.form['vlan.vlan'][i]
                formdata[editid] = entry
        else:
            # editing just one entry
            entry = {}
            editid = req.form[UPDATE_ENTRY]
            idlist = [editid]
            entry['netaddr'] = req.form['netaddr']
            entry['description'] = req.form['vlan.description']
            entry['netident'] = req.form['vlan.netident']
            entry['orgid'] = req.form['vlan.orgid']
            entry['usageid'] = req.form['vlan.usageid']
            entry['nettype'] = req.form['vlan.nettype']
            entry['vlan'] = req.form['vlan.vlan']
            formdata[editid] = entry

        for updateid,data in formdata.items():
            vlanfields = {'description': data['description'],
                          'netident': data['netident'],
                          'nettype': data['nettype']}
            if len(data['orgid']):
                vlanfields['orgid'] = data['orgid']
            else:
                vlanfields['orgid'] = None
            if len(data['usageid']):
                vlanfields['usageid'] = data['usageid']
            else:
                vlanfields['usageid'] = None
            if len(data['vlan']):
                vlanfields['vlan'] = data['vlan']
            else:
                vlanfields['vlan'] = None

            prefixfields = {'netaddr': data['netaddr']}
          
            vlanid = manage.Prefix(updateid).vlan.vlanid 
            updateEntryFields(vlanfields,'vlan','vlanid',str(vlanid))
            updateEntryFields(prefixfields,'prefix','prefixid',updateid)

        selected = idlist
        action = 'list'
        if not error:
            action = 'list'
            status.messages.append('Updated prefix: ' + self.describe(updateid))
        else:
            action = 'edit'
            status.errors.append(error)
        return (status,action,templateform,selected)

class pageProduct(editdbPage):
    """ Describes editing of the product table. """
    
    basePath = BASEPATH + 'product/'
    table = nav.db.manage.Product
    pageName = 'product'
    tableName = 'product'
    tableIdKey = 'productid'
    sequence = 'product_productid_seq'
    editMultipleAllowed = True
    editIdAllowed = False

    # Description format used by describe(id)
    descriptionFormat = [('','vendor.vendorid'),
                         (', ','productno')]

    # Unique fields (for errormessages from add/update)
    unique = ['vendorid']

    # Nouns
    singular = 'product'
    plural = 'products'

    # Delete dependencies
    dependencies = []

    pathAdd = EDITPATH + [('Product',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Product',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Product',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Product',False)]

    class listDef(entryList):
        """ Describes product list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Vendor',True,None),
                                      ('Productno',True,None),
                                      ('Description',True,None)]

            self.cellDefinition = [(('productid,vendorid,productno,descr',
                                     'product',
                                     None,
                                     None,
                                     'vendorid,productno'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None),
                                     (3,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing product entries.
            The template uses this field information to display the form. """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            # Field definitions {field name: [input object, required]}
            f = {'vendorid': [inputSelect(table=editTables.editdbVendor),
                              REQ_TRUE,'Vendor',FIELD_STRING],
                 'productno': [inputText(),REQ_TRUE,'Productno',FIELD_STRING],
                 'descr': [inputText(),REQ_FALSE,'Description',FIELD_STRING]}

            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData)

class pageRic(editdbPage):
    """ Describes editing of routers in containers (vp_netbox_grp). """
    
    basePath = BASEPATH + 'ric/'
    table = nav.db.manage.Vp_netbox_grp
    pageName = 'ric'
    tableName = 'vp_netbox_grp'
    # Id is vp_netbox_grp_infoid and pnetboxid, but use pnetboxid
    # since it's easier and should be unique
    tableIdKey = 'pnetboxid'
    sequence = None
    editMultipleAllowed = False
    editIdAllowed = True

    # Description format used by describe(id)
    descriptionFormat = [(' in container',None)]

    # Unique fields (for errormessages from add/update)
    unique = ['vp_netbox_grp_infoid','pnetboxid']

    # Nouns
    singular = 'router in container'
    plural = 'routers in containers'

    # Delete dependencies
    dependencies = []

    ric = 'Routers in containers'
    pathAdd = EDITPATH + [(ric,basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [(ric,basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [(ric,basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [(ric,False)]

    class listDef(entryList):
        """ Describes product list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Container',True,None),
                                      ('Router',True,None)]

            self.cellDefinition = [(('vp_netbox_grp.pnetboxid,' +\
                                     'vp_netbox_grp_info.name,netbox.sysname',
                                     'vp_netbox_grp,vp_netbox_grp_info,netbox',
                                     None,
                                     'pnetboxid=netbox.netboxid AND ' +\
                                     'vp_netbox_grp.vp_netbox_grp_infoid=' +\
                                     'vp_netbox_grp_info.vp_netbox_grp_infoid',
                                     'vp_netbox_grp_info.name,netbox.sysname'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing routers to containers.
            The template uses this field information to display the form. """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            self.hiddenFields = {}

            # Make list of routers
            where = "AND ((SELECT count(*) FROM vp_netbox_grp WHERE " +\
                    "pnetboxid=netbox.netboxid) = 0)"
            selectedRouters = []
            disabled = False
            if editId:
                # editId given is netboxid, get containerid
                sql = "SELECT vp_netbox_grp_infoid FROM vp_netbox_grp " +\
                      "WHERE pnetboxid='" + editId + "'"
                result = executeSQLreturn(sql)
                containerId = str(result[0][0])
                # Doesn't call self.fill(), so set update attribs here
                self.boxName = UPDATE_ENTRY
                self.editId = editId
                self.boxId = self.editId
                # Disable container select
                disabled = True

                sql = "SELECT pnetboxid FROM vp_netbox_grp WHERE " +\
                      "vp_netbox_grp_infoid='" + containerId + "'"
                result = executeSQLreturn(sql)      
                for row in result:
                    selectedRouters.append(str(row[0]))

                # If we're editing, include routers already in container
                where = "AND (((SELECT count(*) FROM vp_netbox_grp WHERE " +\
                        "pnetboxid=netbox.netboxid) = 0) OR ((SELECT " +\
                        "count(*) FROM vp_netbox_grp WHERE " +\
                        "vp_netbox_grp_infoid='" + containerId +\
                        "' AND pnetboxid=netboxid) = 1))"
               
            select1 = simpleSelect('Routers',
                                   'cn_routers',
                                   ('netboxid,sysname',
                                    'netbox',
                                    None,
                                    "(catid='GSW' OR catid='GW') " + where,
                                    'sysname'),
                                    selectedRouters,
                                    optionFormat='$2',
                                    setOnChange=False,
                                    selectMultiple=True,
                                    multipleHeight=8)

            st = selectTree()
            st.addSelect(select1)
            lb = None
            if req:
                st.update(req.form)
                lb = selectTreeLayoutBox(showEmptySelects=True,
                                         showTitles=False)
                lb.addSelect(select1)

            # Make list of containers
            containers = [('','Select a container')]
            cs = nav.db.manage.Vp_netbox_grp_info.getAll(orderBy='name')
            for c in cs:
                containers.append((str(c.vp_netbox_grp_infoid),c.name))
            # Field definitions {field name: [input object, required]}
            f = {'container': [inputSelect(options=containers,
                                           disabled=disabled),
                              REQ_TRUE,'Container',FIELD_STRING],
                 'routers': [inputTreeSelect(treeselect=lb),REQ_TRUE,
                             'Routers',FIELD_STRING]}

            self.fields = f
            self.setControlNames()

            if editId:
                # Set container value (routers list set by selectTree)
                self.fields['container'][0].value = containerId
            if disabled:
                self.addDisabled()

    def add(self,req,templateForm,action):
            """ Adds routers in containers. Overrides the default add 
                function. """
            error = None
            status = editdbStatus()

            containerId = req.form['container']
            routerList = req.form['cn_routers']
            if not type(routerList) is list:
                routerList = [routerList]
                
            for netboxId in routerList:
                fields = {'vp_netbox_grp_infoid': containerId,
                          'pnetboxid': netboxId}
                try:
                    addEntryFields(fields,self.tableName)
                except psycopg.ProgrammingError:
                    # This router already added to this container
                    routerList.remove(netboxId)

            action = 'list'
            cntname = nav.db.manage.Vp_netbox_grp_info(containerId).name
            for netboxId in routerList:
                sysname = nav.db.manage.Netbox(netboxId).sysname
                message = "Added router '" + sysname + "' to container '" +\
                          cntname + "'"
                status.messages.append(message)
            return (status,action,templateForm,None)

    def update(self,req,templateForm,selected):
        """ Updates routers in containers. Overrides the default update 
            function in editdbPage """

        action = 'list'
        status = editdbStatus()
        editId = req.form[UPDATE_ENTRY]

        routerList = req.form['cn_routers']
        if not type(routerList) is list:
            routerList = [routerList]
       
        # editId given is netboxid, get containerid
        sql = "SELECT vp_netbox_grp_infoid FROM vp_netbox_grp " +\
              "WHERE pnetboxid='" + editId + "'"
        result = executeSQLreturn(sql)
        containerId = str(result[0][0])

        # Remove all routers from container
        sql = "DELETE FROM vp_netbox_grp WHERE vp_netbox_grp_infoid='" +\
             containerId + "'"
        executeSQL([sql])

        # Add selected routers to container
        for netboxId in routerList:
            fields = {'vp_netbox_grp_infoid':  containerId,
                      'pnetboxid': netboxId}
            addEntryFields(fields,self.tableName)

        selected = [editId]
        status.messages.append('Updated container')
        return (status,action,templateForm,selected)


class pageRoom(editdbPage):
    """ Describes editing of the room table. """
    
    basePath = BASEPATH + 'room/'
    table = nav.db.manage.Room
    pageName = 'room'
    tableName = 'room'
    tableIdKey = 'roomid'
    sequence = None
    editMultipleAllowed = True
    editIdAllowed = False

    # Description format used by describe(id)
    # Example: room 021 (descr) to jack 123, building, office
    # BUG: roomid.roomid should only have to be roomid
    #      can't find any error in describe()
    descriptionFormat = [('','roomid.roomid')]

    # Unique fields (for errormessages from add/update)
    unique = 'roomid'

    # Nouns
    singular = 'room'
    plural = 'rooms'

    # Delete dependencies
    dependencies = [(nav.db.manage.Netbox,
                     'boxes',
                     'roomid',
                     '/report/netbox/?roomid=')]

    pathAdd = EDITPATH + [('Room',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Room',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Room',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Room',False)]

    class listDef(entryList):
        """ Describes room list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Room Id',True,None),
                                      ('Location',True,None),
                                      ('Description',True,None),
                                      ('Optional 1',True,None),
                                      ('Optional 2',True,None),
                                      ('Optional 3',True,None),
                                      ('Optional 4',True,None)]

            self.cellDefinition = [(('roomid,roomid,locationid,descr,' +\
                                     'opt1,opt2,opt3,opt4',
                                     'room',
                                     None,
                                     None,
                                     'roomid,locationid'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None),
                                     (3,None,None,None,None),
                                     (4,None,None,None,None),
                                     (5,None,None,None,None),
                                     (6,None,None,None,None),
                                     (7,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing room entries.
            The template uses this field information to display the form. """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            self.hiddenFields = {}

            disabled = False
            if editId:
                disabled = True

            locations = [('','Select a location')]
            for l in nav.db.manage.Location.getAllIterator(
                                            orderBy='locationid'):
                locations.append((l.locationid,l.locationid + ' (' +
                                  l.descr + ')'))

            f = {'roomid': [inputText(disabled=disabled,maxlength=30),
                            REQ_TRUE,'Room Id',FIELD_STRING],
                 'locationid': [inputSelect(options=locations),
                                REQ_TRUE,'Location',FIELD_STRING],
                 'descr': [inputText(),REQ_FALSE,'Description',FIELD_STRING],
                 'opt1': [inputText(),REQ_FALSE,'Optional 1',FIELD_STRING],
                 'opt2': [inputText(),REQ_FALSE,'Optional 2',FIELD_STRING],
                 'opt3': [inputText(),REQ_FALSE,'Optional 3',FIELD_STRING],
                 'opt4': [inputText(),REQ_FALSE,'Optional 4',FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()
            
            if formData:
                self.formFill(formData)

            if disabled:
                self.addDisabled()

class pageService(editdbPage):
    """ Describes editing of the service table. """
    
    basePath = BASEPATH + 'service/'
    table = nav.db.manage.Service
    pageName = 'service'
    tableName = 'service'
    tableIdKey = 'serviceid'
    sequence = 'service_serviceid_seq'
    editMultipleAllowed = False
    editIdAllowed = False

    # Description format used by describe(id)
    # Example: room 021 (descr) to jack 123, building, office
    descriptionFormat = [('','handler'),
                         (' on ','netbox.sysname')]

    # Unique fields (for errormessages from add/update)
    unique = ''

    # Nouns
    singular = 'service'
    plural = 'services'

    # Delete dependencies
    dependencies = []

    pathAdd = EDITPATH + [('Service',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Service',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Service',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Service',False)]

    class listDef(entryList):
        """ Describes service list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Server',True,None),
                                      ('Handler',True,None),
                                      ('Version',True,None)]

            self.cellDefinition = [(('serviceid,netbox.sysname,handler,version',
                                     'service,netbox',
                                     None,
                                     'service.netboxid=netbox.netboxid',
                                     'netbox.sysname,handler'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None),
                                     (3,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing service entries.
            The template uses this field information to display the form. """

        def __init__(self,page,req=None,editId=None,formData=None,
                     disabled=False):
           
            self.page = page.pageName
            self.table = page.table
            self.hiddenFields = {}
            self.editId = editId
            self.help = ''
            form = {}
            if req:
                form = req.form
           
            propertyListFilled = []
            handlerEntries = []
            presentHandlers = []
            if editId:
                # Make editbox for editing properties (not for adding services)
                self.help = 'Edit service properties for services on this ' +\
                            'IP device'

                # Set the name of this boxname to reflect that we are
                # updating an entry
                self.boxName = UPDATE_ENTRY
                self.boxId = editId

                # editId is serviceid, get netboxid
                boxid = str(nav.db.manage.Service(editId).netbox.netboxid)
                sql = "SELECT serviceid FROM service WHERE netboxid='" +\
                       boxid + "' ORDER BY handler"

                result = executeSQLreturn(sql)
                serviceIdList = []
                if result:
                    for row in result:
                        serviceIdList.append(str(row[0]))
               
                for serviceId in serviceIdList:        
                    handler = nav.db.manage.Service(serviceId).handler
                    presentHandlers.append(handler)
                    handlerId = handler + '_' + serviceId
                    handlerName = handler
                    if presentHandlers.count(handler) > 0:
                        handlerName = handler + ' (' +\
                                      str(presentHandlers.count(handler)) + ')'
                    handlerEntries.append((handlerId,handlerName,True))
                    sql = "SELECT * FROM serviceproperty WHERE " + \
                          "serviceid='" + serviceId + "'"
                    result = executeSQLreturn(sql)
                    propertyValues = {}
                    for entry in result:
                        property = entry[1]
                        value = entry[2]
                        propertyValues[property] = value

                    prop = self.makePropertyInput(handler,propertyValues,
                                                  serviceId=serviceId)
                    if prop:
                        propertyListFilled.append(prop)
                # Preselected values
                catid = nav.db.manage.Netbox(boxid).cat.catid
                preSelectedCatid = [catid]
                preSelectedBoxid = [boxid]
                catidDisabled = True
                boxidDisabled = True
            else:
                self.help = 'Select an IP device and one or more service ' +\
                            'handlers'
                preSelectedCatid = []
                preSelectedBoxid = []
                catidDisabled = False
                boxidDisabled = False

            lb = None
            lb2 = None
            if req:
                # Catid select
                select1 = simpleSelect('Category',
                                       'cn_catid',
                                       ('catid,descr',
                                        'cat',
                                        None,
                                        None,
                                        'catid'),
                                        preSelectedCatid,
                                        optionFormat='$1',
                                        selectMultiple=False,
                                        multipleHeight=8,
                                        disabled=catidDisabled)

                # Ip device select
                select2 = updateSelect(select1,
                                       'catid',
                                       'IP device',
                                       'boxid',
                                       ('netboxid,sysname',
                                        'netbox',
                                        None,
                                        None,
                                        'sysname'),
                                        preSelectedBoxid,
                                        optionFormat='$2',
                                        actionOnChange="toggleDisabled" +\
                                                       "(this,'handler');",
                                        selectMultiple=False,
                                        multipleHeight=8,
                                        disabled=boxidDisabled)

                # Handler select
                # Get checkers (handler names)
                for c in getCheckers():
                    presentHandlers.append(c)
                    handlerName = c
                    if presentHandlers.count(c) > 1:
                        handlerName = c + ' (' + str(presentHandlers.count(c))+\
                                      ')'
                    handlerEntries.append((c,handlerName,False))

                handlerEntries.sort()

                handlerDisabled = True
                if req.form.has_key('boxid') or editId:
                    handlerDisabled = False
                select3 = simpleSelect('Handler',
                                       'handler',
                                       None,
                                       addEntryList=handlerEntries,
                                       actionOnChange="updateDisplay" +\
                                                      "(this);",
                                       selectMultiple=True,
                                       multipleHeight=8,
                                       disabled=handlerDisabled)

                st = selectTree()
                st.addSelect(select1)
                st.addSelect(select2)
                st.update(req.form)

                st2 = selectTree()
                st2.addSelect(select3)
                st2.update(req.form)

                lb = selectTreeLayoutBox(showTitles=False)
                lb.addSelect(select1)
                lb.addSelect(select2)

                lb2 = selectTreeLayoutBox(showEmptySelects=True,
                                          showTitles=False)
                lb2.addSelect(select3)

            # Make all the serviceproperty boxes (they are hidden until
            # displayed by javascript)
            # Remember selected boxes
            selectedHandlers = []
            if form.has_key('handler'):
                selectedHandlers = form['handler']
            if not type(selectedHandlers) is list:
                selectedHandlers = [selectedHandlers]
            
            propertyList = []
            for checker in getCheckers():
                prop = self.makePropertyInput(checker,form,selectedHandlers)
                if prop:
                    propertyList.append(prop)
            propertyList = propertyListFilled + propertyList

            f = {'boxid': [inputTreeSelect(treeselect=lb),
                           REQ_TRUE,'IP device',FIELD_STRING],
                 'handler': [inputTreeSelect(treeselect=lb2),
                            REQ_TRUE,'Handler',FIELD_STRING],
                 'properties': [inputServiceProperties(propertyList),
                                REQ_FALSE,'Properties',FIELD_STRING]}

            self.fields = f
            self.setControlNames()

        def makePropertyInput(self,handler,form,selectedHandlers=None,
                              serviceId=None):
            """ Used by init to make property inputs
                handler = handler/checker name (string)
                form    = form/value (dict)
                selectedHandler = list of handlers already selected in add 
                serviceId = fill fields with this service """
            properties = getDescription(handler)
            propertyInput = None

            args = {}
            optargs = {}
            if properties:
                title = "Properties for " + handler + ' (' +\
                        properties['description']+ ')'

                if properties.has_key('args'):
                    i = 0
                    for a in properties['args']:
                        textInput = inputText()
                        if serviceId:
                            name = handler + '_' + serviceId + '_' + str(i)
                        else:
                            name = handler + '_' + str(i)
                        textInput.name = name
                        if form.has_key(name):
                            textInput.value = form[name]
                        elif form.has_key(a):
                            # When editing, form is replaced by
                            # propertyValues which is a dict with
                            # the real propertyy names (not the form names)
                            textInput.value = form[a]
                        args[a] = [textInput,REQ_TRUE]
                        i += 1
                if properties.has_key('optargs'):
                    i = 0
                    for a in properties['optargs']:
                        textInput = inputText()
                        if serviceId:
                            name = handler + '_' + serviceId + '_opt_' + str(i)
                        else:
                            name = handler + '_opt_' + str(i)
                        textInput.name = name
                        if form.has_key(name):
                            textInput.value = form[name]
                        elif form.has_key(a):
                            textInput.value = form[a]
                        optargs[a] = [textInput,REQ_FALSE]
                        i += 1
                if len(args) or len(optargs):
                    if serviceId:
                        id = handler + '_' + serviceId
                    else:
                        id = handler
                    if type(selectedHandlers) is list:
                        if (id in selectedHandlers):
                            # This property was already selected, so show
                            # the property box
                            display = True
                        else:
                            display = False
                    else:
                        # No list of selected handlers given
                        # (for making edit page)
                        display = True
                    propertyInput = inputServiceProperty(title,id,args,optargs,
                                                         display)
                return propertyInput
   
    def checkRequiredProperties(self,handler,form,serviceId=None):
        """ Check if all the required properties of handler is present
            in the form data. 
            handler = handler/checker name (string)
            form = form data dict
            serviceId = id to append to field names if we're editing (string)"""
        properties = getDescription(handler)
        if properties:
            if properties.has_key('args'):
                i = 0
                for arg in properties['args']:
                    if serviceId:
                        requiredArg = handler + '_' + serviceId + '_' + str(i) 
                    else:
                        requiredArg = handler + '_' + str(i)
                    missing = False
                    if not form.has_key(requiredArg):
                        missing = True
                    else:
                        if not len(form[requiredArg]):
                            missing = True
                    if missing:
                        raise("Missing required field '" + arg + "'" +\
                              " for handler " + handler) 
                    i += 1
    
    def insertProperties(self,handler,form,serviceId,editing=False):
        """ Insert service properties for a serviceId from form data.
            handler   = service handler (string)
            form      = form data (dict)
            serviceId = service id the properties belong to (string)
            editing   = if we're editing then add serviceId to field names """
        properties = getDescription(handler)
        if properties:
            if properties.has_key('args'):
                i = 0
                for property in properties['args']:
                    # Already know that all properties in 'args'
                    # are present
                    if editing:
                        propertyName = handler + '_' + serviceId + '_' + str(i)
                    else:
                        propertyName = handler + '_' + str(i)
                    fields = {'serviceid': serviceId,
                              'property': property,
                              'value': form[propertyName]}
                    addEntryFields(fields,
                                   'serviceproperty')
                    i += 1
            if properties.has_key('optargs'):
                i = 0
                for property in properties['optargs']:
                    # optargs are optional, must 
                    # check if they are present
                    if editing:
                        propertyName = handler + '_' + serviceId + '_opt_' +\
                                       str(i)
                    else:
                        propertyName = handler + '_opt_' + str(i)
                    if form.has_key(propertyName):
                        if len(form[propertyName]):
                            fields = {'serviceid': serviceId,
                                      'property': property,
                                      'value': form[propertyName]}
                            addEntryFields(fields,
                                           'serviceproperty')
                    i += 1

    def add(self,req,templateForm,action):
        """ Adds a service entry. Overrides the default add function of
            editdbPage. """

        action = 'add'
        status = editdbStatus()

        form = req.form
        try:
            if not form.has_key('boxid'):
                raise("Missing required field 'IP device'")
            if not form.has_key('handler'):
                raise("Missing required field 'handler'")
            # Make list of selected handlers
            selectedHandlers = form['handler']
            if not type(selectedHandlers) is list:
                selectedHandlers = [selectedHandlers]
            # Check if all required properties are present
            for handler in selectedHandlers:
                self.checkRequiredProperties(handler,form)
            # Add new services
            for handler in selectedHandlers:
                # Add service entry
                fields = {'netboxid': form['boxid'],
                          'handler': handler}
                serviceId = addEntryFields(fields,self.tableName,
                                          (self.tableIdKey,self.sequence))
                # Add serviceproperty entries
                self.insertProperties(handler,form,serviceId)
                action = 'list'
                status.messages.append('Added service: ' +\
                                       self.describe(serviceId))
        except:
            status.errors.append(str(sys.exc_info()[0]))
        return (status,action,templateForm,None)

    def update(self,req,templateForm,selected):
        """ Updates service entries. Overrides the default update function
            in editdbPage """

        action = 'edit'
        status = editdbStatus()
        editId = selected[0]
        form = req.form

        # Get selected handlers
        selectedHandlers = []
        if form.has_key('handler'):
            if len(form['handler']):
                selectedHandlers = form['handler']
        if not type(selectedHandlers) is list:
            selectedHandlers = [selectedHandlers]

        try:
            # editId is serviceid, get netboxid
            boxid = str(nav.db.manage.Service(editId).netbox.netboxid)
            sql = "SELECT serviceid FROM service WHERE netboxid='" +\
                   boxid + "' ORDER BY handler"

            result = executeSQLreturn(sql)
            # get all serviceid's for this netbox
            serviceIdList = []
            if result:
                for row in result:
                    serviceIdList.append(str(row[0]))
          
            stillSelectedHandlers = []
            deselectedHandlers = []
            currentHandlerIds = []
            for serviceId in serviceIdList: 
                handler = nav.db.manage.Service(serviceId).handler
                handlerId = handler + '_' + serviceId
                currentHandlerIds.append(handlerId)
                
                if handlerId in selectedHandlers:
                    stillSelectedHandlers.append(serviceId)
                else:
                    deselectedHandlers.append(serviceId)

                addHandlers = []
                for handlerId in selectedHandlers:
                    # Remove selected handlers which were already present
                    # when starting editing. selectedHandlers should contain
                    # only new handlers for adding after this
                    if not (handlerId in currentHandlerIds):
                        addHandlers.append(handlerId)
             
            # Check for all required properties for old services
            for serviceId in stillSelectedHandlers:
                handler = nav.db.manage.Service(serviceId).handler
                self.checkRequiredProperties(handler,form,serviceId)  

            # Check for all required properties for new services
            for handler in addHandlers:
                self.checkRequiredProperties(handler,form)

            # Update properties for old services
            for serviceId in stillSelectedHandlers:
                # Delete all old serviceproperties for this serviceId,
                handler = nav.db.manage.Service(serviceId).handler
                sql = "DELETE FROM serviceproperty WHERE serviceid='" +\
                      serviceId + "'"
                executeSQL([sql])
                # Insert new serviceproperties
                self.insertProperties(handler,form,serviceId,editing=True)
                status.messages.append('Updated service: ' +\
                                       self.describe(serviceId))

            # Add new services
            for handler in addHandlers:
                fields = {'netboxid': boxid,
                          'handler': handler}
                serviceId = addEntryFields(fields,self.tableName,
                                          (self.tableIdKey,self.sequence))
                # Add serviceproperty entries
                self.insertProperties(handler,form,serviceId)
                status.messages.append('Added service: ' +\
                                       self.describe(serviceId))

            # Delete deselected services
            for serviceId in deselectedHandlers:
                status.messages.append('Deleted service: ' +\
                                       self.describe(serviceId))
                sql = "DELETE FROM service WHERE serviceid='" + serviceId + "'"
                executeSQL([sql])

            action = 'list'
        except:
            status.errors.append(str(sys.exc_info()[0]))
        return (status,action,templateForm,selected)


    def updateOLD(self):
        action = 'edit'
        status = editdbStatus()
        editId = req.form[UPDATE_ENTRY]
        # Check if all required serviceproperties are present
        handler = nav.db.manage.Service(editId).handler
        properties = getDescription(handler)
        missing = False
        propertyStep = False

        if properties:
            if properties.has_key('args'):
                for required in properties['args']:
                    if not req.form.has_key(required):
                        propertyStep = True
                    if req.form.has_key(required):
                        if not len(req.form[required]):
                            missing = required
                            propertyStep = True
            if properties.has_key('optargs'):
                for optional in properties['optargs']:
                    if not req.form.has_key(optional):
                        # If optargs are missing, then we haven't reached
                        # the add property step yet
                        propertyStep = True

        if propertyStep or (missing and len(req.form['netboxid'])):
            if missing:
                # Missing required property
                status.errors.append("Missing required property '" +\
                                     missing + "'")

            checker = handler
            templateForm.title = 'Edit service'
            templateForm.add(self.editbox(self,formData=req.form,
                                          editId=selected[0],disabled=True))
            templateForm.add(self.editboxServiceProperties(checker,
                                                    req.form['netboxid'],
                                                    editId=selected[0]))
            action = 'continueEdit'
        elif not missing:
            # Update service entry
            fields = {'netboxid': req.form['netboxid'],
                      'handler': handler}
            updateEntryFields(fields,'service','serviceid',editId)
            # Update serviceproperty entries
            if properties:
                # Delete old properties
                deleteEntry([editId],'serviceproperty','serviceid')
                if properties.has_key('args'):
                    for property in properties['args']:
                        # Already know that all properties in 'args' are present
                        fields = {'serviceid': editId,
                                  'property': property,
                                  'value': req.form[property]}
                        addEntryFields(fields,'serviceproperty')
                        action = 'list'
                if properties.has_key('optargs'):
                    for property in properties['optargs']:
                        # optargs are optional, must check if they are present
                        if req.form.has_key(property):
                            if len(req.form[property]):
                                fields = {'serviceid': editId,
                                          'property': property,
                                          'value': req.form[property]}
                                addEntryFields(fields,'serviceproperty')
                                action = 'list'
        else:
            status.errors.append("Missing required property '" + missing+"'")
            action = 'list'
        selected = [editId]
        return (status,action,templateForm,selected)

class pageSnmpoid(editdbPage):
    """ Describes adding to the snmpoid table. """
    
    basePath = BASEPATH + 'snmpoid/'
    table = nav.db.manage.Snmpoid
    pageName = 'snmpoid'
    tableName = 'snmpoid'
    tableIdKey = 'snmpoidid'
    sequence = 'snmpoid_snmpoidid_seq'
    editMultipleAllowed = False
    editIdAllowed = False

    # Description format used by describe(id)
    descriptionFormat = [('','snmpoid')]

    # Unique fields (for errormessages from add/update)
    unique = 'oidkey'

    # Nouns
    singular = 'snmpoid'
    plural = 'snmpoids'

    # Delete dependencies
    # delete not allowed for snmpoid, so no dependencies

    pathAdd = EDITPATH + [('Snmpoid',False),('Add',False)]

    class listDef(entryList):
        """ Dummy class. No list view defined for for the snmpoid page. """
        pass

    class editbox(editbox):
        """ Describes fields for adding snmpoid entries.
            The template uses this field information to display the form. """
           
        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table

            self.hiddenFields = {}

            disabled = False
            if editId:
                disabled = True

            f = {'oidkey': [inputText(disabled=disabled),REQ_TRUE,'OID key',
                            FIELD_STRING],
                 'snmpoid': [inputText(),REQ_TRUE,'Snmpoid',FIELD_STRING],
                 'descr': [inputText(),REQ_FALSE,'Description',FIELD_STRING],
                 'oidsource': [inputText(),REQ_FALSE,'OID source',FIELD_STRING],
                 'match_regex': [inputText(),REQ_FALSE,'Match regexp',
                                 FIELD_STRING],
                 'oidname': [inputText(),REQ_FALSE,'OID name',FIELD_STRING],
                 'mib': [inputText(),REQ_FALSE,'MIB',FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()
            if formData:
                self.formFill(formData)
            if disabled:
                self.addDisabled()


    def add(self,req,outputForm,action):
        """ Dummy function which calls editdbPage.add and then sets action
            to redirect (to the menu page). """

        status,action,outputForm,addedId = editdbPage.add(self,req,
                                                          outputForm,action)
        action = 'redirect'

        return (status,action,outputForm,addedId)

class pageSubcat(editdbPage):
    """ Describes editing of the subcat table. """
    
    basePath = BASEPATH + 'subcat/'
    table = nav.db.manage.Subcat
    pageName = 'subcat'
    tableName = 'subcat'
    tableIdKey = 'subcatid'
    sequence = None
    editMultipleAllowed = True
    editIdAllowed = True

    # Description format used by describe(id)
    descriptionFormat = [('','subcatid'),
                         (' (','descr'),
                         (')',None)]

    # Unique fields (for errormessages from add/update)
    unique = 'subcatid'

    # Nouns
    singular = 'subcategory'
    plural = 'subcategories'

    # Delete dependencies
    dependencies = []

    pathAdd = EDITPATH + [('Subcategory',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Subcategory',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Subcategory',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Subcategory',False)]

    class listDef(entryList):
        """ Describes subcat list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Subcategory',True,None),
                                      ('Parent category',True,None),
                                      ('Description',True,None)]

            self.cellDefinition = [(('subcatid,subcatid,catid,descr',
                                     'subcat',
                                     None,
                                     None,
                                     'catid,subcatid'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None),
                                     (3,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing patch entries.
            The template uses this field information to display the form. """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            
            o = [('','Select a category')]
            for cat in nav.db.manage.Cat.getAllIterator():
                o.append((cat.catid,cat.catid + ' (' + cat.descr + ')'))

            f = {'subcatid': [inputText(),REQ_TRUE,'Subcategory',FIELD_STRING],
                 'catid': [inputSelect(options=o),REQ_TRUE,'Category',
                           FIELD_STRING],
                 'descr': [inputText(),REQ_TRUE,'Description',FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData) 

class pageType(editdbPage):
    """ Describes editing of the type table. """
    
    basePath = BASEPATH + 'type/'
    table = nav.db.manage.Type
    pageName = 'type'
    tableName = 'type'
    tableIdKey = 'typeid'
    sequence = 'type_typeid_seq' 
    editMultipleAllowed = True
    editIdAllowed = False

    # Description format used by describe(id)
    descriptionFormat = [('','vendor.vendorid'),
                         (' ','typename')]

    # Unique fields (for errormessages from add/update)
    unique = 'sysobjectid'

    # Nouns
    singular = 'type'
    plural = 'types'

    # Delete dependencies
    dependencies = []

    pathAdd = EDITPATH + [('Type',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Type',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Type',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Type',False)]

    class listDef(entryList):
        """ Describes room list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Vendor',True,None),
                                      ('Typename',True,None),
                                      ('Description',True,None),
                                      ('Sysobjectid',True,None),
                                      ('Frequency',True,None),
                                      ('cdp',True,None),
                                      ('tftp',True,None)]

            self.cellDefinition = [(('typeid,vendorid,typename,descr,' +\
                                     'sysobjectid,frequency,' +\
                                     'CASE WHEN cdp THEN \'yes\' ' +\
                                     'ELSE \'no\' END,' +\
                                     'CASE WHEN tftp THEN \'yes\' ' +\
                                     'ELSE \'no\' END',
                                     'type',
                                     None,
                                     None,
                                     'vendorid,typename'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,None,None,None,None),
                                     (2,'{p}edit/{id}',None,None,None),
                                     (3,None,None,None,None),
                                     (4,None,None,None,None),
                                     (5,None,None,None,None),
                                     (6,None,None,None,None),
                                     (7,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing type entries.
            The template uses this field information to display the form. """
 
        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            # Field definitions {field name: [input object, required]}
            f = {'typename': [inputText(),REQ_TRUE,'Typename',FIELD_STRING],
                 'vendorid': [inputSelect(table=editTables.editdbVendor),
                              REQ_TRUE,'Vendor',FIELD_STRING],
                 'descr': [inputText(),REQ_TRUE,'Description',FIELD_STRING],
                 'sysobjectid': [inputText(),REQ_TRUE,'Sysobjectid',
                                 FIELD_STRING],
                 'cdp': [inputCheckbox(),REQ_NONEMPTY,'cdp',FIELD_STRING],
                 'tftp': [inputCheckbox(),REQ_NONEMPTY,'tftp',FIELD_STRING],
                 'frequency': [inputText(),REQ_NONEMPTY,'frequency',
                               FIELD_INTEGER]}

            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData)


class pageUsage(editdbPage):
    """ Describes editing of the usage table. """
    
    basePath = BASEPATH + 'usage/'
    table = nav.db.manage.Usage
    pageName = 'usage'
    tableName = 'usage'
    tableIdKey = 'usageid'
    sequence = None
    editMultipleAllowed = True
    editIdAllowed = True

    # Description format used by describe(id)
    descriptionFormat = [('','usageid'),
                         (' (','descr'),
                         (')',None)]

    # Unique fields (for errormessages from add/update)
    unique = 'usageid'

    # Nouns
    singular = 'usage category'
    plural = 'usage categories'

    # Delete dependencies
    dependencies = []

    pathAdd = EDITPATH + [('Usage',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Usage',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Usage',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Usage',False)]

    class listDef(entryList):
        """ Describes usage list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Usage category',True,None),
                                      ('Description',True,None)]

            self.cellDefinition = [(('usageid,usageid,descr',
                                     'usage',
                                     None,
                                     None,
                                     'usageid'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing patch entries.
            The template uses this field information to display the form. """
           
        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            # Field definitions {field name: [input object, required]}
            f = {'usageid': [inputText(maxlength=30),REQ_TRUE,
                             'Usage category',FIELD_STRING],
                 'descr': [inputText(),REQ_TRUE,'Description',FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData)

class pageVendor(editdbPage):
    """ Describes editing of the vendor table. """
    
    basePath = BASEPATH + 'vendor/'
    table = nav.db.manage.Vendor
    pageName = 'vendor'
    tableName = 'vendor'
    tableIdKey = 'vendorid'
    sequence = None
    editMultipleAllowed = True
    editIdAllowed = True

    # Description format used by describe(id)
    descriptionFormat = [('','vendorid')]

    # Unique fields (for errormessages from add/update)
    unique = 'vendorid'

    # Nouns
    singular = 'vendor'
    plural = 'vendors'

    # Delete dependencies
    dependencies = [(nav.db.manage.Type,
                    'types',
                    'vendorid',
                    '/report/type/?vendorid='),
                    (nav.db.manage.Product,
                    'products',
                    'vendorid',
                    '/report/product/?vendorid=')]

    pathAdd = EDITPATH + [('Vendor',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Vendor',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Vendor',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Vendor',False)]

    class listDef(entryList):
        """ Describes vendor list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Vendor',True,None)]

            self.cellDefinition = [(('vendorid,vendorid',
                                     'vendor',
                                     None,
                                     None,
                                     'vendorid'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing vendor entries.
            The template uses this field information to display the form. """
    
        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            # Field definitions {field name: [input object, required]}
            f = {'vendorid': [inputText(maxlength=15),REQ_TRUE,'Vendor',
                              FIELD_STRING]}
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill()

            if formData:
                self.formFill(formData)

class pageVlan(editdbPage):
    """ Describes editing of the vlan table (no adding or 
        deleting allowed). """
    
    basePath = BASEPATH + 'vlan/'
    table = nav.db.manage.Vlan
    pageName = 'vlan'
    tableName = 'vlan'
    tableIdKey = 'vlanid'
    sequence = 'vlan_vlanid_seq'
    editMultipleAllowed = True
    editIdAllowed = False

    # Disallow adding
    disallowAdd = True
    disallowAddReason = 'Cannot add vlans manually'

    # Description format used by describe(id)
    descriptionFormat = [('','nettype'),
                         (' ','vlan')]

    # Unique fields (for errormessages from add/update)
    unique = ''

    # Nouns
    singular = 'vlan'
    plural = 'vlans'

    # Delete dependencies
    dependencies = []

    pathAdd = EDITPATH + [('Vlan',basePath+'list'),('Add',False)]
    pathEdit = EDITPATH + [('Vlan',basePath+'list'),('Edit',False)]
    pathDelete = EDITPATH + [('Vlan',basePath+'list'),('Delete',False)]
    pathList = EDITPATH + [('Vlan',False)]

    class listDef(entryList):
        """ Describes vlan list view """
        def __init__(self,req,struct,sort,deleteWhere=None):
            # Do general init
            entryList.__init__(self,req,struct,sort,deleteWhere)
            
            # Specific init
            self.defaultSortBy = 1

            # list of (heading text, show sortlink, compare function for sort)
            self.headingDefinition = [('Select',False,None),
                                      ('Vlan',True,None),
                                      ('Nettype',True,None),
                                      ('Organisation',True,None),
                                      ('Usage',True,None),
                                      ('Netident',True,None),
                                      ('Description',True,None),
                                      ('Prefixes',False,None)]

            prefixSQL = "SELECT netaddr FROM prefix WHERE VLANID={id}"
            self.cellDefinition = [(('vlanid,vlan,nettype,orgid,usageid,' +\
                                     'netident,description',
                                     'vlan',
                                     None,
                                     None,
                                     'vlan,nettype,orgid'),
                                    [(None,None,entryListCell.CHECKBOX,None,None),
                                     (1,'{p}edit/{id}',None,None,None),
                                     (2,'{p}edit/{id}',None,None,None),
                                     (3,None,None,None,None),
                                     (4,None,None,None,None),
                                     (5,None,None,None,None),
                                     (6,None,None,None,None),
                                     (prefixSQL,None,None,None,None)])]

    class editbox(editbox):
        """ Describes fields for adding and editing vlan entries.
            The template uses this field information to display the form. """

        def __init__(self,page,req=None,editId=None,formData=None):
            self.page = page.pageName
            self.table = page.table
            # Available nettypes (should be in the database)
            nettypes = [('core','core'),
                        ('elink','elink'),
                        ('lan','lan'),
                        ('link','link'),
                        ('loopback','loopback'),
                        ('private','private')]

            orgs = [('','No organisation')]
            for o in nav.db.manage.Org.getAllIterator():
                orgs.append((o.orgid,o.orgid + ' (' + str(o.descr) + ')'))

            usageids = [('','No usage')]
            for usage in nav.db.manage.Usage.getAllIterator():
                usageids.append((usage.usageid,usage.usageid + ' (' + \
                                usage.descr + ')'))

            # Field definitions {field name: [input object, required]}
            f = {'nettype': [inputSelect(options=nettypes),REQ_TRUE,
                             'Nettype',FIELD_STRING],
                 'orgid': [inputSelect(options=orgs),REQ_FALSE,
                           'Organisation',FIELD_STRING],
                 'netident': [inputText(),REQ_FALSE,'Netident',FIELD_STRING],
                 'description': [inputText(),REQ_FALSE,'Description',
                                 FIELD_STRING],
                 'vlan': [inputText(size=5),REQ_FALSE,'Vlan',FIELD_INTEGER],
                 'usageid': [inputSelect(options=usageids),REQ_FALSE,
                             'Usage',FIELD_STRING]}
                 
            self.fields = f
            self.setControlNames()

            if editId:
                self.editId = editId
                self.fill() 
            if formData:
                self.formFill(formData)

# List of editdb pages
pageList = {'cabling': pageCabling,
            'container': pageContainer,
            'location': pageLocation,
            'netbox': pageNetbox,
            'org': pageOrg,
            'patch': pagePatch,
            'prefix': pagePrefix,
            'product': pageProduct,
            'ric': pageRic,
            'room': pageRoom,
            'service': pageService,
            'snmpoid': pageSnmpoid,
            'subcat': pageSubcat,
            'type': pageType,
            'usage': pageUsage,
            'vendor': pageVendor,
            'vlan': pageVlan}

######################
##
## Bulk import classes
##
########################


class editboxBulk(editbox):
    """ Editbox used by the template to disaply the main bulk import page. """

    page = 'bulk'

    help = 'Import multiple entries by selecting a file, or pasting ' +\
           'into the textarea. Select an import type to see syntax ' + \
           'for this type.'
    
    def __init__(self):
        tables = [('','Select an import type'),
                  ('location','Locations'),
                  ('room','Rooms'),
                  ('org','Organisations'),
                  ('usage','Usage categories'),
                  ('subcat','Subcategories'),
                  ('type','Types'),
                  ('product','Products'),
                  ('vendor','Vendors'),
                  ('netbox','IP devices'),
                  ('service','Services'),
                  ('vlan','Vlans'),
                  ('prefix','Prefixes'),
                  ('cabling','Cabling'),
                  ('patch','Patch')]

        sep = [(':','Colon (:)'),
               (';','Semicolon (;)'),
               (',','Comma (,)')]

        f = {'table': [inputSelect(options=tables),REQ_FALSE],
             'separator': [inputSelect(options=sep),REQ_FALSE],
             'file': [inputFile(),REQ_FALSE],
             'textarea': [inputTextArea(),REQ_FALSE]}
        self.fields = f
        self.setControlNames()

def bulkImportParse(input,bulkdef,separator):
    """ Parses a list of input data.
        input = list of rows to import
        bulkdef = bulk defintion class
        separator = field separator chosen """
    commentChar = '#'
    # Any number of spaces followed by a # is a comment
    comment = re.compile('\s*%s' % commentChar)

    # list of (parsed correctly,data/error)
    parsed = []

    linenr = 0
    for line in input:
        linenr += 1    
        remark = None
        if comment.match(line):
            # This line is a comment
            pass
        elif len(line) > 0:
            fields = line.split(separator)
            data = {}
            if (bulkdef.enforce_max_fields) and \
               (len(fields) >  bulkdef.max_num_fields):
                # len(fields) > max_num_fields
                # and enforce_max_fields == True
                status = BULK_STATUS_RED_ERROR
                remark = 'Too many fields'
            elif len(fields) < bulkdef.min_num_fields:
                status = BULK_STATUS_RED_ERROR
                remark = 'Missing one or more required fields'
            else:
                status = BULK_STATUS_OK
                excessCounter = 0
                for i in range(0,len(fields)):
                    # Is this one of the predefined fields?
                    # ie. where i < max_fields
                    # if not, it is eg. a subcatfield
                    if i < bulkdef.max_num_fields:
                        # fieldname,maxlen,required,use
                        fn,ml,req,use = bulkdef.fields[i]
                        # missing required field?
                        if req and not len(fields[i]):
                            status = BULK_STATUS_RED_ERROR
                            remark = "Syntax error: Required field '"+ fn + \
                                     "' missing"
                            break
                        # max field length exceeded?
                        if ml and (len(fields[i]) > ml):
                            status = BULK_STATUS_RED_ERROR
                            remark = "Syntax error: Field '" + fn + \
                                     "' exceeds max field length"
                            break
                        # if this is the id field, 
                        # check if it's unique in the db
                        if type(bulkdef.uniqueField) is str:
                            if fn == bulkdef.uniqueField:
                                where = bulkdef.uniqueField+"='"+fields[i] + "'"
                                result = bulkdef.table.getAllIDs(where=where)
                                if result:
                                    status = BULK_STATUS_YELLOW_ERROR
                                    remark = "Not unique: An entry with " +fn + \
                                             "=" + fields[i] + " already exists"
                                    break
                    else:
                        # This field isn't specified in the bulkdef
                        # Used by netbox for adding any number of subcats
                        fn = BULK_UNSPECIFIED_FIELDNAME + str(excessCounter)
                        excessCounter += 1

                    # check the validity of this field with the bulkdefs 
                    # checkValidity function this is for checking things 
                    # like: do ip resolve to a hostname for ip devices?
                    (status,validremark) = bulkdef.checkValidity(fn,fields[i])
                    if validremark:
                        remark = validremark

                    if status != BULK_STATUS_OK:
                        break
                    # use this field if no error (status==BULK_STATUS_OK)
                    # and if it's marked to be used (use == true)                   
                    if fn=='serial' and status==BULK_STATUS_OK:
                        data[fn] = fields[i] 
                    if (status == BULK_STATUS_OK) and (use == True):
                        data[fn] = fields[i] 
            # postCheck

            if status == BULK_STATUS_OK:
                validremark = False
                if bulkdef.postCheck:

                    (status,validremark,data) = bulkdef.postCheck(data)
                    #if data.has_key('serial'):
                    #    del(data['serial'])

                if validremark:
                    remark = validremark
            parsed.append((status,data,remark,line,linenr))
    return parsed


def bulkImport(req,action):
    """ Main bulk import function. Displays menu and starts parsing. """
    # Cnames for hidden inputs
    BULK_HIDDEN_DATA = 'blk_hd'
    BULK_TABLENAME = 'blk_tbl'
    BULK_SEPARATOR = 'blk_sep'

    status = editdbStatus()
    # form
    form = editForm()
    form.status = status
    form.action = BASEPATH + 'bulk/'
    form.title = 'Bulk import'
    form.textConfirm = 'Preview import'
    form.enctype = 'multipart/form-data'
    form.add(editboxBulk())
    # list
    list = None

    help = "# Rows starting with a '#' are comments\n" + \
           "# Select a file to import from, or write here\n" + \
           "# For field syntax, select an import type\n"

    # Dict with the different bulk definitions
    bulkdef = {'patch': bulkdefPatch,
               'cabling': bulkdefCabling,
               'location': bulkdefLocation,
               'room': bulkdefRoom,
               'netbox': bulkdefNetbox,
               'org': bulkdefOrg,
               'usage': bulkdefUsage,
               'service': bulkdefService,
               'vendor': bulkdefVendor,
               'subcat': bulkdefSubcat,
               'type': bulkdefType,
               'product': bulkdefProduct,
               'prefix': bulkdefPrefix}

    listView = None
    # direct link to a specific table?
    if action:
        if bulkdef.has_key(action):
            help = bulkdef[action].syntax
        form.editboxes[0].fields['table'][0].value = action
    form.editboxes[0].fields['textarea'][0].value = help

    # form  submitted?
    if req.form.has_key(form.cnameConfirm) and len(req.form['table']):
        # Get data from uploaded file or from textarea
        fileinput = req.form['file']
        input = req.form['textarea']
        if len(fileinput):
            input = fileinput

        # Try decoding different encodings
        for encoding in BULK_TRY_ENCODINGS:
            try:
                # Work internally with DEFAULT_ENCODING (utf-8)
                input = input.decode(encoding).encode(DEFAULT_ENCODING)
                break
            except UnicodeError:
                pass
            except:
                raise(repr(encoding))

        input = input.split('\n')

        # strip cr
        i = []
        for line in input:
            i.append(line.strip('\r'))
        input = i

        separator = req.form['separator']
        table = req.form['table']
        parsed = bulkImportParse(input,bulkdef[table],separator)

        rows = []
        for p in parsed:
            status,data,remark,line,linenr = p

            if status == BULK_STATUS_OK:
                row = [(['<IMG src="' + BULK_IMG_GREEN + '">'],False),
                       ([linenr],False),
                       ([line],False),
                       ([remark],False)]
            elif status == BULK_STATUS_YELLOW_ERROR:
                row = [(['<IMG src="' + BULK_IMG_YELLOW + '">'],False),
                       ([linenr],False),
                       ([line],False),
                       ([remark],False)]
            elif status == BULK_STATUS_RED_ERROR:
                row = [(['<IMG src="' + BULK_IMG_RED + '">'],False),
                       ([linenr],False),
                       ([line],False),
                       ([remark],False)]
            rows.append((data,row)) 
            
        # show list
        list = selectList()
        list.action = BASEPATH + 'bulk/'
        list.isBulkList = True
        list.imgGreen = BULK_IMG_GREEN
        list.imgYellow = BULK_IMG_YELLOW
        list.imgRed = BULK_IMG_RED
        list.legendGreen = 'No errors. Row will be imported.'
        list.legendYellow = 'Other error. Row will not be imported.'
        list.legendRed = 'Syntax error. Row will not be imported.'
        list.title = 'Preview import'
        list.hiddenData = []
        list.hiddenData.append((BULK_TABLENAME,req.form['table']))
        list.hiddenData.append((BULK_SEPARATOR,req.form['separator']))
        for p in parsed:
            status,data,remark,line,linenr = p
            if status == BULK_STATUS_OK:
                list.hiddenData.append((BULK_HIDDEN_DATA,line))
        list.headings = ['','Line','Input','Remark']
        list.rows = rows
        form = None
    elif req.form.has_key(selectList.cnameBulkConfirm):
        # import confirmed after preview
        table = req.form[BULK_TABLENAME]
        separator = req.form[BULK_SEPARATOR]
        form.status = editdbStatus()
        if req.form.has_key(BULK_HIDDEN_DATA):
            data = req.form[BULK_HIDDEN_DATA]
            result = bulkInsert(data,bulkdef[table],separator)
            noun = ' rows'
            if result == 1:
                noun = ' row'
            form.status.messages.append('Inserted ' + str(result) + noun)
            page = pageList[table]
            listView = page.listDef(req,page,None)
            listView.status = form.status
            listView.fill(req)
            form = None
        else:
            form.status.errors.append('No rows to insert.')

    nameSpace = {'entryList': listView, 'editList': list, 'editForm': form}
    template = editdbTemplate(searchList=[nameSpace])
    template.path = EDITPATH + [('Bulk import',False)]
    return template.respond()

#Function for bulk inserting
def bulkInsert(data,bulkdef,separator):
    """ Inserts data when bulk importing. """
    if not type(data) is list:
        data = [data]

    prerowlist = []
    for line in data:
        fields = line.split(separator)

        row = {}
        inputLen = len(fields)
        # If we've got additional arguments (service or netbox)
        # make sure we don't exceed number of arguments specified
        # by bulkdef.fields
        if inputLen > len(bulkdef.fields):
            inputLen = len(bulkdef.fields)
        for i in range(0,inputLen):
            # fieldname,maxlen,required,use
            field,ml,req,use = bulkdef.fields[i]
            row[field] = fields[i] 
        # Add extra arguments
        excessCount = 0        
        i = inputLen
        if len(fields) > len(bulkdef.fields):
            while(i < (len(fields))):
                field = BULK_UNSPECIFIED_FIELDNAME + str(excessCount)
                row[field] = fields[i]
                excessCount += 1
                i += 1
        prerowlist.append(row)

    # Do table specific things with the data before insterting
    # (create missing devices for netboxes for example)
    if bulkdef.process:
        rowlist = []
        for row in prerowlist:
            row = bulkdef.preInsert(row)
            if row:
                rowlist.append(row)
    else:
        # do nothing, just insert it
        rowlist = prerowlist            

    # Remove all fields
    # where use = False
    if not bulkdef.onlyProcess:
        for row in rowlist:
            for i in range(0,len(fields)):
                # fieldname,maxlen,required,use
                field,ml,req,use = bulkdef.fields[i]
                # Escape special characters
                if row.has_key(field):
                    row[field] = row[field].replace("'","\\'")
                #row[field] = row[field].replace('"','\\"')
                if not use:
                    if row.has_key(field):
                        del(row[field])

        addEntryBulk(rowlist,bulkdef.tablename)
    return len(rowlist)


# Classes describing the fields for bulk import
class bulkdefCabling:
    """ Contains defintion of fields for bulk importing cabling """
    tablename = 'cabling'
    table = nav.db.manage.Cabling
    uniqueField = ['roomid','jack']
    enforce_max_fields = True
    max_num_fields = 6
    min_num_fields = 4

    process = True
    onlyProcess = False
    syntax = '#roomid:jack:building:targetroom:[category:descr]\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('roomid',30,True,True),
              ('jack',0,True,True),
              ('building',0,True,True),
              ('targetroom',0,True,True),
              ('category',0,False,True),
              ('descr',0,False,True)]

    def checkValidity(cls,field,data):
        status = BULK_STATUS_OK
        remark = None
        # locationid must exist in Location
        if field == 'roomid':
            if data:
                if len(data):
                    try:
                        nav.db.manage.Room(data).load()
                    except forgetSQL.NotFound:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Room '" + data + "' not found in database"
        if field == 'category':
            if data:
                if len(data):
                    catlist = []
                    for cat in CATEGORY_LIST:
                        catlist.append(cat[0])
                    if not data in catlist:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Category '" + data + "' not found in " +\
                                 "config file"
        return (status,remark)
    checkValidity = classmethod(checkValidity)

    def preInsert(cls,row):
        """ Inserts default value for category. """
        if not row.has_key('category'):
            # Set default category
            row['category'] = CATEGORY_LIST[0][0]
        else:
            if not len(row['category']):
                # Set default category
                row['category'] = CATEGORY_LIST[0][0]

        # Check uniqueness
        where = ""
        first = True
        for field in cls.uniqueField:
            if not first:
                where += 'AND '
            where += field + "='" + row[field] + "' "
            first = False
        result = cls.table.getAll(where)
        if result:
            row = None

        return row
    preInsert = classmethod(preInsert)


class bulkdefPatch:
    """ Contains defintion of fields for bulk importing patches """
    tablename = 'patch'
    table = nav.db.manage.Patch
    uniqueField = ['swportid','cablingid']
    enforce_max_fields = True
    max_num_fields = 6
    min_num_fields = 5

    process = True
    onlyProcess = False
    syntax = '#switch(sysname):module:port:roomid:jack[:split]\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('sysname',0,True,False),
              ('module',0,True,False),
              ('port',0,True,False),
              ('roomid',0,True,False),
              ('jack',0,True,False),
              ('split',0,False,True)]

    def checkValidity(cls,field,data):
        """ Checks validity (eg. existance) of input fields."""
        status = BULK_STATUS_OK
        remark = None
        if field == 'roomid':
            if data:
                if len(data):
                    try:
                        room = nav.db.manage.Room(data)
                        cls.roomId = room.roomid
                        # If room existsm, check if netbox is in it
                        where = "netboxid=" + str(cls.netboxId) + " AND " +\
                                "roomid='" + cls.roomId + "'"
                        box = nav.db.manage.Netbox.getAll(where)
                        if not box:
                            sw = nav.db.manage.Netbox(cls.netboxId).sysname
                            status = BULK_STATUS_RED_ERROR
                            remark = "Switch '" + sw + "' not in room " +\
                                     cls.roomId
                    except forgetSQL.NotFound:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Room '" + data + "' not found in database"
        if field == 'sysname':
            if data:
                if len(data):
                    # Check if switch is given as ip or sysname
                    result = re.match('^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$',
                                      data)
                    ip = None
                    if result:
                        # This is an IP
                        ip = data
                    else:
                        # Not an IP, possibly a hostname
                        try:
                            ip = gethostbyname(data)
                            sysname = data
                        except:
                            status = BULK_STATUS_RED_ERROR
                            remark = "Switch '" + data + "' not found in database"
                    # 'ip' should be numerical ip now, 
                    # else there already was an error
                    if ip:
                        where = "ip='" + ip + "'"
                        box = nav.db.manage.Netbox.getAll(where)
                        if box:
                            box = box[0]
                            cls.netboxId = box.netboxid
                        else:
                            status = BULK_STATUS_RED_ERROR
                            remark = "Switch '" + data + "' not found in database"
        if field == 'module':
            if data:
                if len(data):
                    try:
                        tst = int(data)
                        where = "module='" + data + "' AND " +\
                                "netboxid='" + str(cls.netboxId) + "'"
                        module = nav.db.manage.Module.getAll(where)
                        if module:
                            module = module[0]
                            cls.moduleId = module.moduleid
                        else:
                            status = BULK_STATUS_RED_ERROR
                            sw = nav.db.manage.Netbox(cls.netboxId).sysname
                            remark = "Module '" + data + "' in switch " +\
                                     sw + " not found in database"
                    except ValueError:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Module must be integer"
        if field == 'port':
            # Check if this port on the specified module in the switch
            # is present in the database
            if data:
                if len(data):
                    try:
                        tst = int(data)
                        where = "moduleid='" + str(cls.moduleId) + "' AND " +\
                                "port='" + data + "'"
                        swport = nav.db.manage.Swport.getAll(where)
                        if swport:
                            swport = swport[0]
                            cls.swportId = swport.swportid
                        else:
                            status = BULK_STATUS_RED_ERROR
                            sw = nav.db.manage.Netbox(cls.netboxId).sysname
                            module = nav.db.manage.Module(cls.moduleId).module
                            remark = "Port '" + data + "', module '" +\
                                     str(module) + "' in switch " +\
                                     sw + " not found in database"
                    except ValueError:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Port must be integer"
        if field == 'jack':
            if data:
                if len(data):
                    where = "roomid='" + cls.roomId + "' AND " +\
                            "jack='" + data + "'"
                    cabling = nav.db.manage.Cabling.getAll(where)
                    if cabling:
                        cabling = cabling[0]
                        cls.cablingId = cabling.cablingid
                    else:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Cabling between " +\
                                 " jack '" + data + "' " +\
                                 " and room '" + cls.roomId + "'" +\
                                 " not found in database"
        if field == 'split':
            if data:
                if len(data):
                    splitlist = []
                    for split in SPLIT_LIST:
                        splitlist.append(split[0])
                    if not data in splitlist:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Split '" + data + "' not found in config " +\
                                 "file"
        return (status,remark)
    checkValidity = classmethod(checkValidity)

    def preInsert(cls,row):
        """ Gets required data from db before inserting row. """
        # Check if sysname is given as ip or sysname
        result = re.match('^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$',
                          row['sysname'])
        ip = None
        if result:
            # This is an IP
            ip = row['sysname']
        else:
            # Not an IP, possibly a hostname
            try:
                ip = gethostbyname(row['sysname'])
            except:
                # DNS lookup failed
                # could happen if DNS stopped working between
                # preview and insert
                row = None

        if ip:
            where = "ip='" + ip + "'"
            box = nav.db.manage.Netbox.getAll(where)
            box = box[0]

            where = "module='" + row['module'] + "' AND " +\
                    "netboxid='" + str(box.netboxid) + "'"
            module = nav.db.manage.Module.getAll(where)
            module = module[0]

            where = "moduleid='" + str(module.moduleid) + "' AND " +\
                    "port='" + row['port'] + "'"
            swport = nav.db.manage.Swport.getAll(where)
            swport = swport[0]

            where = "roomid='" + row['roomid'] + "' AND " +\
                    "jack='" + row['jack'] + "'"
            cabling = nav.db.manage.Cabling.getAll(where)
            cabling = cabling[0]

            row['swportid'] = str(swport.swportid)
            row['cablingid'] = str(cabling.cablingid)

            if not row.has_key('split'):
                # Set default split
                row['split'] = SPLIT_LIST[0][0]
            if not len(row['split']):
                row['split'] = SPLIT_LIST[0][0]

            # Check if the selected jack already belongs to a patch
            where = "cablingid='" + row['cablingid'] + "'"
            otherPatch = nav.db.manage.Patch.getAll(where)
            if otherPatch:
                # Already exists a patch with this jack, it must
                # be splitted, if split is changed then do something
                otherPatch = otherPatch[0]
                otherSplit = otherPatch.split

                if SPLIT_OPPOSITE[row['split']] != otherSplit:
                    # Splits are different, either update split on the
                    # other entry, or delete it if this split='no'
                    otherPatchId = str(otherPatch.patchid)
                    # SPLIT_LIST[0][0] is default entry id
                    if row['split'] == SPLIT_LIST[0][0]:
                        # Delete other entry
                        deleteEntry([otherPatchId],'patch','patchid')
                    else:
                        # Update other entry
                        fields = {'split': SPLIT_OPPOSITE[row['split']]}
                        updateEntryFields(fields,'patch',
                                          'patchid',otherPatchId)

        # Check uniqueness
        where = ""
        first = True
        for field in cls.uniqueField:
            if not first:
                where += 'AND '
            where += field + "='" + row[field] + "' "
            first = False
        result = cls.table.getAll(where)
        if result:
            row = None

        return row
    preInsert = classmethod(preInsert)


class bulkdefLocation:
    """ Contains defintion of fields for bulk importing locations """
    # number of fields
    tablename = 'location'
    table = manage.Location
    uniqueField = 'locationid'
    enforce_max_fields = True
    max_num_fields = 2
    min_num_fields = 2

    process = False
    onlyProcess = False
    syntax = '#locationid:descr\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('locationid',30,True,True),
              ('descr',0,True,True)]

    def checkValidity(cls,field,data):
        """ Checks validity of fields. (No need for location). """
        status = True
        remark = None
        return (status,remark)
    checkValidity = classmethod(checkValidity)

class bulkdefRoom:
    """ Contains defintion of fields for bulk importing rooms """
    # number of fields
    tablename = 'room'
    table = manage.Room
    uniqueField = 'roomid'
    enforce_max_fields = True
    max_num_fields = 7
    min_num_fields = 1

    process = False
    onlyProcess = False
    syntax = '#roomid[:locationid:descr:opt1:opt2:opt3:opt4]\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('roomid',30,True,True),
              ('locationid',30,False,True),
              ('descr',0,False,True),
              ('opt1',0,False,True),
              ('opt2',0,False,True),
              ('opt3',0,False,True),
              ('opt4',0,False,True)]

    def checkValidity(cls,field,data):
        status = BULK_STATUS_OK
        remark = None
        # locationid must exist in Location
        if field == 'locationid':
            if data:
                if len(data):
                    try:
                        manage.Location(data).load()
                    except forgetSQL.NotFound:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Location '" + data + "' not found in database"
        return (status,remark)
    checkValidity = classmethod(checkValidity)

class bulkdefOrg:
    """ Contains field definitions for bulk importing orgs. """
    tablename = 'org'
    table = manage.Org
    uniqueField = 'orgid'
    enforce_max_fields = True
    max_num_fields = 6
    min_num_fields = 1

    process = False
    onlyProcess = False
    syntax = '#orgid[:parent:description:optional1:optional2:optional3]\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('orgid',30,True,True),
              ('parent',30,False,True),
              ('descr',0,False,True),
              ('opt1',0,False,True),
              ('opt2',0,False,True),
              ('opt3',0,False,True)]

    def checkValidity(cls,field,data):
        """ Checks validity of input fields. """
        status = BULK_STATUS_OK
        remark = None
        if field == 'parent' and len(data):
             try:
                manage.Org(data).load()
             except forgetSQL.NotFound:
                status = BULK_STATUS_RED_ERROR
                remark = "Parent '" + data + "' not found in database"  
        return (status,remark)
    checkValidity = classmethod(checkValidity)

class bulkdefUsage:
    """ Contains field definitions for bulk importing usage. """
    # number of fields
    tablename = 'usage'
    table = manage.Usage
    uniqueField = 'usageid'
    enforce_max_fields = True
    max_num_fields = 2
    min_num_fields = 2

    process = False
    onlyProcess = False
    syntax = '#usageid:descr\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('usageid',30,True,True),
              ('descr',0,True,True)]

    def checkValidity(cls,field,data):
        """ Checks validity of input fields. """
        status = BULK_STATUS_OK
        remark = None
        return (status,remark)
    checkValidity = classmethod(checkValidity)

class bulkdefVendor:
    """ Contains field information for bulk importing vendors. """
    # number of fields
    tablename = 'vendor'
    table = manage.Vendor
    uniqueField = 'vendorid'
    enforce_max_fields = True
    max_num_fields = 1
    min_num_fields = 1

    process = False
    onlyProcess = False
    syntax = '#vendorid\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('vendorid',15,True,True)]

    def checkValidity(cls,field,data):
        """ Checks validity of input fields. """
        status = BULK_STATUS_OK
        remark = None
        return (status,remark)
    checkValidity = classmethod(checkValidity)

class bulkdefSubcat:
    """ Contains field information for bulk importing subcats. """
    tablename = 'subcat'
    table = manage.Subcat
    uniqueField = 'subcatid'
    enforce_max_fields = True
    max_num_fields = 3
    min_num_fields = 3

    process = False
    onlyProcess = False
    syntax = '#subcatid:catid:description\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('subcatid',0,True,True),
              ('catid',8,True,True),
              ('descr',0,True,True)]

    def checkValidity(cls,field,data):
        """ Checks validity of input fields. """
        status = BULK_STATUS_OK
        remark = None

        if field == 'catid':
             try:
                manage.Cat(data).load()
             except forgetSQL.NotFound:
                status = BULK_STATUS_RED_ERROR
                remark = "Category '" + data + "' not found in database"  

        return (status,remark)
    checkValidity = classmethod(checkValidity)


class bulkdefType:
    """ Contains field defintions for bulk importing types. """
    # number of fields
    tablename = 'type'
    table = manage.Type
    uniqueField = 'typename'
    enforce_max_fields = True
    max_num_fields = 7
    min_num_fields = 3

    process = True
    onlyProcess = False
    syntax = '#vendorid:typename:sysoid[:description:frequency:cdp=(yes|no)' +\
             ':tftp=(yes|no)]\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('vendorid',15,True,True),
              ('typename',0,True,True),
              ('sysobjectid',0,True,True),
              ('descr',0,False,True),
              ('frequency',0,False,True),
              ('cdp',0,False,True),
              ('tftp',0,False,True)]

    def checkValidity(cls,field,data):
        """ Checks validity of input fields. """
        status = BULK_STATUS_OK
        remark = None

        if field == 'vendorid':
            try:
                manage.Vendor(data).load()
            except forgetSQL.NotFound:
                status = BULK_STATUS_RED_ERROR
                remark = "Vendor '" + data + "' not found in database"  

        return (status,remark)
    checkValidity = classmethod(checkValidity)

    def preInsert(cls,row):
        """ Alter fields before inserting. (set correct value for cdp
            and tftp if anything is input in those fields) """
        if row.has_key('cdp'):
            if len(row['cdp']):
                if not row['cdp'].lower() == 'no':
                    row['cdp'] = '1'
            else:
                row['cdp'] = '0'
        if row.has_key('tftp'):
            if len(row['tftp']):
                if not row['tftp'].lower() == 'no':
                    row['tftp'] = '1'
            else:
                row['tftp'] = '0'
        return row
    preInsert = classmethod(preInsert)

class bulkdefProduct:
    """ Contains field definitions for bulk importing products. """
    # number of fields
    tablename = 'product'
    table = manage.Product
    uniqueField = 'productno'
    enforce_max_fields = True
    max_num_fields = 3
    min_num_fields = 2

    process = True
    onlyProcess = False
    syntax = '#vendorid:productno[:description]\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('vendorid',15,True,True),
              ('productno',0,True,True),
              ('descr',0,False,True)]

    def checkValidity(cls,field,data):
        """ Checks validity of input fields. """
        status = BULK_STATUS_OK
        remark = None

        if field == 'vendorid':
             try:
                manage.Vendor(data).load()
             except forgetSQL.NotFound:
                status = BULK_STATUS_RED_ERROR
                remark = "Vendor '" + data + "' not found in database"  
        return (status,remark)
    checkValidity = classmethod(checkValidity)

    def preInsert(cls,row):
        """ Alter fields before inserting. (set correct value for cdp
            and tftp if anything is input in those fields) """
        if row.has_key('cdp'):
            row['cdp'] = '1'
        if row.has_key('tftp'):
            row['tftp'] = '1'
        return row
    preInsert = classmethod(preInsert)

class bulkdefNetbox:
    """ Contains field definitions for bulk importing boxes. """
    tablename = 'netbox'
    table = manage.Netbox
    uniqueField = 'ip'
    # number of fields
    enforce_max_fields = False
    max_num_fields = 8
    min_num_fields = 4

    process = True
    onlyProcess = True
    syntax = '#roomid:ip:orgid:catid:[ro:serial:rw:function:subcat1:subcat2..]\n'
    # list of (fieldname,max length,not null,use field)
    fields = [('roomid',0,True,True),
              ('ip',0,True,True),
              ('orgid',30,True,True),
              ('catid',8,True,True),
              ('ro',0,False,True),
              ('serial',0,False,False),
              ('rw',0,False,True),
              ('function',0,False,False)]

    def postCheck(cls,data):
        """ Checks each box before inserting. Tries to connect with snmp
            if ro is specified. """
        status = BULK_STATUS_OK
        remark = None

        try:
            hasRO = False
            if data.has_key('ro'):
                if len(data['ro']):
                    hasRO = True
            hasSerial = False
            if data.has_key('serial'):
                if len(data['serial']):
                   hasSerial = True

            if (not hasRO) and manage.Cat(data['catid']).req_snmp:
                status = BULK_STATUS_YELLOW_ERROR
                raise("This category requires an RO community")

            ## SERIAL IS NOW OPTIONAL
            #if not (hasRO or hasSerial):
            #    status = BULK_STATUS_RED_ERROR
            #    raise("Neither RO, nor serial specified.")

            if hasRO:
                error = False
                try:
                    box = initBox.Box(data['ip'],data['ro'])
                    
                    # DeviceId / Serial takes too long time to get
                    # We will not do it here
#                    box.getDeviceId()
#                    if (not hasSerial) and (not box.serial):
#                        status = BULK_STATUS_YELLOW_ERROR
#                        error = "No serial returned by SNMP, and no serial given."
                    if (not box.typeid):
                        if manage.Cat(data['catid']).req_snmp:
                            status = BULK_STATUS_YELLOW_ERROR
                            error = "Got SNMP response, but couldn't get type which is required for IP devices of this category. Add type manually."
                        else:
                            status = BULK_STATUS_OK
                            error = "Got SNMP response, but couldn't get type (type isn't required for this category)."
                except nav.Snmp.TimeOutException:
                    if manage.Cat(data['catid']).req_snmp:
                        # Snmp failed, but is required by this CAT
                        status = BULK_STATUS_YELLOW_ERROR
                        raise("RO given, but failed to contact IP device by SNMP (IP devices of this category are required to answer).")
                    else:
                        # Snmp failed, but isn't required by this CAT
                        if hasSerial:
                            status = BULK_STATUS_OK
                            raise("RO given, but failed to contact IP device by SNMP (IP devices of this cateogry aren't required to answer as long as a serial is given).")
                        else:
                            status = BULK_STATUS_YELLOW_ERROR
                            raise("RO given, but failed to contact IP device by SNMP (IP devices of this cateogry aren't required to answer, but you must supply a serial if they don't).")
                except Exception, e:
                    status = BULK_STATUS_RED_ERROR
                    error = 'Uknown error while querying IP device: '
                    error += str(sys.exc_info()[0]) + ': '
                    error += str(sys.exc_info()[1])
                if error:
                    raise(error)
        except:
            remark = sys.exc_info()[0]

        return (status,remark,data)
    postCheck = classmethod(postCheck)

    def checkValidity(cls,field,data):
        """ Checks the validity of the input fields. """
        status = BULK_STATUS_OK
        remark = None
                 
        if field == 'ip':
            try:
                sysname = gethostbyaddr(data)[0]
            except:
                remark = "DNS lookup failed, using '" + data + "' as sysname"
        if field == 'roomid':
             try:
                manage.Room(data).load()
             except forgetSQL.NotFound:
                status = BULK_STATUS_RED_ERROR
                remark = "Room '" + data + "' not found in database"  
        if field == 'orgid':
             try:
                manage.Org(data).load()
             except forgetSQL.NotFound:
                status = BULK_STATUS_RED_ERROR
                remark = "Organisation '" + data + "' not found in database"
        if field == 'catid':
             try:
                manage.Cat(data).load()
             except forgetSQL.NotFound:
                status = BULK_STATUS_RED_ERROR
                remark = "Invalid category '" + data + "'"
        if field == 'serial':
            if len(data):
                where = "serial='%s'" % (data,)
                device = manage.Device.getAll(where)
                if device:
                    # There exists a device with this serial,
                    # must check if any netbox is connected with this
                    # device
                    where = "deviceid='%s'" % (device[0].deviceid,)
                    netbox = manage.Netbox.getAll(where)
                    if netbox:
                        status = BULK_STATUS_RED_ERROR
                        remark = "An IP device with the serial '" + data + \
                                 "' already exists"
        if field == BULK_UNSPECIFIED_FIELDNAME:
            # These are subcats
            # Need to check not only if the subcat exists, but
            # also if the cat is correct
            try:
                manage.Subcat(data).load()
            except forgetSQL.NotFound:
                status = BULK_STATUS_RED_ERROR
                remark = "Invalid subcat '" + data + "'"
        return (status,remark)
    checkValidity = classmethod(checkValidity)

    def preInsert(cls,row):
        """ Changes rows before inserting. Gets required data from db. """
        # Get sysname
        try:
            sysname = gethostbyaddr(row['ip'])[0]
        except:
            sysname = row['ip'] 
        row['sysname'] = sysname

        # Get prefixid
        query = "SELECT prefixid FROM prefix WHERE '%s'::inet << netaddr" \
                % (row['ip'],)
        try:
            result = executeSQLreturn(query) 
            row['prefixid'] = str(result[0][0])
        except:
            pass        
    
        deviceid = None
        box = None
        if row.has_key('ro'):
            if len(row['ro']):
                try:
                    box = initBox.Box(row['ip'],row['ro'])
                    if box.typeid:
                        typeId = str(box.typeid)
                        row['typeid'] = typeId
                    if box.snmpversion:
                        row['snmp_version'] = str(box.snmpversion[0])
                    # getDeviceId() now returns an Int
                    deviceid = box.getDeviceId()
                except:
                    # If initBox fails, always make a new device
                    deviceid = None

        if deviceid:
            # Already got a device from initbox
            row['deviceid'] = str(deviceid)
            if row.has_key('serial'):
                # Serial shouldn't be inserted into Netbox table
                # remove it from the row
                del(row['serial'])
        else:
            # Must make a new device
            newSerial = None

            # Got serial from row?
            if row.has_key('serial'):
                if len(row['serial']):
                    newSerial = row['serial']
                # Serial shouldn't be inserted into Netbox table
                # remove it from the row
                del(row['serial'])

            # If we got a serial by SNMP and none was specified in the bulk
            # data, use the one retrieved by SNMP
            if box and not newSerial:
                if box.serial:
                    newSerial = str(box.serial)

            fields = {}
            if newSerial:
                # Serial given in row, or retrieved by snmp
                fields = {'serial': newSerial}

                # Must check if a device with this serial is already present
                where = "serial='%s'" % (fields['serial'])
                device = manage.Device.getAll(where)
                if device:
                    # Found device, and it is unique (serial must be unique)
                    deviceid = str(device[0].deviceid)
            
            if not deviceid:                
                # Make new device
                deviceid = addEntryFields(fields,
                                          'device',
                                          ('deviceid','device_deviceid_seq'))
            
            row['deviceid'] = deviceid

        if row:
            # Function
            netboxFunction = None
            if row.has_key('function'):
                if len(row['function']):
                    netboxFunction = row['function']
                del(row['function'])

            # Subcat's
            excessCount = 0
            excessField = BULK_UNSPECIFIED_FIELDNAME + str(excessCount) 
            subcatList = []
            while(row.has_key(excessField)):
                subcatList.append(row[excessField]) 
                del(row[excessField])
                excessCount += 1
                excessField = BULK_UNSPECIFIED_FIELDNAME + str(excessCount) 
           
            # Insert netbox
            netboxId = addEntryFields(row,
                                      'netbox',
                                      ('netboxid','netbox_netboxid_seq'))

        
            # Insert netboxfunction
            if netboxFunction:
                fields = {'netboxid': netboxId,
                          'var': 'function',
                          'val': netboxFunction}
                addEntryFields(fields,
                               'netboxinfo')

            if subcatList:                          
                for subcat in subcatList:
                    if len(subcat):
                        sql = "SELECT subcatid FROM subcat WHERE " +\
                              "subcatid='%s'" % (subcat,)
                        result = executeSQLreturn(sql)
                        if result:
                            fields = {'netboxid': netboxId,
                                      'category': subcat}
                            addEntryFields(fields,
                                           'netboxcategory')

        return row
    preInsert = classmethod(preInsert)

class bulkdefService:
    """ Contains field definitions for bulk importing services. """
    tablename = 'service'
    table = manage.Service
    uniqueField = None
    enforce_max_fields = False
    max_num_fields = 2
    min_num_fields = 2

    process = True
    onlyProcess = True
    syntax = '#ip/sysname:handler[:arg=value[:arg=value]]\n'

    postCheck = False
    # Seperator for optargs arguments
    optSep = '='

    # list of (fieldname,max length,not null,use field)
    fields = [('netboxid',0,True,True),
              ('handler',0,True,True)]

    def insert(cls,row):
        raise(repr(row))
    insert = classmethod(insert)

    def postCheck(cls,data):
        """ Changes row data before inserting. Does DNS lookup etc. """
        status = BULK_STATUS_OK
        remark = None

        try:
            # Check sysname/ip
            try:
                ip = gethostbyname(data['netboxid'])
            except gaierror:
                raise ("DNS query for '%s' failed." % (data['netboxid'],)) 
            where = "ip='%s'" % (ip,)
            box = manage.Netbox.getAll(where)
            if box:
                data['netboxid'] = str(box[0].netboxid)
            else:
                raise("No box with sysname or ip '" + data['netboxid'] + \
                      "' found in database.")

            # Check validity of additional arguments
            properties = getDescription(data['handler'])
            optargs = []
            args = []
            if properties:
                if properties.has_key('optargs'):
                    for optarg in properties['optargs']:
                        optargs.append(optarg)
                if properties.has_key('args'):
                    for arg in properties['args']:
                        args.append(arg)

            seperator = bulkdefService.optSep
            excessCount = 0
            excessField = BULK_UNSPECIFIED_FIELDNAME + str(excessCount) 
            argsData = {}
            while(data.has_key(excessField)):
                splitted = data[excessField].split('=',1)
                if len(splitted) == 2:
                    if len(splitted[1]):
                        argsData[splitted[0]] = splitted[1]
                excessCount += 1
                excessField = BULK_UNSPECIFIED_FIELDNAME + str(excessCount) 

            for arg in args:
                if not argsData.has_key(arg):
                    raise("Missing required argument '" + arg +"'")
                del(argsData[arg])
            for key in argsData.keys():
                if not key in optargs:
                    raise("Invalid argument '" + key + "'")
            
        except:
            status = BULK_STATUS_YELLOW_ERROR
            remark = sys.exc_info()[0]

        return (status,remark,data)
    postCheck = classmethod(postCheck)
           
    def checkValidity(cls,field,data):
        """ Checks validity of input fields. """
        status = BULK_STATUS_OK
        remark = None
       
        if field == 'handler': 
            if not data in getCheckers():
                remark = "Invalid handler '" + data + "'"
                status = BULK_STATUS_RED_ERROR
        return (status,remark)
    checkValidity = classmethod(checkValidity)

    def preInsert(cls,data):
        """ Fills in all missing data before inserting entry. """
        try:
            ip = gethostbyname(data['netboxid'])
            where = "ip='%s'" % (ip,)
            box = manage.Netbox.getAll(where)
            if box:
                data['netboxid'] = str(box[0].netboxid)
            else:
                data = None
        except:
            data = None

        if data:
            fields = {'netboxid': data['netboxid'],
                      'handler': data['handler']}
            serviceid = addEntryFields(fields,
                                      'service',
                                      ('serviceid','service_serviceid_seq'))

            # Check validity of additional arguments
            seperator = bulkdefService.optSep
            excessCount = 0
            excessField = BULK_UNSPECIFIED_FIELDNAME + str(excessCount) 
            argsData = {}
            while(data.has_key(excessField)):
                splitted = data[excessField].split('=',1)
                if len(splitted) == 2:
                    if len(splitted[1]):
                        argsData[splitted[0]] = splitted[1]
                excessCount += 1
                excessField = BULK_UNSPECIFIED_FIELDNAME + str(excessCount) 

        
            for property,value in argsData.items():
                fields = {'serviceid': serviceid,
                          'property': property,
                          'value': value}
                addEntryFields(fields,
                               'serviceproperty')
        return data
    preInsert = classmethod(preInsert)


class bulkdefPrefix:
    """ Contains field definitions for bulk importing prefixes. """
    tablename = 'prefix'
    table = manage.Prefix
    uniqueField = 'prefixid'
    enforce_max_fields = True
    max_num_fields = 7
    min_num_fields = 1

    process = True
    onlyProcess = False
    syntax= '#prefix/mask:nettype[:orgid:netident:usage:description:vlan]\n'

    postCheck = False

    # list of (fieldname,max length,not null,use field)
    fields = [('netaddr',0,True,True),
              ('nettype',0,True,False),
              ('orgid',0,False,False),
              ('netident',0,False,False),
              ('usage',0,False,False),
              ('description',0,False,False),
              ('vlan',0,False,False)]

    def checkValidity(cls,field,data):
        """ Checks validity of fields """
        status = BULK_STATUS_OK
        remark = None
        if field == 'netaddr':
            # Valid CIDR?
            try:
                sql = "SELECT '%s'::inet::cidr" % (data,) 
                executeSQL([sql])

                # Already present?
                where = "netaddr='%s'" % (data,)
                prefixes = manage.Prefix.getAll(where)
                if prefixes:
                    status = BULK_STATUS_YELLOW_ERROR
                    remark = "CIDR already present in database."
            
            except psycopg.ProgrammingError:
                status = BULK_STATUS_RED_ERROR
                remark = "Invalid CIDR '" + data + "'"
        if field == 'nettype':
            # Only add nettypes we're allowed to
            where = "nettypeid='%s' and edit='t'" % (data,)
            result = manage.Nettype.getAll(where)
            if not result:
                status = BULK_STATUS_RED_ERROR
                remark = "Invalid nettype '" + data + "'"
        if field == 'orgid':
            if data:
                if len(data):
                    try:
                        manage.Org(data).load()
                    except forgetSQL.NotFound:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Organisation '" + data + "' not found in database"
        if field == 'usage':
            if data:
                if len(data):
                    try:
                        manage.Usage(data).load()
                    except forgetSQL.NotFound:
                        status = BULK_STATUS_RED_ERROR
                        remark = "Usage '" + data + "' not found in database"
 
        return (status,remark)
    checkValidity = classmethod(checkValidity)

    def preInsert(cls,row):
        """ Changes row data before inserting. Removes empty fields. """
        fields = {}
        if row.has_key('nettype'):
            if len(row['nettype']):
                fields['nettype'] = row['nettype']
            #del(row['nettype'])

        if row.has_key('orgid'):
            if len(row['orgid']):
                fields['orgid'] = row['orgid']
            #del(row['orgid'])

        if row.has_key('netident'):
            if len(row['netident']):
                fields['netident'] = row['netident']
            #del(row['netident'])

        if row.has_key('usage'):
            if len(row['usage']):
                fields['usageid'] = row['usage']
            #del(row['usage'])

        if row.has_key('description'):
            if len(row['description']):
                fields['description'] = row['description']
            #del(row['description'])

        if row.has_key('vlan'):
            try:
                vlan = int(row['vlan'])
                fields['vlan'] = row['vlan']
            except:
                vlan = None
            #del(row['vlan'])

        vlanid = addEntryFields(fields,
                                'vlan',
                                ('vlanid','vlan_vlanid_seq'))

        row['vlanid'] = str(vlanid)
        return row
 
    preInsert = classmethod(preInsert)

# Class representing a list of entries, used by the template
class selectList:
    """ Used by the template to display a list of entries. Only used by
        bulk import. Could be replaced by the more flexible entryList
        class for this purpose. """

    # Text and controlnames for the action bar
    textAdd = 'Add new'
    textEdit = 'Edit selected'
    textDelete = 'Delete selected'
    cnameAdd = 'submit_add'
    cnameEdit = 'submit_edit'
    cnameDelete = 'submit_delete'
    cnameChk = 'checkbox_id'
    # Delete controls
    cnameDeleteConfirm = 'confirm_delete'
    textDeleteConfirm = 'Delete'
    # Bulk controls
    cnameBulkConfirm = 'confirm_bulk'
    textBulkConfirm = 'Import'
    # Hidden id control
    cnameHiddenId = 'hidden_id'
    cnameHiddenData = 'hidden_data'
    # List rows where
    where = None

    def __init__(self):
        # bulk confirm list?
        self.isBulkList = False
        self.hiddenIdValue = None
        # is this a confirm delete list?
        self.isDeleteList = False
        # list of entries to delete
        self.deleteList = []
        # For the template
        self.method = 'post'
        self.action = None
        self.error = None
        self.status = None
        self.backlink = None

        # Variables that must be filled before passing to the template
        self.title = None
        self.headings = []
        self.rows = []

        # Variables used by fill()
        self.table = None
        self.idcol = None
        self.orderBy = None
        self.tablename = ''

    def fill(self):
        " Fill the headings and rows lists "
    
        # fill headings
        self.headings = []
        if not self.isDeleteList:
            self.headings = ['Select']
        for heading,column,link in self.columns:    
            self.headings.append(heading)

        # fill rows
        entries = []
        if not self.isDeleteList:
            entries = self.table.getAllIterator(orderBy=self.orderBy,
                                                where=self.where)
        else:
            for id in self.deleteList:
                entries.append(self.table(id))

        for entry in entries:
            id = getattr(entry,self.idcol)

            row = []
            for heading,column,link in self.columns:
                if link:
                    eid = id
                    if not type(eid) is str:
                        eid = str(id)
                    row.append(([getattr(entry,column)],BASEPATH + self.tablename + '/edit/' + eid))
                else:
                    text = []
                    if type(column) is str:
                        text = [getattr(entry,column)]
                    else:
                        sectable,secidfield,sectextfield = column
                        iter = sectable.getAllIterator(where=secidfield + \
                                        "='" + eid + "'")
                        for i in iter:
                            text.append(getattr(i,sectextfield)) 
                    row.append((text,None))
            self.rows.append((id,row))  
