import unittest
from workbench.domain import *

class DomainBoundaryTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertIsNone(intersection([['2026-01-01','2026-01-02'],['2026-01-03','2026-01-04']]))
        self.assertEqual(intersection([['2026-01-01','2026-01-02'],['2026-01-02','2026-01-04']]),['2026-01-02','2026-01-02'])
        with self.assertRaises(ValueError):intersection([['2026-02-01','2026-01-01']])
        self.assertTrue(reachable([['a','b'],['b','c'],['c','b']],'a','c'))
        self.assertEqual(scope_intersection([['甲'],['乙']]),[])
