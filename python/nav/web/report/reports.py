#
# Copyright (C) 2003-2005 Norwegian University of Science and Technology
# Copyright (C) 2008-2012 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""Handling web requests for the Report subsystem."""


from IPy import IP

from operator import itemgetter
from time import localtime, strftime
import copy
import csv
from django.http import HttpResponse
import os
import os.path
import re
import string
import urllib

os.environ['DJANGO_SETTINGS_MODULE'] = 'nav.django.settings'
from django.core.cache import cache

from IPy import IP
from nav import db
from nav.report.IPtree import getMaxLeaf, buildTree
from nav.report.generator import Generator, ReportList
from nav.report.matrixIPv4 import MatrixIPv4
from nav.report.matrixIPv6 import MatrixIPv6
from nav.report.metaIP import MetaIP
from nav.web import redirect
from nav.web import state
from nav.web.URI import URI
from nav.web.templates.MatrixScopesTemplate import MatrixScopesTemplate
from nav.web.templates.ReportListTemplate import ReportListTemplate
from nav.web.templates.ReportTemplate import ReportTemplate, MainTemplate
from nav.web.encoding import encoded_output
import nav.path

config_file_package = os.path.join(nav.path.sysconfdir, "report/report.conf")
config_file_local = os.path.join(nav.path.sysconfdir, "report/report.local.conf")
frontFile = os.path.join(nav.path.sysconfdir, "report/front.html")

def fix_report_urlpath(func):
    """Decorates report's mod_python handler to fix strange URLs.

    report is very picky about URLs, and there is no URL magic helping us
    anywhere in mod_python.  Only the following path patterns allow hyperlinks
    within reports to function properly:

    * /report/
    * /report/(?P<report_name>)

    I.e. the report front page path must always end in a slash, while any
    report page must never end in a slash.  This works some redirect magic on
    requests with non-conforming paths. Looking forward to replace this crazy
    voodoo with Django's sweet URL magic!

    """
    from functools import wraps
    import logging
    from urlparse import urlparse, ParseResult
    logger = logging.getLogger(__name__)
    multislash = re.compile(r'/+')

    @wraps(func)
    def _wrapper(request, *args, **kwargs):
        url = urlparse(request.unparsed_uri)
        elements = [e for e in multislash.split(url.path) if e]
        if len(elements) > 1:
            path = '/%s/%s' % (elements[0], elements[-1])
        else:
            path = '/%s/' % elements[0]

        if path != url.path:
            url = ParseResult(url.scheme, url.netloc, path,
                              url.params, url.query, url.fragment)
            logger.warning("fixing broken url: %r -> %r",
                           request.unparsed_uri, url.geturl())
            redirect(request, url.geturl())
        return func(request, *args, **kwargs)

    return _wrapper

@fix_report_urlpath
@encoded_output
def handler(req):

    (report_name, export_delimiter, uri, nuri) = arg_parsing(req)

    if report_name == "report" or report_name == "index":
        page = MainTemplate()
        req.content_type = "text/html"
        req.send_http_header()
        page.path = [("Home", "/"), ("Report", False)]
        page.title = "Report - Index"
        page.content = lambda:file(frontFile).read()
        req.write(page.respond())

    elif report_name == "matrix":
        matrix_report(req)

    elif report_name == "reportlist":
        report_list(req)

    else:
        make_report(req, report_name, export_delimiter, uri, nuri)

    return HttpResponse()



