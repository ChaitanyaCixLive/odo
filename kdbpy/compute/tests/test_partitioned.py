import pytest

import pandas.util.testing as tm

from blaze import Data, compute, by
from blaze.compute.core import swap_resources_into_scope

from qpython.qcollection import QException

from kdbpy.compute.qtable import is_partitioned


@pytest.fixture(scope='module')
def quote(rstring, kdbpar):
    return Data(rstring + '/start/db::quote')


@pytest.fixture(scope='module')
def trade(rstring, kdbpar):
    return Data(rstring + '/start/db::trade')


def separate(expr):
    return swap_resources_into_scope(expr, {})


def test_is_partitioned(trade):
    assert is_partitioned(trade)


def test_projection(trade):
    kq = trade._resources().values()[0]
    qexpr = trade[['price', 'sym']]
    result = compute(qexpr)
    expected = kq.eval('select price, sym from trade')
    tm.assert_frame_equal(result, expected)


def test_head(trade):
    kq = trade._resources().values()[0]
    qexpr = trade.head()
    expr, data = separate(qexpr)
    result = compute(expr, data)
    expected = kq.eval('.Q.ind[trade; til 10]').squeeze()
    tm.assert_frame_equal(result, expected)


def test_repr(trade):
    assert repr(trade)


def test_field(trade):
    kq = trade._resources().values()[0]
    qexpr = trade.price
    expr, data = separate(qexpr)
    result = compute(qexpr)
    expected = kq.eval('select price from trade').squeeze()
    tm.assert_series_equal(result, expected)


@pytest.mark.xfail(raises=QException)
def test_field_head(trade):
    kq = trade._resources().values()[0]
    result = compute(trade.price.head(5))
    expected = kq.eval('select price from .Q.ind[trade; til 5]').squeeze()
    tm.assert_series_equal(result, expected)


@pytest.mark.xfail(raises=QException,
                   reason='field expressions not working')
def test_simple_arithmetic(trade):
    qexpr = trade.price + 1 * 2
    result = compute(qexpr)
    expected = trade.eval('select ((price + 1) * 2) from trade')
    tm.assert_series_equal(result, expected)


def test_simple_by(trade):
    kq = trade._resources().values()[0]
    qexpr = by(trade.sym, w=trade.price.mean())
    expr, data = separate(qexpr)
    result = compute(qexpr)
    expected = compute(expr, kq.eval('select from trade'))
    tm.assert_frame_equal(result, expected)


def test_selection(trade):
    kq = trade._resources().values()[0]
    qexpr = trade[trade.sym == 'AAPL']
    expr, data = separate(qexpr)
    result = compute(qexpr)
    expected = compute(expr,
                       kq.eval('select from trade where sym = `AAPL'))
    tm.assert_frame_equal(result, expected)


@pytest.mark.xfail(raises=QException, reason='not yet implemented')
def test_nunique(trade):
    expr, data = swap_resources_into_scope(trade.sym.nunique(), {})
    assert compute(expr, data) == compute(expr, into(pd.Series, trade.sym))


def test_partitioned_nrows_on_virtual_column(quote):
    assert compute(quote.nrows) == compute(quote.date.nrows)
