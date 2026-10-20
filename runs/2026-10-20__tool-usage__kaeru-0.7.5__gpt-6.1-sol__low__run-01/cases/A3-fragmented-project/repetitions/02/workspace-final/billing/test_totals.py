from decimal import Decimal
import json
from pathlib import Path
import unittest

from billing.totals import invoice_total


class InvoiceTotalTests(unittest.TestCase):
    def test_sample_invoice(self):
        data = json.loads(
            Path(__file__).with_name('sample-lines.json').read_text(),
            parse_float=Decimal,
        )
        self.assertEqual(invoice_total(data['line_items']), Decimal('5.86'))

    def test_rounds_each_line_before_summing(self):
        self.assertEqual(invoice_total(['0.006', '0.006']), Decimal('0.02'))

    def test_preserves_high_precision_around_rounding_boundary(self):
        self.assertEqual(
            invoice_total(['1.0050000000000000000000000001']),
            Decimal('1.01'),
        )

    def test_half_even_ties_and_credits(self):
        self.assertEqual(invoice_total(['1.005', '1.015']), Decimal('2.02'))
        self.assertEqual(invoice_total(['-0.006', '-0.006']), Decimal('-0.02'))

    def test_empty_and_generator_inputs(self):
        self.assertEqual(invoice_total([]), Decimal('0.00'))
        self.assertEqual(invoice_total(x for x in [0.1, 0.2]), Decimal('0.30'))


if __name__ == '__main__':
    unittest.main()
