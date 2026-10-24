"""🎛 HID device listing: one entry per unit, however many interfaces it has.

Run:  py -m unittest tests.shared.controllers.test_hid_devices -v

hidapi is faked: the tests hand-build what `hid.enumerate()` returns.
"""
import unittest
from unittest import mock

from shared.controllers import hid_input


def _iface(path, serial="", usage_page=1, vid=0x17CC, pid=0x1500):
    return {"vendor_id": vid, "product_id": pid, "path": path,
            "serial_number": serial, "usage_page": usage_page,
            "manufacturer_string": "Native Instruments",
            "product_string": "Traktor Kontrol"}


class _Hid:
    def __init__(self, ifaces):
        self.ifaces = ifaces

    def enumerate(self):
        return list(self.ifaces)


class HidUnitsTest(unittest.TestCase):

    def _plug(self, *ifaces):
        patcher = mock.patch.object(hid_input, "hid", _Hid(ifaces))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_one_unit_with_two_interfaces_is_listed_once(self):
        self._plug(_iface(b"a0", "S1"), _iface(b"a1", "S1", usage_page=0xFF01))
        self.assertEqual(hid_input.list_devices(),
                         [("17cc:1500", "Native Instruments Traktor Kontrol")])
        self.assertEqual(hid_input._path_for("17cc:1500"), b"a1")

    def test_a_second_identical_unit_can_be_picked(self):
        """L9: the list kept vendor:product only, so the second unit of the
        same model never showed up and could never be opened."""
        self._plug(_iface(b"a0", "S1"), _iface(b"a1", "S1", usage_page=0xFF01),
                   _iface(b"b0", "S2"), _iface(b"b1", "S2", usage_page=0xFF01))
        self.assertEqual([i for i, _n in hid_input.list_devices()],
                         ["17cc:1500", "17cc:1500 #2"])
        self.assertEqual(hid_input._path_for("17cc:1500"), b"a1")
        self.assertEqual(hid_input._path_for("17cc:1500 #2"), b"b1")

    def test_units_without_a_serial_stay_one_entry(self):
        # Nothing tells their interfaces apart, so they are not guessed at.
        self._plug(_iface(b"a0"), _iface(b"b0"))
        self.assertEqual([i for i, _n in hid_input.list_devices()], ["17cc:1500"])

    def test_a_unit_gone_is_not_found(self):
        self._plug(_iface(b"a0", "S1"))
        self.assertIsNone(hid_input._path_for("17cc:1500 #2"))


if __name__ == "__main__":
    unittest.main()
