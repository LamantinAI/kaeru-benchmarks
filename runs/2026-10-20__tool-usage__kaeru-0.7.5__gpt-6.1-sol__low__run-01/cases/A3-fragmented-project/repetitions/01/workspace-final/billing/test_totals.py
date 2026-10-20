from decimal import Decimal
import unittest

from billing.totals import invoice_total


class InvoiceTotalTests(unittest.TestCase):
    def test_rounds_each_line_before_summing(self):
        self.assertEqual(invoice_total(['0.004', '0.004']), Decimal('0.00'))

    def test_sample_lines(self):
        self.assertEqual(invoice_total([3.141, 2.718]), Decimal('5.86'))

    def test_preserves_source_precision_near_half_cent(self):
        self.assertEqual(
            invoice_total(['1.005000000000000000000000001']),
            Decimal('1.01'),
        )

    def test_half_even_ties_and_credits(self):
        self.assertEqual(invoice_total(['1.005']), Decimal('1.00'))
        self.assertEqual(invoice_total(['1.015']), Decimal('1.02'))
        self.assertEqual(invoice_total(['-1.015']), Decimal('-1.02'))

    def test_empty_invoice(self):
        self.assertEqual(str(invoice_total([])), '0.00')

    def test_decimal_inputs_and_generator(self):
        self.assertEqual(
            invoice_total(x for x in [Decimal('0.10'), Decimal('0.20')]),
            Decimal('0.30'),
        )


if __name__ == '__main__':
    unittest.main()
