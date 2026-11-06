"""🔊 What Windows says about an output: the slider and the form factor.

The COM calls are replaced by a fake vtable, so the reading, the clamping and
every way a device can refuse are covered without a sound card.
"""
import ctypes
import sys
import unittest
from unittest import mock

if sys.platform != "win32":
    raise unittest.SkipTest("Windows-only")

from player.audio import master_volume_win32 as mv  # noqa: E402

DEV = 1111
ENDPOINT = 2222
STORE = 3333
ENUM = 4444


class _Com:
    """A fake `method()`: the function at a slot of whatever object is called."""

    def __init__(self, level=0.5, form=3, vt=19, fail_on=()):
        self.level, self.form, self.vt = level, form, vt
        self.fail_on = set(fail_on)
        self.released = []
        self.calls = []

    def release(self, ptr):
        self.released.append(ptr)

    def method(self, ptr, slot, *_argtypes):
        def call(*args):
            self.calls.append((ptr, slot))
            if (ptr, slot) in self.fail_on:
                raise OSError("refused")
            out = args[-1]._obj   # the byref'd c_void_p / c_float, or an address
            if (ptr, slot) == (DEV, mv._ACTIVATE):
                out.value = ENDPOINT
            elif (ptr, slot) == (DEV, mv._OPEN_PROPERTY_STORE):
                out.value = STORE
            elif (ptr, slot) == (ENDPOINT, mv._GET_MASTER_SCALAR):
                out.value = self.level
            elif (ptr, slot) == (ENUM, mv._GET_DEVICE):
                out.value = DEV
            elif (ptr, slot) == (ENUM, mv._GET_DEFAULT_ENDPOINT):
                out.value = DEV
        return call


def _fake_value(com):
    """GetValue writes a PROPVARIANT at the address it is given."""
    real = com.method

    def method(ptr, slot, *argtypes):
        if (ptr, slot) != (STORE, mv._GET_VALUE):
            return real(ptr, slot, *argtypes)

        def call(store, _key, address):
            com.calls.append((store, slot))
            ctypes.c_ushort.from_address(address).value = com.vt
            ctypes.c_ulong.from_address(address + 8).value = com.form
        return call
    return method


class MasterTest(unittest.TestCase):
    def read(self, com, fn, ptr):
        with mock.patch.object(mv, "method", _fake_value(com)), \
                mock.patch.object(mv, "release", com.release):
            return fn(ptr)

    def test_the_slider_is_read_and_the_endpoint_released(self):
        com = _Com(level=0.5)
        self.assertEqual(self.read(com, mv._master, DEV), 0.5)
        self.assertEqual(com.released, [ENDPOINT])

    def test_a_slider_outside_the_range_is_clamped(self):
        for raw, want in ((1.7, 1.0), (-0.3, 0.0)):
            with self.subTest(raw=raw):
                self.assertEqual(self.read(_Com(level=raw), mv._master, DEV), want)

    def test_no_endpoint_means_no_slider(self):
        com = _Com()
        real = com.method

        def method(ptr, slot, *argtypes):
            if (ptr, slot) == (DEV, mv._ACTIVATE):
                return lambda *_a: None   # leaves the out pointer empty
            return real(ptr, slot, *argtypes)
        with mock.patch.object(mv, "method", method), mock.patch.object(mv, "release", com.release):
            self.assertIsNone(mv._master(DEV))

    def test_the_form_factor_is_read_and_the_store_released(self):
        com = _Com(form=5)
        self.assertEqual(self.read(com, mv._form_factor, DEV), 5)
        self.assertEqual(com.released, [STORE])

    def test_a_form_factor_of_another_type_is_unknown(self):
        self.assertIsNone(self.read(_Com(vt=8), mv._form_factor, DEV))

    def test_no_property_store_means_no_form_factor(self):
        com = _Com()
        real = com.method

        def method(ptr, slot, *argtypes):
            if (ptr, slot) == (DEV, mv._OPEN_PROPERTY_STORE):
                return lambda *_a: None
            return real(ptr, slot, *argtypes)
        with mock.patch.object(mv, "method", method), mock.patch.object(mv, "release", com.release):
            self.assertIsNone(mv._form_factor(DEV))


class EndpointInfoTest(unittest.TestCase):
    def info(self, com, endpoint_id="", hr=0, enum=ENUM):
        def create(_clsid, _outer, _ctx, _iid, ref):
            ref._obj.value = enum
            return hr
        ole = mock.Mock()
        ole.CoCreateInstance.side_effect = create
        with mock.patch.object(mv, "_ole32", ole), \
                mock.patch.object(mv, "method", _fake_value(com)), \
                mock.patch.object(mv, "release", com.release):
            return mv.endpoint_info(endpoint_id)

    def test_the_default_output_reports_its_slider_and_form(self):
        com = _Com(level=0.25, form=3)
        self.assertEqual(self.info(com), (0.25, 3))
        self.assertIn((ENUM, mv._GET_DEFAULT_ENDPOINT), com.calls)
        self.assertEqual(com.released, [ENDPOINT, STORE, DEV, ENUM])

    def test_a_named_device_is_asked_for_by_id(self):
        com = _Com()
        self.info(com, endpoint_id="{0.0.0.00000000}.{abc}")
        self.assertIn((ENUM, mv._GET_DEVICE), com.calls)
        self.assertNotIn((ENUM, mv._GET_DEFAULT_ENDPOINT), com.calls)

    def test_an_unknown_id_falls_back_to_the_default_output(self):
        com = _Com(fail_on=[(ENUM, mv._GET_DEVICE)])
        self.assertEqual(self.info(com, endpoint_id="gone"), (0.5, 3))
        self.assertIn((ENUM, mv._GET_DEFAULT_ENDPOINT), com.calls)

    def test_no_enumerator_says_nothing(self):
        self.assertEqual(self.info(_Com(), hr=-1), (None, None))
        self.assertEqual(self.info(_Com(), enum=0), (None, None))

    def test_no_default_output_says_nothing(self):
        com = _Com()
        real = com.method

        def method(ptr, slot, *argtypes):
            if (ptr, slot) == (ENUM, mv._GET_DEFAULT_ENDPOINT):
                return lambda *_a: None
            return real(ptr, slot, *argtypes)
        com.method = method
        self.assertEqual(self.info(com), (None, None))

    def test_a_device_that_refuses_both_questions_still_answers(self):
        com = _Com(fail_on=[(DEV, mv._ACTIVATE), (DEV, mv._OPEN_PROPERTY_STORE)])
        self.assertEqual(self.info(com), (None, None))
        self.assertIn(DEV, com.released)

    def test_a_failing_default_lookup_says_nothing(self):
        com = _Com(fail_on=[(ENUM, mv._GET_DEFAULT_ENDPOINT)])
        self.assertEqual(self.info(com), (None, None))
        self.assertEqual(com.released, [ENUM])


class RealDeviceTest(unittest.TestCase):
    def test_the_real_default_output_answers_without_raising(self):
        master, form = mv.endpoint_info()
        self.assertTrue(master is None or 0.0 <= master <= 1.0, master)
        self.assertTrue(form is None or isinstance(form, int), form)


if __name__ == "__main__":
    unittest.main(verbosity=2)
