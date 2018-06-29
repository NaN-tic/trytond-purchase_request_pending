=========================
Purchase Request Scenario
=========================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> from trytond.tests.tools import activate_modules
    >>> today = datetime.date.today()

Install purchase_request_pending Module::

    >>> config = activate_modules('purchase_request_pending')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'Product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('20')
    >>> template.cost_price = Decimal('8')
    >>> template.purchasable = True
    >>> template.account_expense = expense
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Get stock locations::

    >>> Location = Model.get('stock.location')
    >>> warehouse_loc, = Location.find([('code', '=', 'WH')])
    >>> supplier_loc, = Location.find([('code', '=', 'SUP')])
    >>> customer_loc, = Location.find([('code', '=', 'CUS')])
    >>> output_loc, = Location.find([('code', '=', 'OUT')])
    >>> storage_loc, = Location.find([('code', '=', 'STO')])

Create a need for missing product::

    >>> ShipmentOut = Model.get('stock.shipment.out')
    >>> shipment_out = ShipmentOut()
    >>> shipment_out.planned_date = today
    >>> shipment_out.effective_date = today
    >>> shipment_out.customer = customer
    >>> shipment_out.warehouse = warehouse_loc
    >>> shipment_out.company = company
    >>> move = shipment_out.outgoing_moves.new()
    >>> move.product = product
    >>> move.uom = unit
    >>> move.quantity = 1
    >>> move.from_location = output_loc
    >>> move.to_location = customer_loc
    >>> move.company = company
    >>> move.unit_price = Decimal('1')
    >>> move.currency = company.currency
    >>> shipment_out.click('wait')

There is no purchase request::

    >>> PurchaseRequest = Model.get('purchase.request')
    >>> PurchaseRequest.find([])
    []

Create the purchase request::

  >>> create_pr = Wizard('stock.supply')
  >>> create_pr.execute('create_')

There is now a draft purchase request::

    >>> pr, = PurchaseRequest.find([])
    >>> pr.product == product
    True
    >>> pr.quantity
    1.0
    >>> pr.state
    u'draft'

Set the purchase request to pending state::

    >>> pr.click('to_pending')
    >>> pr.state
    u'pending'

Create more needs of the same product::

    >>> ShipmentOut = Model.get('stock.shipment.out')
    >>> shipment_out = ShipmentOut()
    >>> shipment_out.planned_date = today
    >>> shipment_out.effective_date = today
    >>> shipment_out.customer = customer
    >>> shipment_out.warehouse = warehouse_loc
    >>> shipment_out.company = company
    >>> move = shipment_out.outgoing_moves.new()
    >>> move.product = product
    >>> move.uom = unit
    >>> move.quantity = 2.0
    >>> move.from_location = output_loc
    >>> move.to_location = customer_loc
    >>> move.company = company
    >>> move.unit_price = Decimal('1')
    >>> move.currency = company.currency
    >>> shipment_out.click('wait')

Another purhcase requests is created::

    >>> create_pr = Wizard('stock.supply')
    >>> create_pr.execute('create_')
    >>> pending_pr, draft_pr = sorted(PurchaseRequest.find([]),
    ...     key=lambda a: a.quantity)
    >>> pending_pr.product == product
    True
    >>> pending_pr.quantity
    1.0
    >>> pending_pr.state
    u'pending'
    >>> draft_pr.product == product
    True
    >>> draft_pr.quantity
    2.0
    >>> draft_pr.state
    u'draft'

Set the purchase request back to draft and chech that they are grouped::

    >>> pending_pr.click('draft')
    >>> pending_pr.state
    u'draft'
    >>> create_pr = Wizard('stock.supply')
    >>> create_pr.execute('create_')
    >>> draft_pr, = PurchaseRequest.find([])
    >>> draft_pr.product == product
    True
    >>> draft_pr.quantity
    3.0
    >>> draft_pr.state
    u'draft'
