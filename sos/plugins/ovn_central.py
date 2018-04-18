# Copyright (C) 2018 Mark Michelson <mmichels@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import json
import os


class OVNCentral(Plugin):
    """ OVN Northd
    """
    plugin_name = "ovn_central"
    profiles = ('network', 'virt')
    option_list = [
        ('log_dir', 'Directory where OVN logs are found', '', ''),
        ('db_dir', 'Directory where OVN databases are found', '', ''),
        ('runtime_dir', 'Directory where OVN runtime files are found', '', ''),
        ('schema_dir', 'Directory where OVN database schema files are found',
         '', '/usr/share/openvswitch/'),
    ]

    def setup(self):

        all_logs = self.get_option("all_logs")
        limit = self.get_option("log_size")

        log_dir = self.get_option('log_dir')
        if not all_logs:
            self.add_copy_spec([
                '/var/log/containers/openvswitch/*.log',
                '/var/log/openvswitch/*log',
                '/usr/local/var/log/openvswitch/*log'
            ], sizelimit=limit)
            if os.environ.get('OVS_LOGDIR'):
                self.add_copy_spec(os.environ.get('OVS_LOGDIR') + '/*.log',
                                   sizelimit=limit)
            if log_dir:
                self.add_copy_spec(log_dir + '/*.log', sizelimit=limit)
        else:
            self.add_copy_spec([
                log_dir,
                os.environ.get('OVS_LOGDIR'),
                '/var/log/containers/openvswitch',
                '/var/log/openvswitch',
                '/usr/local/var/log/openvswitch'
            ], sizelimit=limit)

        ovs_rundir = os.environ.get('OVS_RUNDIR')
        runtime_dir = self.get_option('runtime_dir')
        for pidfile in ['ovnnb_db.pid', 'ovnsb_db.pid', 'ovn-northd.pid']:
            self.add_copy_spec([
                '/var/lib/openvswitch/ovn/' + pidfile,
                '/usr/local/var/run/openvswitch/' + pidfile,
                '/var/run/openvswitch/' + pidfile,
                '/run/openvswitch/' + pidfile
            ])
            if ovs_rundir:
                self.add_copy_spec(ovs_rundir + '/' + pidfile)
            if runtime_dir:
                self.add_copy_spec(runtime_dir + '/' + pidfile)

        # Some user-friendly versions of DB output
        self.add_cmd_output([
            'ovn-sbctl lflow-list',
            'ovn-nbctl get-ssl',
            'ovn-nbctl get-connection',
            'ovn-sbctl get-ssl',
            'ovn-sbctl get-connection',
        ])

        schema_dir = self.get_option('schema_dir')
        try:
            with open(os.path.join(schema_dir, 'ovn-nb.ovsschema'), 'r') as f:
                db = json.load(f)
                for table in db['tables'].iterkeys():
                    self.add_cmd_output('ovn-nbctl list %s' % table)
        except IOError, NameError:
            # skip if ovsschema not found or not in json format
            pass

        try:
            with open(os.path.join(schema_dir, 'ovn-sb.ovsschema'), 'r') as f:
                db = json.load(f)
                for table in db['tables'].iterkeys():
                    # Don't include Logical_Flow because we'll use the more
                    # user-friendly `ovn-sbctl lflow-list` command to get that
                    # information
                    if table != 'Logical_Flow':
                        self.add_cmd_output('ovn-sbctl list %s' % table)
        except IOError, NameError:
            # skip if ovsschema not found or not in json format
            pass

        self.add_copy_spec("/etc/sysconfig/ovn-northd")

        ovs_dbdir = os.environ.get('OVS_DBDIR')
        db_dir = self.get_option('db_dir')
        for dbfile in ['ovnnb_db.db', 'ovnsb_db.db']:
            self.add_copy_spec([
                '/var/lib/openvswitch/ovn/' + dbfile,
                '/usr/local/var/run/openvswitch/' + dbfile,
                '/etc/openvswitch/' + dbfile,
                '/var/lib/openvswitch/' + dbfile
            ])
            if ovs_dbdir:
                self.add_copy_spec(ovs_dbdir + '/' + pidfile)
            if db_dir:
                self.add_copy_spec(db_dir + '/' + pidfile)

        self.add_journal(units="ovn-northd")


class RedHatOVNCentral(OVNCentral, RedHatPlugin):

    packages = ('openvswitch-ovn-central', )


class DebianOVNCentral(OVNCentral, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-central', )
