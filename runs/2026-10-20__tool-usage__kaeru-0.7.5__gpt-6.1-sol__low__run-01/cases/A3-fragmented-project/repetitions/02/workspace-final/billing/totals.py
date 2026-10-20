from decimal import Decimal, ROUND_HALF_EVEN


CENT = Decimal('0.01')

def invoice_total(line_items):
    """Sum lines rounded to cents, using decimal half-even rounding.

    Pass strings or Decimals to preserve all digits from usage sources.
    """
    return sum(
        (Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_EVEN)
         for x in line_items),
        Decimal('0.00'),
    )
