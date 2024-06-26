# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Ntp(Plugin):

    short_desc = 'Network Time Protocol'
    plugin_name = "ntp"
    profiles = ('system', 'services')

    packages = ('ntp',)

    def setup(self):

        self.add_copy_spec("/etc/ntp.conf", tags="ntp_conf")

        self.add_copy_spec([
            "/etc/ntp/step-tickers",
            "/etc/ntp/ntpservers"
        ])
        self.add_cmd_output([
            "ntptime",
            "ntpq -pn"
        ], cmd_as_tag=True)

        ids = self.collect_cmd_output('ntpq -c as')
        if ids['status'] == 0:
            for asid in [i.split()[1] for i in ids['output'].splitlines()[3:]]:
                self.add_cmd_output(f"ntpq -c 'rv {asid}'")


class RedHatNtp(Ntp, RedHatPlugin):

    def setup(self):
        super().setup()
        self.add_copy_spec("/etc/sysconfig/ntpd")
        self.add_cmd_output("ntpstat")


class DebianNtp(Ntp, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super().setup()
        self.add_copy_spec('/etc/default/ntp')


# vim: set et ts=4 sw=4 :
