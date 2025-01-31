# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, Form

class TestCarpentryMrp(common.SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
