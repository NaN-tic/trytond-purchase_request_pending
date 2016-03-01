# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .purchase_request import *


def register():
    Pool.register(
        PurchaseRequest,
        module='purchase_request_pending', type_='model')
