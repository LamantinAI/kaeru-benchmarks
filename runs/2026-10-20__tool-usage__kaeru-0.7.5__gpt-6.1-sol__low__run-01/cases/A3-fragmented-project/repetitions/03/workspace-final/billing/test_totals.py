import unittest
from decimal import Decimal, localcontext

from billing.totals import invoice_total


class InvoiceTotalTests(unittest.TestCase):
    def test_sample(self):
        self.assertEqual(invoice_total([3.141, 2.718]), Decimal('5.86'))

    def test_rounds_each_line_before_summing(self):
        self.assertEqual(invoice_total(['0.0049', '0.0049']), Decimal('0.00'))
        self.assertEqual(invoice_total(['0.0051', '0.0051']), Decimal('0.02'))

    def test_half_even_and_credits(self):
        self.assertEqual(invoice_total(['1.005', '1.015']), Decimal('2.02'))
        self.assertEqual(invoice_total(['-1.015', '0.0051']), Decimal('-1.01'))

    def test_preserves_source_precision(self):
        self.assertEqual(
            invoice_total(['0.005000000000000000000000000001']),
            Decimal('0.01'),
        )

    def test_large_total_independent_of_context_precision(self):
        with localcontext() as context:
            context.prec = 4
            self.assertEqual(
                invoice_total(iter(['123456789012345678901234567890.999', '0.01'])),
                Decimal('123456789012345678901234567891.01'),
            )

    def test_empty(self):
        self.assertEqual(str(invoice_total([])), '0.00')

    def test_rejects_nonfinite_amounts(self):
        for amount in ['NaN', 'Infinity', '-Infinity']:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                invoice_total([amount])
