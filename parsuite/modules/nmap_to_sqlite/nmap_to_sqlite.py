from time import sleep
from parsuite.core.suffix_printer import sprint, esprint
from parsuite.core.argument import (Argument,
        DefaultArguments,
        ArgumentGroup,
        MutuallyExclusiveArgumentGroup)
from pathlib import Path
import pdb
from django.core.management import execute_from_command_line
from parsuite.abstractions.xml.generic.network_host import *
import hashlib


help = '''Convert XML files generated by NMap to an SQLite
database.
'''

args = [
    DefaultArguments.input_files,
    Argument('--sqlite-db-file', '-db',
        help='Output database file'),
    Argument('--db-config-file',
        required=False,
        help='File containing a JSON configuration object. This is ' \
        'passed directly to Django\'s ORM. See Django\' ' \
        'settings documentation for possible values.'),
    Argument('--verbose',
        action='store_true',
        help='Show verbose output'),
    Argument('--disable-prune',
        action='store_true',
        help='Disable pruning of XML files'),
    Argument('--debug',
        action='store_true',
        help='Drop to a shell upon exception during DB processing'),
    Argument('--shell',
        action='store_true',
        help='Drop to an IPython shell to interact with the ' \
            'Django ORM instead of creating a new database'),
]

def getBaseDir():
    '''Get the base working directory for the current module.

    - returns a pathlib.Path object
    '''

    return Path(__file__).parent.absolute()

def purgeMigrations(base_dir):
    '''Purge all migrations from the migrations directory to enusre
    that a fresh DB is created each time.

    This may not be necessary...need to research
    '''

    for f in Path(base_dir / 'nmap' / 'migrations').glob('*.py'):
        if f.name.startswith('_'): continue
        f.unlink()

def configure(db_config,base_dir,migrate=True):
    '''Configure a fake Django application and initialize an SQLite
    database to capture the scan data.
    '''
    import django
    from django.conf import settings
    from django.apps.config import AppConfig

    # =========================
    # CONFIGURE THE APPLICATION
    # =========================
    
    INSTALLED_APPS=[
        'nmap',
    ]

    DATABASES = {
        'default': db_config
    }
    
    settings.configure(
        INSTALLED_APPS = INSTALLED_APPS,
        DATABASES = DATABASES,
    )

    # =======================
    # INITIALIZE THE DATABASE
    # =======================

    if migrate:

        execute_from_command_line([base_dir,'makemigrations'])
        execute_from_command_line([base_dir,'migrate'])

