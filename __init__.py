# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import purchase_request


def register():
    Pool.register(
        purchase_request.PurchaseRequest,
        module='purchase_request_pending', type_='model')
