import unittest
import PythonCanyonScraper as pcs


class TestMyTestCase(unittest.TestCase):
    def BikeSMSAdv(self):
        """test Twilio messaging"""
        print('starting unittest')
        self.assertEqual(pcs.BikelisttoSMSAdvanced([['21332', 'special test', '£222', '£111']]), True, \
                         "Should be True, need to find another check possibly in message.sid")
        print ('ending unittest')


if __name__ == '__main__':
    print('starting main')
    unittest.main()
    print('finishing main')