def processHost(host,import_info,models):
    '''
    Process a network host and make relevant associations for
    it in a database using Django's ORM. Database configuraitons
    must be applied using django.conf.settings.

    - host - network_host.Host object generated by a parser
    module from Parsuite
    '''

    # =================================
    # INITIALIZE THE HOST AND ADDRESSES
    # =================================

    dbhost, mac, ipv4, ipv6 = None, None, None, None

    # ==================
    # HANDLE MAC ADDRESS
    # ==================
    '''
    - MAC is not associated with a host, but an IP address
    - Collect that information now and prepare a record, if
      necessary
    '''

    if host.mac_address:

        mac, mac_created = models.MACAddress.objects.uoc(
                import_info=import_info,
                address=host.mac_address)

    # ===================
    # HANDLE IP ADDRESSES
    # ===================

    # IPv4
    if host.ipv4_address:

        ipv4, ipv4_created = models.IPAddress.objects.uoc(
                import_info=import_info,
                address=host.ipv4_address,
                addrtype='ipv4')

        if not dbhost and ipv4.host:
            dbhost = ipv4.host

        # Update the IPv4 MAC
        '''
        - A MAC address can be associated with multiple IP addresses
        - This accomidation is made in cases where ProxyARP is being
          used for multiple upstream hosts or when a firewall/router
          is responding to all ARP requests with its IP address

        update() will create a historical record of the
        '''
        if mac and ipv4.address != mac:
            try:
                ipv4.update(import_info, mac_address=mac)
            except:
                pdb.set_trace()

    # IPv6
    if host.ipv6_address:

        ipv6, ipv6_created = models.IPAddress.objects.uoc(
                import_info=import_info,
                ip_address=host.ipv6_address,
                addrtype='ipv6')

        if not dbhost and ipv6.host:
            dbhost = ipv6.host

        # Update the IPv6 MAC
        # See IPv4 section above for notes on why this is a thing
        if mac and ipv4.mac_address != mac:
            ipv6.update(import_info, mac_address=mac)

    # Skip if no addresses were recovered from the host
    if not mac and not ipv4 and not ipv6:
        return False

    # ==================================================
    # CREATE/UPDATE HOST AND ASSOCIATE WITH IP ADDRESSES
    # ==================================================

    if dbhost:
        # Update the history for a given host and save the changes

        dbhost.updateHistory(import_info)
        dbhost.save()

    if not dbhost:
        # Create a new host for the address

        dbhost = models.Host.objects.create(
            import_info=import_info,
            status=host.status,
            status_reason=host.status_reason)

        # Associate the addresses with the new host
        # No history occurs here because all future lookups for the
        # IP addresses will return the previous dbhost
        if ipv4:
            ipv4.host = dbhost
            ipv4.save()
    
        if ipv6:
            ipv6.host = dbhost
            ipv6.save()

    # ================
    # HANDLE HOSTNAMES
    # ================

    for hn in host.hostnames:

        addresses = []

        if ipv4: addresses.append(ipv4)
        if ipv6: addresses.append(ipv6)

        dbhn, created = models.Hostname.objects.uoc(
            import_info=import_info,
            name=hn)
        dbhn.addresses.add(*addresses)

    # ============
    # HANDLE PORTS
    # ============

    for protocol in ['ip','tcp','udp','sctp']:

        ports = getattr(host, f'{protocol}_ports')

        for port in ports.values():

            defaults = {
                'portid':port.portid,
                'state':port.state,
                'protocol':protocol,
                'reason':port.reason,
            }

            # get_or_create each of the ports
            if ipv4:

                dbport, created = models.Port.objects.uoc(
                    defaults=defaults,
                    import_info=import_info,
                    address=ipv4,
                    portid=port.portid)

            if ipv6:

                dbport, created = models.Port.objects.uoc(
                    defaults=defaults,
                    import_info=import_info,
                    address=ipv6,
                    portid=port.portid)

            # ==============
            # HANDLE SCRIPTS
            # ==============

            if port.service:

                defaults = {
                    k:getattr(port.service,k) for k in
                    Service.ATTRIBUTES
                }

                dbservice, created = models.Service.objects \
                    .uoc(
                        defaults=defaults,
                        import_info=import_info,
                        port=dbport
                    )

            # ===============
            # HANDLE SERVICES
            # ===============

            if port.scripts:

                for script in port.scripts:

                    dbscript, created = models.Script.objects.uoc(
                        defaults={
                            'nmap_id':script.id,
                            'output':script.output,
                            'import_info':import_info
                        },
                        import_info=import_info,
                        port=dbport)


def createFileInfo(path,models):
    '''Create a FileInfo record. This a distinct FileIO object is
    used because LXML supposedly implements compression to make
    parsing faster when initiated from a string instead of a file.

    - path - str/Path - Path to the file that is being fingerprinted
    - models - reference to nmap.models
    '''

    # =======================
    # GATHER FILE INFORMATION
    # =======================

    sha256sum = None
    with open(path,'rb') as infile:
        h = hashlib.sha256()
        h.update(infile.read())
        sha256sum = h.digest().hex()

    # Create and save the import information
    import_info, created = models.ImportInfo \
        .objects.get_or_create(
            file_path=path.absolute(),
            sha256sum=sha256sum
        )

    return import_info

