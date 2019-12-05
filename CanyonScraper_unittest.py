import unittest
import datetime
import logging
import PythonCanyonScraper as pcs


class MyTestCase(unittest.TestCase):
    # def testBikeSMSAdv(self):
    #     """test Twilio messaging"""
    #     self.assertEqual(pcs.BikelisttoSMSAdvanced([['21332', 'special test', '£222', '£111']]), True,
    #                      "Should be True, need to find another check possibly in message.sid")

    def printstuff(self, listoflistofbikes: list) -> None:
        """admin method to print stdout"""
        log = logging.getLogger("mytestcase.canyonscraper")
        log.warning(type(listoflistofbikes))
        for work in listoflistofbikes:
            log.warning(type(work))
            log.warning("element may contain something below")
            log.warning(work)
            log.warning("^^^^^^ finished single loop ^^^^^^^")
        return None

    def testcheck_bike_list_full(self) -> None:
        """test the data structure"""
        insert_time_stamp = (datetime.datetime.now())
        workinglist = pcs.check_bike_list([['21332', 'special test 1', '£000', '£111', insert_time_stamp]])
        self.assertListEqual(workinglist, [], "list should be empty")

    def testcheck_bike_list_first_fail(self) -> None:
        """test the data structure"""
        insert_time_stamp = (datetime.datetime.now())
        workinglist = pcs.check_bike_list([[None, 'special test 2', '£111', '£111', insert_time_stamp]])
        # self.printstuff(workinglist)
        self.assertIsNot(workinglist, [], "list should not be empty")

    def testcheck_bike_list_second_fail(self) -> None:
        """test the data structure"""
        insert_time_stamp = (datetime.datetime.now())
        workinglist = pcs.check_bike_list([['222222', None, '£222', '£111', insert_time_stamp]])
        # self.printstuff(workinglist)
        self.assertIsNot(workinglist, [], "list should not be empty")

    def testcheck_bike_list_third_fail(self) -> None:
        """test the data structure"""
        insert_time_stamp = (datetime.datetime.now())
        workinglist = pcs.check_bike_list([['222222', 'Special test 4', None, '£111', insert_time_stamp]])
        # self.printstuff(workinglist)
        self.assertIsNot(workinglist, [], "list should not be empty")

    def testcheck_bike_list_four_fail(self) -> None:
        """test the data structure"""
        insert_time_stamp = (datetime.datetime.now())
        workinglist = pcs.check_bike_list([['222222', 'Special test 4', '£111', None, insert_time_stamp]])
        # self.printstuff(workinglist)
        self.assertIsNot(workinglist, [], "list should not be empty")

    def testcheck_bike_list_five_fail(self) -> None:
        """test the data structure"""
        insert_time_stamp = (datetime.datetime.now())
        workinglist = pcs.check_bike_list([['222222', 'Special test 4', '£222', '£111', None]])

        self.assertIsNot(workinglist, [], "list should not be empty")

    def testaddGBPprices(self) -> None:
        """tests the three GBP additions, price, price and Percent_discount"""
        insert_time_stamp = (datetime.datetime.now())
        workinglist = [['222222', 'Special test 4', '£222.00', '£111.00', insert_time_stamp]]
        bikelist_with_added_int = pcs.addGBPprices(workinglist)

        self.assertIsNot(bikelist_with_added_int, [], "list should not be empty")

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger("mytestcase.canyonscraper").setLevel(logging.DEBUG)
    unittest.main()
