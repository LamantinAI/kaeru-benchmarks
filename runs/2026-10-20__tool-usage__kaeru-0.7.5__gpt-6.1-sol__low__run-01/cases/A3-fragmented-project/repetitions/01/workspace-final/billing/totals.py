from decimal import Decimal, ROUND_HALF_EVEN


CENT = Decimal('0.01')


def invoice_total(line_items):
    """Sum line amounts rounded to cents, matching the printed invoice.

    Pass strings or Decimals to preserve all source decimal places.
    Half-cent ties use half-even rounding.
    """
    return sum(
        (Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_EVEN)
         for x in line_items),
        Decimal('0.00'),
    )
