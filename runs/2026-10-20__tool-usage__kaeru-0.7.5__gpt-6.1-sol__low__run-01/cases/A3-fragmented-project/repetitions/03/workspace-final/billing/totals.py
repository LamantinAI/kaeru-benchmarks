from decimal import Decimal, ROUND_HALF_EVEN, localcontext


def invoice_total(line_items):
    """Sum lines rounded to cents using decimal half-even rounding.

    Pass strings or Decimals to preserve all digits from the usage source.
    """
    amounts = [Decimal(str(x)) for x in line_items]
    if any(not amount.is_finite() for amount in amounts):
        raise ValueError('Line items must be finite amounts')

    with localcontext() as context:
        # Allow cents, rounding carry, and growth from summing all the lines.
        context.prec = max(
            3, max((amount.adjusted() + 3 for amount in amounts), default=3)
        ) + len(str(len(amounts))) + 1
        return sum(
            (amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
             for amount in amounts),
            Decimal('0.00'),
        )
