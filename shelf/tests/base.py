from nose.tools import ok_, eq_
from shelf import Shelf


def test_shelf():
    shelf = Shelf()
    shelf.bp = "test"
    eq_(shelf.app, None)
    ok_(shelf.bp is not None)