def arg_parsing(request):

    uri = request.unparsed_uri
    nuri = URI(uri)
    export_delimiter = None

    # These arguments and their friends will be deleted
    remove = []

    # Finding empty values
    for key, val in nuri.args.items():
        if val == "":
            remove.append(key)

    if 'exportcsv' in nuri.args and 'export' in nuri.args:
        delimiter = urllib.unquote(nuri.args['export'])
        # Remember to match against 'page.delimiters'
        match = re.search("(\,|\;|\:|\|)", delimiter)
        if match:
            export_delimiter = match.group(0)
        else:
            remove.append('export')
            remove.append('exportcsv')

    # Deleting empty values
    for r in remove:
        if nuri.args.has_key(r):
            del(nuri.args[r])
        if nuri.args.has_key("op_"+r):
            del(nuri.args["op_"+r])
        if nuri.args.has_key("not_"+r):
            del(nuri.args["not_"+r])

    # Redirect if any arguments were removed
    if len(remove):
        redirect(request, nuri.make())

    match = re.search("\/(\w+?)(?:\/$|\?|\&|$)", request.uri)

    if match:
        report_name = match.group(1)
    else:
        report_name = "report"

    return (report_name, export_delimiter, uri, nuri)



def matrix_report(request):

    request.content_type = "text/html"

    argsdict = request.GET or {}

    scope = None
    if argsdict.has_key("scope") and argsdict["scope"]:
        scope = IP(argsdict["scope"])
    else:
        # Find all scopes in database.
        connection = db.getConnection('webfront','manage')
        database = connection.cursor()
        database.execute("SELECT netaddr FROM prefix INNER JOIN vlan USING (vlanid) WHERE nettype='scope'")
        databasescopes = database.fetchall()

        if len(databasescopes) == 1:
            # If there is a single scope in the db, display that
            scope = IP(databasescopes[0][0])
        else:
            # Otherwise, show an error or let the user select from
            # a list of scopes.
            page = MatrixScopesTemplate()
            page.path = [("Home", "/"), ("Report", "/report/"),
                         ("Subnet matrix", False)]
            page.scopes = []
            for scope in databasescopes:
                page.scopes.append(scope[0])

            return HttpResponse(page.respond())

    # If a single scope has been selected, display that.
    if scope is not None:
        show_unused_addresses = True

        if argsdict.has_key("show_unused_addresses"):
            boolstring = argsdict["show_unused_addresses"]
            if boolstring == "True":
                show_unused_addresses = True
            elif boolstring == "False":
                show_unused_addresses = False

        matrix = None
        tree = buildTree(scope)

        if scope.version() == 6:
            end_net = getMaxLeaf(tree)
            matrix = MatrixIPv6(scope, end_net=end_net)

        elif scope.version() == 4:
            end_net = None

            if scope.prefixlen() < 24:
                end_net = IP("/".join([scope.net().strNormal(),"27"]))
                matrix = MatrixIPv4(scope, show_unused_addresses,
                                    end_net=end_net)

            else:
                max_leaf = getMaxLeaf(tree)
                bits_in_matrix = max_leaf.prefixlen()-scope.prefixlen()
                matrix = MatrixIPv4(scope, show_unused_addresses,
                                    end_net=max_leaf,
                                    bits_in_matrix=bits_in_matrix)

        else:
            raise UnknownNetworkTypeException, "version: " + str(scope.version())
        matrix_template_response = matrix.getTemplateResponse()

        # Invalidating the MetaIP cache to get rid of processed data.
        MetaIP.invalidateCache()

        return HttpResponse(matrix_template_response)



def report_list(request):

    page = ReportListTemplate()
    request.content_type = "text/html"

    # Default config
    report_list = ReportList(config_file_package).getReportList()
    map(itemgetter(1), report_list)
    report_list = sorted(report_list, key=itemgetter(1))

    # Local config
    report_list_local = ReportList(config_file_local).getReportList()
    map(itemgetter(1), report_list_local)
    report_list_local = sorted(report_list_local, key=itemgetter(1))

    name = "Report List"
    name_link = "reportlist"
    page.path = [("Home", "/"), ("Report", "/report/"), (name, "/report/" + name_link)]
    page.title = "Report - " + name
    page.report_list = report_list
    page.report_list_local = report_list_local

    return HttpResponse(page.respond())



