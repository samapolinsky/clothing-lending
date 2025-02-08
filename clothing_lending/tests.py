from django.test import TestCase

# Create your tests here.
class DummyTestCase(TestCase):
    def setUp(self):
        x = 1
        y = 2
    
    def dummy_test_case_pass(self):
        self.assertEqual(1, 1)
