from decimal import Decimal

def invoice_total(line_items):
    return sum((Decimal(str(x)) for x in line_items), Decimal('0'))
