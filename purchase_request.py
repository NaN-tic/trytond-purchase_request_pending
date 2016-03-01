#The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import datetime
import operator
from trytond.model import ModelView, fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['PurchaseRequest']


class PurchaseRequest:
    __name__ = 'purchase.request'
    __metaclass__ = PoolMeta

    pending = fields.Boolean('Pending', readonly=True)

    @classmethod
    def __setup__(cls):
        super(PurchaseRequest, cls).__setup__()
        pending = ('pending', 'Pending')
        if pending not in cls.state.selection:
            cls.state.selection.append(pending)
        cls._buttons.update({
                'draft': {
                    'invisible': Eval('state') != 'pending',
                    'icon': 'tryton-go-previous',
                    },
                'to_pending': {
                    'invisible': Eval('state') != 'draft',
                    'icon': 'tryton-go-next',
                    },
                })

    @staticmethod
    def default_pending():
        return False

    @classmethod
    @ModelView.button
    def draft(cls, requests):
        cls.write(requests, {'pending': False})

    @classmethod
    @ModelView.button
    def to_pending(cls, requests):
        cls.write(requests, {'pending': True})

    def get_state(self, name):
        if self.pending and not self.purchase_line:
            return 'pending'
        return super(PurchaseRequest, self).get_state(name)

    @classmethod
    def generate_requests(cls, products=None, warehouses=None):
        with Transaction().set_context(generate_requests=True):
            return super(PurchaseRequest, cls).generate_requests(products,
                warehouses)

    @classmethod
    def compare_requests(cls, new_requests):
        pool = Pool()
        Uom = pool.get('product.uom')
        Request = pool.get('purchase.request')
        requests = Request.search([
                ('purchase_line', '=', None),
                ('pending', '=', True),
                ])
        # Fetch data from existing requests
        existing_req = {}
        for request in requests:
            existing_req.setdefault(
                (request.product.id, request.warehouse.id),
                []).append({
                        'supply_date': (
                            request.supply_date or datetime.date.max),
                        'quantity': request.quantity,
                        'uom': request.uom,
                        })

        new_requests = super(PurchaseRequest, cls).compare_requests(
            new_requests)
        new_requests.sort(key=operator.attrgetter('supply_date'))
        for new_req in new_requests:
            for old_req in existing_req.get(
                    (new_req.product.id, new_req.warehouse.id), []):
                if old_req['supply_date'] <= new_req.supply_date:
                    quantity = Uom.compute_qty(old_req['uom'],
                        old_req['quantity'], new_req.uom)
                    new_req.quantity = max(0.0, new_req.quantity - quantity)
                    new_req.computed_quantity = new_req.quantity
                    old_req['quantity'] = Uom.compute_qty(new_req.uom,
                        max(0.0, quantity - new_req.quantity), old_req['uom'])
                else:
                    break
        return new_requests

    @classmethod
    def delete(cls, requests):
        if Transaction().context.get('generate_requests', False):
            requests = [r for r in requests if not r.pending]
        super(PurchaseRequest, cls).delete(requests)
