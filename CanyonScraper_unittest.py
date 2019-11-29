import unittest
import PythonCanyonScraper as pcs


class MyTestCase(unittest.TestCase):
    def testBikeSMSAdv(self):
        """test Twilio messaging"""
        self.assertEqual(pcs.BikelisttoSMSAdvanced([['21332', 'special test', '£222', '£111']]), True,
                         "Should be True, need to find another check possibly in message.sid")


if __name__ == '__main__':
    unittest.main()
