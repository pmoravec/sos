# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.hostname_map import SoSHostnameMap


class SoSHostnameParser(SoSCleanerParser):

    name = 'Hostname Parser'
    map_file_key = 'hostname_map'
    regex_patterns = [
        r'(((\b|_)[a-zA-Z0-9-\.]{1,200}\.[a-zA-Z]{1,63}(\b|_)))'
    ]

    def __init__(self, config, opt_domains=None):
        self.mapping = SoSHostnameMap()
        super(SoSHostnameParser, self).__init__(config)
        self.mapping.load_domains_from_map()
        self.mapping.load_domains_from_options(opt_domains)
        self.short_names = []
        self.load_short_names_from_mapping()
        self.mapping.set_initial_counts()

    def load_short_names_from_mapping(self):
        """When we load the mapping file into the hostname map, we have to do
        some dancing to get those loaded properly into the "intermediate" dicts
        that the map uses to hold hosts and domains. Similarly, we need to also
        extract shortnames known to the map here.
        """
        for hname in self.mapping.dataset.keys():
            if len(hname.split('.')) == 1:
                # we have a short name only with no domain
                if hname not in self.short_names:
                    self.short_names.append(hname)

    def load_hostname_into_map(self, hostname_string):
        """Force add the domainname found in /sos_commands/host/hostname into
        the map. We have to do this here since the normal map prep approach
        from the parser would be ignored since the system's hostname is not
        guaranteed
        """
        if 'localhost' in hostname_string:
            return
        domains = hostname_string.split('.')
        if len(domains) > 1:
            self.short_names.append(domains[0])
        else:
            self.short_names.append(hostname_string)
        if len(domains) > 3:
            # make sure we implicitly get example.com if the system's hostname
            # is something like foo.bar.example.com
            high_domain = '.'.join(domains[-2:])
            self.mapping.add(high_domain)
        self.mapping.add(hostname_string)

    def load_hostname_from_etc_hosts(self, content):
        """Parse an archive's copy of /etc/hosts, which requires handling that
        is separate from the output of the `hostname` command. Just like
        load_hostname_into_map(), this has to be done explicitly and we
        cannot rely upon the more generic methods to do this reliably.
        """
        lines = content.splitlines()
        for line in lines:
            if line.startswith('#') or 'localhost' in line:
                continue
            hostln = line.split()[1:]
            for host in hostln:
                if len(host.split('.')) == 1:
                    # only generate a mapping for fqdns but still record the
                    # short name here for later obfuscation with parse_line()
                    self.short_names.append(host)
                else:
                    self.mapping.add(host)

    def generate_item_regexes(self):
        # instead of other classes, we need to keep two lists of regexes
        # here:
        # 1) self.hosts_domains will contain a tripple
        # ( host, fqdn, re.compile(fqdn, re.I) )
        # for each host in mapping.
        # The list will be ordered by len of host to prevent
        # substring-host matching.
        #
        # 2) self.short_names will be:
        # - sorted
        # - items extended to pair ( shortname, re.compile(shortname) )
        self.hosts_domains = []
        hosts = [h for h in self.mapping.dataset.keys() if '.' in h]
        for host in sorted(hosts, reverse=True, key=lambda x: len(x)):
            fqdn = host
            for c in '.-':
                fqdn = fqdn.replace(c, '_')
            self.hosts_domains.append((host, fqdn, re.compile(fqdn, re.I)))

        short_names = []
        for short_name in sorted(self.short_names, reverse=True):
            short_names.append((short_name, re.compile(short_name, re.I)))
        self.short_names = short_names

    def parse_line(self, line):
        """Override the default parse_line() method to also check for the
        shortname of the host derived from the hostname.
        """

        def _check_line(ln, count, search, search_re, repl=None):
            """Perform a second manual check for substrings that may have been
            missed by regex matching
            """
            if search in self.mapping.skip_keys:
                return ln, count
            _reg = re.compile(search, re.I)
            if search_re.search(ln):
                return search_re.subn(self.mapping.get(repl or search), ln)
            return ln, count

        count = 0
        line, count = super(SoSHostnameParser, self).parse_line(line)
        # make an additional pass checking for '_' formatted substrings that
        # the regex patterns won't catch
        for host, fqdn, re_fqdn in self.hosts_domains:
            line, count = _check_line(line, count, fqdn, re_fqdn, host)

        for shortname, shortname_re in self.short_names:
            line, count = _check_line(line, count, shortname, shortname_re)

        return line, count