def make_report(request, report_name, export_delimiter, uri, nuri):

    # Initiating variables used when caching
    report = contents = neg = operator = adv = dbresult = result_time = None

    # Deleting meta variables from uri to help identifying if the report
    # asked for is in the cache or not.
    nuri.setArguments(['offset', 'limit', 'export', 'exportcsv'], '')
    for key, val in nuri.args.items():
        if val == "":
            del nuri.args[key]

    uri_strip = nuri.make()
    username = request.session['user']['login']
    mtime_config = os.stat(config_file_package).st_mtime + os.stat(config_file_local).st_mtime
    cache_name = 'report_' + username + '_' + str(mtime_config)

    gen = Generator()
    # Caching. Checks if cache exists for this user, that the cached report is
    # the one requested and that config files are unchanged.
    if cache.get(cache_name) and cache.get(cache_name)[0] == uri_strip:
        report_cache = cache.get(cache_name)
        dbresult_cache = report_cache[7]
        config_cache = report_cache[6]
        (report, contents, neg, operator, adv) = gen.makeReport(report_name, None, None, uri, config_cache, dbresult_cache)
        result_time = cache.get(cache_name)[8]
        dbresult = dbresult_cache

    else: # Report not in cache, fetch data from DB
        (report, contents, neg, operator, adv, config, dbresult) = gen.makeReport(report_name, config_file_package, config_file_local, uri, None, None)
        result_time = strftime("%H:%M:%S", localtime())
        cache.set(cache_name, (uri_strip, report, contents, neg, operator, adv, config, dbresult, result_time))


    if export_delimiter:
        generate_export(request, report, report_name, export_delimiter)

    else:
        request.content_type = "text/html"
        request.send_http_header()
        page = ReportTemplate()
        page.result_time = result_time
        page.report = report
        page.contents = contents
        page.operator = operator
        page.neg = neg

        namename = ""
        if report:
            namename = report.title
            if not namename:
                namename = report_name
            namelink = "/report/"+report_name

        else:
            namename = "Error"
            namelink = False

        page.path = [("Home", "/"), ("Report", "/report/"),
                     (namename, namelink)]
        page.title = "Report - "+namename
        old_uri = request.unparsed_uri
        page.old_uri = old_uri

        if adv:
            page.adv_block = True
        else:
            page.adv_block = False

        if report:
            if old_uri.find("?")>0:
                old_uri += "&"
            else:
                old_uri += "?"
            page.old_uri = old_uri

            #### A maintainable list of variables sent to template
            # Searching
            page.operators = {"eq": "=",
                              "like": "~",
                              "gt": "&gt;",
                              "lt": "&lt;",
                              "geq": "&gt;=",
                              "leq": "&lt;=",
                              "between": "[:]",
                              "in":"(,,)",
                              }
            page.operatorlist = ["eq", "like", "gt", "lt", "geq", "leq",
                                 "between", "in"]
            page.descriptions = {
                "eq": "equals",
                "like": "contains substring (case-insensitive)",
                "gt": "greater than",
                "lt": "less than",
                "geq": "greater than or equals",
                "leq": "less than or equals",
                "between": "between (colon-separated)",
                "in":"is one of (comma separated)",
                }
            # CSV Export dialects/delimiters
            page.delimiters = (",", ";", ":", "|")

        request.write(page.respond())



def generate_export(req, report, report_name, export_delimiter):
    def _cellformatter(cell):
        if isinstance(cell.text, unicode):
            return cell.text.encode('utf-8')
        else:
            return cell.text

    req.content_type = "text/x-csv; charset=utf-8"
    req.headers_out["Content-Type"] = "application/force-download"
    req.headers_out["Content-Disposition"] = (
        "attachment; filename=report-%s-%s.csv" %
        (report_name, strftime("%Y%m%d", localtime()))
        )
    req.send_http_header()
    writer = csv.writer(req, delimiter=export_delimiter)

    # Make a list of headers
    header_row = [_cellformatter(cell) for cell in report.table.header.cells]
    writer.writerow(header_row)

    # Make a list of lists containing each cell. Considers the 'hidden' option
    # from the config.
    rows = []
    for row in report.table.rows:
        rows.append([_cellformatter(cell) for cell in row.cells])
    writer.writerows(rows)

    req.write("")



class UnknownNetworkTypeException(Exception): pass
