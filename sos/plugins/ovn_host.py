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

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OVNHost(Plugin):
    """ OVN Controller
    """
    plugin_name = "ovn_host"
    profiles = ('network', 'virt')
    option_list = [
        ('log_dir', 'Directory where OVN logs are found', '', ''),
        ('runtime_dir', 'Directory where OVN runtime files are found', '', ''),
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

        self.add_copy_spec([
            '/var/lib/openvswitch/ovn/ovn-controller.pid',
            '/usr/local/var/run/openvswitch/ovn-controller.pid',
            '/var/run/openvswitch/ovn-controller.pid',
            '/run/openvswitch/ovn-controller.pid'
        ])
        if os.environ.get('OVS_RUNDIR'):
            self.add_copy_spec(os.environ.get('OVS_RUNDIR') +
                               '/ovn-controller.pid')
        if self.get_option('runtime_dir'):
            self.add_copy_spec(self.get_option('runtime_dir') +
                               '/ovn-controller.pid')

        self.add_copy_spec('/etc/sysconfig/ovn-controller')

        self.add_cmd_output([
            'ovs-ofctl -O OpenFlow13 dump-flows br-int',
            'ovs-vsctl list-br',
            'ovs-vsctl list OpenVswitch',
        ])

        self.add_journal(units="ovn-controller")


class RedHatOVNHost(OVNHost, RedHatPlugin):

    packages = ('openvswitch-ovn-host', )


class DebianOVNHost(OVNHost, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-host', )