def parse(input_files=None, sqlite_db_file=None, shell=None, verbose=None,
        process_count=None, db_config_file=None, disable_prune=False,
        debug=False, *args, **kwargs):

    # ================================
    # IMPORT LXML AS THE XML PROCESSOR
    # ================================

    try:
        import lxml.etree as ET
    except:
        # This probably won't work
        import xml.etree.ElementTree as ET

    # =========================
    # ADDITIONAL MODULE IMPORTS
    # =========================

    from parsuite.parsers.nmap import parse_nmap, iter_nmap
    from parsuite import helpers
    import sys
    import logging
    from copy import copy
    from pprint import PrettyPrinter
    pp = PrettyPrinter(indent=4)

    # =============================================
    # UPDATE THE CURRENT PATH TO INCLUDE THE MODULE
    # =============================================

    # This makes it possible for Django to find the
    # nmap module
    base_dir = getBaseDir()
    sys.path.append(str(base_dir))

    # =================
    # CONFIGURE LOGGING
    # =================

    LOG_FORMAT='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logger = logging.getLogger('parsuite.nmap_to_sqlite')
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    if verbose: logger.setLevel(logging.DEBUG)

    # ======================
    # CONFIGURE THE DATABASE
    # ======================

    if sqlite_db_file and db_config_file:

        raise Exception(
            'sqlite_db_file and db_config_file are mutually exclusive' \
            'options')

    if db_config_file:

        import json
        with open(db_config_file) as infile:
            db_config = json.load(infile)

    else:

        db_config = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': sqlite_db_file,
        }

    import nmap
    esprint('Current database configuration:\n')

    _config = copy(db_config)
    if 'PASSWORD' in _config:
        _config['PASSWORD'] = '*'*10
    pp.pprint(_config)
    print()

    # ====================
    # MIGRATE THE DATABASE
    # ====================
    
    purgeMigrations(base_dir)
    esprint('Configuring the environment')
    print()
    configure(db_config, base_dir, migrate=not shell)

    # ====================
    # HANDLE SHELL REQUEST
    # ====================

    if shell:
        execute_from_command_line([base_dir,'shell'])
        return 0

    # ==========================
    # BEGIN PROCESSING XML FILES
    # ==========================

    print()
    esprint('Beginning execution')

    # =======================================
    # PREPARE THE XSLT IF PRUNE ISNT DISABLED
    # =======================================

    xslt, transform = None, None
    if not disable_prune:
    
        xslt = base_dir / 'open_only.xsl'
        if not xslt.exists():
            raise Exception(f'XSL file not found: {xslt}')
        xslt = ET.parse(str(xslt))
        transform = ET.XSLT(xslt)

    # ==========================
    # BEGIN PROCESSING XML FILES
    # ==========================

    for input_file in input_files:

        file_info = None

        esprint(f'Processing: {input_file}')

        # ===================================
        # PRUNE INPUT FILES OF NON-OPEN PORTS
        # ===================================

        if not disable_prune:

            # =======================
            # HANDLE OUTPUT DIRECTORY
            # =======================

            to_prune = Path(input_file)
            out_prune = Path(f'{to_prune}.pruned')
            reuse = False

            if not to_prune.exists():
                esprint(f'File doesn\'t exist: {to_prune}')

            try:

                # =================================
                # ATTEMPT TO REUSE PRUNED XML FILES
                # =================================

                if out_prune.exists() and out_prune.is_file():

                    reuse = True
                    esprint(f'Using previously pruned file {out_prune}')

                    try:

                        # Parse the XML file to an ETree
                        tree = ET.parse(str(out_prune))
                        file_info = createFileInfo(out_prune,nmap.models)

                    except Exception as e:

                        # Something went wrong...try again
                        reuse = False
                        esprint(f'Failed to parse XML: {out_prune} ({e})')
                        esprint(f'Parsing XML: {to_prune}')
                        tree = ET.parse(str(to_prune))
                        file_info = createFileInfo(to_prune,nmap.models)

                else:

                    # Parse the XML file to an ETree
                    tree = ET.parse(str(to_prune))
                    file_info = createFileInfo(to_prune,nmap.models)

            except Exception as e:

                # Something went fatally wrong...ignore the file
                # and continue to the next one
                esprint(f'Failed to parse XML: {to_prune} ({e})')
                continue

            # =============
            # PRUNE RECORDS
            # =============

            if not reuse:

                esprint('Pruning the XML document. This may take ' \
                    'some time.')

                tree = transform(tree)

                # =============================
                # WRITE THE PRUNED FILE TO DISK
                # =============================

                esprint('Finished! Writing pruned file to ' \
                    f'disk {out_prune}')

                with open(out_prune, 'wb+') as outfile:
                    outfile.write(ET.tostring(tree, pretty_print=True))
                file_info = createFileInfo(out_prune,nmap.models)

        else:

            # ====================================
            # CONTINUE WITHOUT PRUNING INPUT FILES
            # ====================================

            try:
               tree = ET.parse(input_file)
               file_info = createFileInfo(input_file,nmap.models)
            except Exception as e:
                esprint(f'Failed to parse XML: {input_file}')
                continue

        # =======================================================
        # TRANSLATE THE TREE TO NMAP OBJECTS AND DUMP TO DATABASE
        # =======================================================

        esprint('Populating the database. This may take some time.')

        # Host count for verbose output
        if verbose: count = 0
        for host in iter_nmap(tree, True, True):

            if verbose:

                count += 1
                address = ''

                if host.mac_address:
                    address += f' {host.mac_address}'
                if host.ipv4_address:
                    address += f' {host.ipv4_address}'
                if host.ipv6_address:
                    address += f' {host.ipv6_address}'

                if address: logger.debug(
                    (f'Count: {count} Input File: {input_file} Address: {address}')
                )

            try:
                processHost(host, file_info, nmap.models)
            except Exception as e:
                if debug:
                    import pdb
                    pdb.set_trace()
                else:
                    raise e

    esprint('Purging migrations')
    purgeMigrations(base_dir)
