# -*- coding: utf-8 -*-

import sys
import optparse
import transaction

from ZODB.POSException import ConflictError
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManager import setSecurityPolicy
from zope.component.hooks import setSite
from Testing.makerequest import makerequest

from Products.CMFCore.tests.base.security import PermissiveSecurityPolicy, OmnipotentUser
from Products.Archetypes.utils import shasattr
from Products.CMFEditions.utilities import dereference


version = '0.2.1'
usage = "usage: /your/instance run clean_history.py [options] [sites]"
description = "Cleanup CMFEdition history in Plone sites. Default is: all sites in the database."
p = optparse.OptionParser(usage=usage, version="%prog " + version, description=description,
                          prog="clean_history")
p.add_option('--portal-type', '-p', dest="portal_types", default=[], action="append", metavar="PORTAL_TYPE",
             help="select to cleanup only histories for a kind of portal_type. Default is \"all types\". "
                  "Can be called multiple times.")
p.add_option('--keep-history', '-k', type="int", dest="keep_history", default=0, metavar="HISTORY_SIZE",
             help='Before purging, temporary set the value of "maximum number of versions to keep in the storage" to this '
                  'value in the portal_purgehistory. Default is: do not change the value. In any case, the original value '
                  'will be restored.')
p.add_option('--verbose', '-v', action="store_true", default=False,
             help="Show verbose output, for every cleaned content's history.")

args = sys.argv[1:]
args = [arg for arg in args
        if arg != '-c' and not arg.endswith('clean_history.py')]

options, psite = p.parse_args(args)
pp_type = options.portal_types

try:
    foo = app
except NameError:
    print p.print_help()
    sys.exit(1)

def spoofRequest(app):
    """
    Make REQUEST variable to be available on the Zope application server.

    This allows acquisition to work properly
    """
    _policy=PermissiveSecurityPolicy()
    _oldpolicy=setSecurityPolicy(_policy)
    newSecurityManager(None, OmnipotentUser().__of__(app.acl_users))
    return makerequest(app)

# Enable Faux HTTP request object
app = spoofRequest(app)

sites = [(id, site) for (id, site) in app.items()
         if hasattr(site, 'meta_type') and site.meta_type=='Plone Site']

print 'Starting analysis for %s. Types to cleanup: %s' % (not psite and 'all sites' or ', '.join(psite),
                                                          not pp_type and 'all' or ', '.join(pp_type))
for id, site in sites:
    setSite(site)
    if not psite or id in psite:
        print "Analyzing %s" % id
        policy = site.portal_purgepolicy
        portal_repository = site.portal_repository
        if policy.maxNumberOfVersionsToKeep==-1 and not options.keep_history:
            print "... maxNumberOfVersionsToKeep is -1; skipping"
            continue

        old_maxNumberOfVersionsToKeep = policy.maxNumberOfVersionsToKeep
        if options.keep_history:
            print "... Putting maxNumberOfVersionsToKeep from %d to %s" % (old_maxNumberOfVersionsToKeep,
                                                                           options.keep_history)
            policy.maxNumberOfVersionsToKeep = options.keep_history

        catalog = site.portal_catalog
        if pp_type:
            results = catalog.unrestrictedSearchResults(portal_type=pp_type)
        else:
            results = catalog.unrestrictedSearchResults()

        for x in results:
            if options.verbose:
                print "... cleaning history for %s (%s)" % (x.getPath(), x.portal_type)
            try:
                obj = x.getObject()
                isVersionable = portal_repository.isVersionable(obj)
                if isVersionable:
                    obj, history_id = dereference(obj)
                    policy.beforeSaveHook(history_id, obj)
                    if shasattr(obj, 'version_id') and options.keep_history<=1:
                        del obj.version_id
                    if options.verbose:
                        print "... cleaned!"
            except ConflictError:
                raise
            except Exception, inst:
                # sometimes, even with the spoofed request, the getObject failed
                print "ERROR purging %s (%s)" % (x.getPath(), x.portal_type)
                print "    %s" % inst

        policy.maxNumberOfVersionsToKeep = old_maxNumberOfVersionsToKeep
        transaction.commit()

print 'End analysis'
sys.exit(0)
