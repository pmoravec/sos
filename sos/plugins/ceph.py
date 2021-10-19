# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin
from socket import gethostname
from sos.utilities import (sos_get_command_output, is_executable)
import re


class Ceph(Plugin, RedHatPlugin, UbuntuPlugin):
    """CEPH distributed storage
    """

    plugin_name = 'ceph'
    profiles = ('storage', 'virt', 'containers')
    ceph_hostname = gethostname()

    packages = (
        'ceph',
        'ceph-mds',
        'ceph-common',
        'libcephfs1',
        'ceph-fs-common',
        'calamari-server',
        'librados2'
    )

    services = (
        'ceph-nfs@pacemaker',
        'ceph-mds@%s' % ceph_hostname,
        'ceph-mon@%s' % ceph_hostname,
        'ceph-mgr@%s' % ceph_hostname,
        'ceph-radosgw@*',
        'ceph-osd@*'
    )

    # This check will enable the plugin regardless of being
    # containerized or not
    files = (
        '/etc/ceph/ceph.conf',
    )

    def _find_ceph_containers(self):
        ceph_containers_re = 'ceph-*'
        self.ceph_containers = []
        self.runtime = None
        for runt in ['docker', 'podman']:
            if is_executable(runt):
                self.runtime = runt
                break
        if self.runtime is not None:
            out = sos_get_command_output('%s ps' % self.runtime)
            if out['status'] == 0:
                for ent in out['output'].splitlines()[1:]:
                    # container name is the latest item
                    ent = ent.split()[-1]
                    if re.match(ceph_containers_re, ent):
                        self.ceph_containers.append(ent)

    def check_enabled(self):
        # check if a ceph container is running
        self._find_ceph_containers()
        if self.ceph_containers:
            return True
        # if not, fallback to enabledness per services/packages/files
        return super(Ceph, self).check_enabled()

    def setup(self):
        all_logs = self.get_option("all_logs")

        if not all_logs:
            self.add_copy_spec([
                "/var/log/ceph/*.log",
                "/var/log/radosgw/*.log",
                "/var/log/calamari/*.log"
            ])
        else:
            self.add_copy_spec([
                "/var/log/ceph/",
                "/var/log/calamari",
                "/var/log/radosgw"
            ])

        self.add_copy_spec([
            "/etc/ceph/",
            "/etc/calamari/",
            "/var/lib/ceph/",
            "/run/ceph/"
        ])

        self.add_cmd_output([
            "ceph mon stat",
            "ceph mon_status",
            "ceph quorum_status",
            "ceph mgr module ls",
            "ceph mgr metadata",
            "ceph osd metadata",
            "ceph osd erasure-code-profile ls",
            "ceph report",
            "ceph osd crush show-tunables",
            "ceph-disk list",
            "ceph versions",
            "ceph features",
            "ceph insights",
            "ceph osd crush dump",
            "ceph -v",
            "ceph-volume lvm list",
            "ceph crash stat",
            "ceph crash ls",
            "ceph config log",
            "ceph config generate-minimal-conf",
            "ceph config-key dump",
        ])

        ceph_cmds = [
            "status",
            "health detail",
            "osd tree",
            "osd stat",
            "osd df tree",
            "osd dump",
            "osd df",
            "osd perf",
            "osd blocked-by",
            "osd pool ls detail",
            "osd numa-status",
            "device ls",
            "mon dump",
            "mgr dump",
            "mds stat",
            "df",
            "df detail",
            "fs ls",
            "fs dump",
            "pg dump",
            "pg stat",
        ]

        ceph_osd_cmds = [
            "ceph-volume lvm list",
        ]

        self.add_cmd_output([
            "ceph %s --format json-pretty" % s for s in ceph_cmds
        ], subdir="json_output")

        for service in self.services:
            self.add_journal(units=service)

        self.add_forbidden_path([
            "/etc/ceph/*keyring*",
            "/var/lib/ceph/*keyring*",
            "/var/lib/ceph/*/*keyring*",
            "/var/lib/ceph/*/*/*keyring*",
            "/var/lib/ceph/osd",
            "/var/lib/ceph/mon",
            # Excludes temporary ceph-osd mount location like
            # /var/lib/ceph/tmp/mnt.XXXX from sos collection.
            "/var/lib/ceph/tmp/*mnt*",
            "/etc/ceph/*bindpass*"
        ])

        # If containerized, run commands in containers
        if self.ceph_containers:
            # Avoid retrieving multiple times the same data
            got_ceph_cmds = False
            for container in self.ceph_containers:
                if re.match("ceph-(mon|rgw|osd)", container) and \
                        not got_ceph_cmds:
                    self.add_cmd_output([
                        "%s exec -t %s ceph %s" % (self.runtime, container, s)
                        for s in ceph_cmds
                    ])
                    got_ceph_cmds = True
                if re.match("ceph-osd", container):
                    self.add_cmd_output([
                        "%s exec -t %s %s" % (self.runtime, container, s)
                        for s in ceph_osd_cmds
                    ])
                    break
        # Not containerized
        else:
            self.add_cmd_output([
                "ceph %s" % s for s in ceph_cmds
            ])


# vim: set et ts=4 sw=4 :
