"""
Test of Fake virtualization backend.

Copyright (C) 2015 Radek Novacek <rnovacek@redhat.com>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import os
from base import TestBase
from virt import Virt, Hypervisor, VirtError
from virt.fakevirt import FakeVirt
from config import ConfigManager
import logging
from tempfile import mkdtemp
import shutil


HYPERVISOR_JSON = """
{
    "hypervisors": [
        {
            "uuid": "60527517-6284-7593-6AAB-75BF2A6375EF",
            "guests": [
                {
                    "guestId": "07ED8178-95D5-4244-BC7D-582A54A48FF8",
                    "state": 1,
                    "attributes": {
                        "active": 1,
                        "virtWhoType": "hyperv",
                        "hypervisorType": "hyperv"
                    }
                }
            ]
        }
    ]
}"""

NON_HYPERVISOR_JSON = """
{
    "hypervisors": [
        {
            "guests": [
                {
                    "guestId": "9f06a84d-5f56-4e7e-be0c-937b3c1924d7",
                    "state": 1,
                    "attributes": {
                        "active": 1,
                        "virtWhoType": "libvirt",
                        "hypervisorType": "QEMU"
                    }
                }
            ]
        }
    ]
}
"""


class TestFakeRead(TestBase):
    def setUp(self):
        self.config_dir = mkdtemp()
        self.addCleanup(shutil.rmtree, self.config_dir)
        self.logger = logging.getLogger("virtwho.test")
        self.hypervisor_file = os.path.join(self.config_dir, "hypervisor.json")
        self.config_file = os.path.join(self.config_dir, "test.conf")

    def test_read_hypervisor(self):
        with open(self.hypervisor_file, "w") as f:
            f.write(HYPERVISOR_JSON)

        with open(self.config_file, "w") as f:
            f.write("""
[test]
type=fake
is_hypervisor=true
file=%s
""" % self.hypervisor_file)

        manager = ConfigManager(self.logger, self.config_dir)
        self.assertEquals(len(manager.configs), 1)
        virt = Virt.fromConfig(self.logger, manager.configs[0])
        self.assertEquals(type(virt), FakeVirt)
        mapping = virt.getHostGuestMapping()
        self.assertTrue("hypervisors" in mapping)
        hypervisors = mapping["hypervisors"]
        self.assertEquals(len(hypervisors), 1)
        hypervisor = hypervisors[0]
        self.assertEquals(type(hypervisor), Hypervisor)
        self.assertEquals(hypervisor.hypervisorId, "60527517-6284-7593-6AAB-75BF2A6375EF")
        self.assertEquals(len(hypervisor.guestIds), 1)
        guest = hypervisor.guestIds[0]
        self.assertEquals(guest.uuid, "07ED8178-95D5-4244-BC7D-582A54A48FF8")
        self.assertEquals(guest.state, 1)

    def test_read_hypervisor_from_non_hypervisor(self):
        with open(self.hypervisor_file, "w") as f:
            f.write(NON_HYPERVISOR_JSON)

        with open(self.config_file, "w") as f:
            f.write("""
[test]
type=fake
is_hypervisor=true
file=%s
""" % self.hypervisor_file)

        manager = ConfigManager(self.logger, self.config_dir)
        self.assertEquals(len(manager.configs), 1)
        virt = Virt.fromConfig(self.logger, manager.configs[0])
        self.assertEquals(type(virt), FakeVirt)
        self.assertRaises(VirtError, virt.getHostGuestMapping)

    def test_read_non_hypervisor(self):
        with open(self.hypervisor_file, "w") as f:
            f.write(NON_HYPERVISOR_JSON)

        with open(self.config_file, "w") as f:
            f.write("""
[test]
type=fake
is_hypervisor=false
file=%s
""" % self.hypervisor_file)

        manager = ConfigManager(self.logger, self.config_dir)
        self.assertEquals(len(manager.configs), 1)
        virt = Virt.fromConfig(self.logger, manager.configs[0])
        self.assertEquals(type(virt), FakeVirt)
        guests = virt.listDomains()
        self.assertEquals(len(guests), 1)
        guest = guests[0]
        self.assertEquals(guest.uuid, "9f06a84d-5f56-4e7e-be0c-937b3c1924d7")
        self.assertEquals(guest.state, 1)

    def test_read_non_hypervisor_from_hypervisor(self):
        with open(self.hypervisor_file, "w") as f:
            f.write(HYPERVISOR_JSON)

        with open(self.config_file, "w") as f:
            f.write("""
[test]
type=fake
is_hypervisor=false
file=%s
""" % self.hypervisor_file)

        manager = ConfigManager(self.logger, self.config_dir)
        self.assertEquals(len(manager.configs), 1)
        virt = Virt.fromConfig(self.logger, manager.configs[0])
        self.assertEquals(type(virt), FakeVirt)
        self.assertRaises(VirtError, virt.listDomains)
