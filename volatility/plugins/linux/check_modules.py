# Volatility
# Copyright (C) 2007-2013 Volatility Foundation
#
# This file is part of Volatility.
#
# Volatility is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License Version 2 as
# published by the Free Software Foundation.  You may not use, modify or
# distribute this program under any other version of the GNU General
# Public License.
#
# Volatility is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Volatility.  If not, see <http://www.gnu.org/licenses/>.
#

"""
@author:       Andrew Case
@license:      GNU General Public License 2.0
@contact:      atcuno@gmail.com
@organization:
"""

from volatility import args
from volatility.plugins.overlays import basic
from volatility.plugins.linux import common


class CheckModules(common.LinuxPlugin):
    """Compares module list to sysfs info, if available.

    Sysfs contains a kset objects for a number of kernel objects (kobjects). One
    of the ksets is the "module_kset" which holds references to all loaded
    kernel modules.

    Each struct module object holds within it a kobj struct for reference
    counting. This object is referenced both from the struct module and the
    sysfs kset.

    This plugin traverses the kset and resolves the kobj back to its containing
    object (which is the struct module itself). We then compare the struct
    module with the list of known modules (which is obtained by traversing the
    module's list member). So if a module were to simply unlink itself from the
    list, it would still be found by its reference from sysfs.
    """

    __name = "check_modules"

    @classmethod
    def is_active(cls, config):
        if super(CheckModules, cls).is_active(config):
            return config.profile.get_constant("module_kset")

    def get_kset_modules(self):
        module_kset = self.profile.get_constant_object(
            "module_kset", target="kset", vm=self.kernel_address_space)

        for kobj in module_kset.list.list_of_type("kobject", "entry"):
            if kobj.name:
                yield kobj

    def render(self, renderer):
        renderer.table_header([
                ("Module", "module_addr", "[addrpad]"),
                ("Module Name", "module", "30"),
                ("Ref Count", "refcount", "^10"),
                ("Known", "known", ""),
                ])
        lsmod = self.session.plugins.lsmod(session=self.session)

        # We check the container module for membership so we do not get fulled
        # by simple name clashes.
        modules = set(lsmod.get_module_list())

        for kobj in self.get_kset_modules():
            name = kobj.name.deref()
            ref_count = kobj.kref.refcount.counter

            # Real modules have at least 3 references in sysfs.
            if ref_count < 3:
                continue

            container_module = basic.container_of(kobj, "module", "mkobj")

            renderer.table_row(container_module, container_module.name,
                               ref_count, container_module in modules)

