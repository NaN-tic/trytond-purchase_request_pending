import datetime
import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.modules.account.tests.tools import create_chart, get_accounts
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install purchase_request_pending Module
        activate_modules('purchase_request_pending')

        # Create company
        _ = create_company()
        company = get_company()

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()
        customer = Party(name='Customer')
        customer.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        product = Product()
        template = ProductTemplate()
        template.name = 'Product'
        template.default_uom = unit
        template.type = 'goods'
        template.list_price = Decimal('20')
        template.purchasable = True
        template.account_category = account_category
        template.save()
        product.template = template
        product.save()

        # Get stock locations
        Location = Model.get('stock.location')
        warehouse_loc, = Location.find([('code', '=', 'WH')])
        supplier_loc, = Location.find([('code', '=', 'SUP')])
        customer_loc, = Location.find([('code', '=', 'CUS')])
        output_loc, = Location.find([('code', '=', 'OUT')])
        storage_loc, = Location.find([('code', '=', 'STO')])

        # Create a need for missing product
        today = datetime.date.today()
        ShipmentOut = Model.get('stock.shipment.out')
        shipment_out = ShipmentOut()
        shipment_out.planned_date = today
        shipment_out.effective_date = today
        shipment_out.customer = customer
        shipment_out.warehouse = warehouse_loc
        shipment_out.company = company
        move = shipment_out.outgoing_moves.new()
        move.product = product
        move.unit = unit
        move.quantity = 1
        move.from_location = output_loc
        move.to_location = customer_loc
        move.company = company
        move.unit_price = Decimal('1')
        move.currency = company.currency
        shipment_out.click('wait')

        # There is no purchase request
        PurchaseRequest = Model.get('purchase.request')
        self.assertEqual(PurchaseRequest.find([]), [])

        # Create the purchase request
        Wizard('stock.supply').execute('create_')

        # There is now a draft purchase request
        pr, = PurchaseRequest.find([])
        self.assertEqual(pr.product, product)
        self.assertEqual(pr.quantity, 1.0)
        self.assertEqual(pr.state, 'draft')

        # Set the purchase request to pending state
        pr.click('to_pending')
        self.assertEqual(pr.state, 'pending')

        # Create more needs of the same product
        ShipmentOut = Model.get('stock.shipment.out')
        shipment_out = ShipmentOut()
        shipment_out.planned_date = today
        shipment_out.effective_date = today
        shipment_out.customer = customer
        shipment_out.warehouse = warehouse_loc
        shipment_out.company = company
        move = shipment_out.outgoing_moves.new()
        move.product = product
        move.unit = unit
        move.quantity = 2.0
        move.from_location = output_loc
        move.to_location = customer_loc
        move.company = company
        move.unit_price = Decimal('1')
        move.currency = company.currency
        shipment_out.click('wait')

        # Another purhcase requests is created
        Wizard('stock.supply').execute('create_')
        pending_pr, draft_pr = sorted(PurchaseRequest.find([]),
                                      key=lambda a: a.quantity)
        self.assertEqual(pending_pr.product, product)
        self.assertEqual(pending_pr.quantity, 1.0)
        self.assertEqual(pending_pr.state, 'pending')
        self.assertEqual(draft_pr.product, product)
        self.assertEqual(draft_pr.quantity, 2.0)
        self.assertEqual(draft_pr.state, 'draft')

        # Set the purchase request back to draft and chech that they are grouped
        pending_pr.click('draft')
        self.assertEqual(pending_pr.state, 'draft')
        Wizard('stock.supply').execute('create_')
        draft_pr, = PurchaseRequest.find([])
        self.assertEqual(draft_pr.product, product)
        self.assertEqual(draft_pr.quantity, 3.0)
        self.assertEqual(draft_pr.state, 'draft')
