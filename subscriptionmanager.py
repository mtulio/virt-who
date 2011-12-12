"""
Module for communcating with subscription-manager, part of virt-who

Copyright (C) 2011 Radek Novacek <rnovacek@redhat.com>

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
import sys

import rhsm.connection as rhsm_connection
import rhsm.certificate as rhsm_certificate
import rhsm.config as rhsm_config

class SubscriptionManagerError(Exception):
    pass

class SubscriptionManager:
    """ Class for interacting subscription-manager. """
    def __init__(self, logger):
        self.logger = logger
        self.cert_uuid = None

        self.readConfig()

        # Consumer ID obtained from consumer certificate
        self.cert_uuid = self.uuid()

    def readConfig(self):
        """ Parse rhsm.conf in order to obtain consumer
            certificate and key paths. """
        self.config = rhsm_config.initConfig()
        consumerCertDir = self.config.get("rhsm", "consumerCertDir")
        cert = 'cert.pem'
        key = 'key.pem'
        self.cert_file = os.path.join(consumerCertDir, cert)
        self.key_file = os.path.join(consumerCertDir, key)
        if not os.access(self.cert_file, os.R_OK):
            self.logger.error("Unable to read certificate, system is not registered or you are not root")
            sys.exit(1)

    def connect(self):
        """ Connect to the subscription-manager. """
        self.connection = rhsm_connection.UEPConnection(
                cert_file=self.cert_file, key_file=self.key_file)
        try:
            if not self.connection.ping()['result']:
                self.logger.error("Unable to obtain status from server, UEPConnection is likely not usable.")
        except Exception, e:
            self.logger.warn("Unable to obtain status from server, UEPConnection is likely not usable:")
            self.logger.exception(e)

    def sendVirtGuests(self, domains):
        """ Update consumer facts with UUIDs of virtual guests. """

        # Get comma separated list of UUIDs
        uuids = []
        for domain in domains:
            uuids.append(domain.UUIDString())
        uuids.sort()

        self.logger.debug("Sending update to updateConsumer: %s" % uuids)

        # Send list of guest uuids to the server
        try:
            self.connection.updateConsumer(self.uuid(), guest_uuids=uuids)
        except Exception, e:
            raise SubscriptionManagerError(str(e))

    def hypervisorCheckIn(self, owner, env, mapping):
        """ Send hosts to guests mapping to subscription manager. """

        self.logger.debug("Sending updates in hosts-to-guests mapping: %s" % mapping)

        # Send the mapping
        try:
            return self.connection.hypervisorCheckIn(owner, env, mapping)
        except Exception, e:
            raise SubscriptionManagerError(str(e))

    def uuid(self):
        """ Read consumer certificate and get consumer UUID from it. """
        if not self.cert_uuid:
            try:
                f = open(self.cert_file, "r")
            except Exception, e:
                self.logger.error("Unable to open certificate (%s): %s" % (self.cert_file, e.message))
                return ""
            certificate = rhsm_certificate.Certificate(f.read())
            f.close()
            self.cert_uuid = certificate.subject().get('CN')
        return self.cert_uuid

    def getFacts(self):
        """ Get fact for current consumer. """
        self.consumer = self.connection.conn.request_get('/consumers/%s' % self.uuid())
        return self.consumer['facts']
