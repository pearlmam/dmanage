# -*- coding: utf-8 -*-

import pytest
from unittest.mock import MagicMock
from unittest.mock import patch
from dmanage.metadata.metastring import compose,parse, _parse


@pytest.fixture
def sample_file():
    return "/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff"


@pytest.fixture
def sample_files():
    return [
        "/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff",
        "/path/to/file/name_L-500mW_T-400C_exp-25ms_ND-0.tiff",
    ]


# --- Unit Tests for _parse ---

def test_parse_single_filename(sample_file):
    result = _parse(sample_file)
    expected = {"L": 10.0, "T": 100.0, "exp": 1.0, "ND": 0.0}
    assert result == expected


def test_parse_with_checkvars_filter(sample_file):
    result = _parse(sample_file, checkVars=["L", "T"])
    assert result == {"L": 10.0, "T": 100.0}


def test_parse_as_string(sample_file):
    result = _parse(sample_file, checkVars=["L", "T"], asstring=True)
    assert result == {"L": "10mW", "T": "100C"}


def test_parse_custom_separators():
    path = "/path/to/file/data|L=50mW#T=200C.tiff"
    result = _parse(path, equiv="=", sep=["|", "#"])
    assert result == {"L": 50.0, "T": 200.0}


# --- Integration Tests for parse() ---

def test_parse_returns_dataframe_when_pandas_installed(sample_files):
    pd = pytest.importorskip("pandas")
    
    with patch("dmanage._compat.HAS_PANDAS", True):
        df = parse(sample_files, checkVars=["L", "T"])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df["L"]) == [10.0, 500.0]


def test_parse_fallback_to_list_when_pandas_missing(sample_files):
    """Verifies that parse() returns a list of dicts when HAS_PANDAS is False."""
    with patch("dmanage._compat.HAS_PANDAS", False):
        result = parse(sample_files, checkVars=["L", "T"])
        assert isinstance(result, list)
        assert result == [
            {"L": 10.0, "T": 100.0},
            {"L": 500.0, "T": 400.0},
        ]

#### compose
def test_compose_empty():
    assert compose({}) == ""
    assert compose([]) == ""


def test_compose_dict_basic():
    data = {"a": "1", "b": "2"}
    assert compose(data) == "a-1_b-2"


def test_compose_dict_custom_separators():
    data = {"a": "1", "b": "2"}
    assert compose(data, equiv="=", sep="|") == "a=1|b=2"


def test_compose_list():
    data = ["alpha", "beta", "gamma"]
    assert compose(data, sep="/") == "alpha/beta/gamma"


def test_compose_dict_formatting():
    data = {"val1": 12.34567, "val2": 100}
    # Formats val1 with %.2f, lets val2 fall through to smartString
    result = compose(data, format=["%.2f", None])
    assert "val1-12.35" in result


def test_compose_pandas_dataframe():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame([{"a": "1", "b": "2"}, {"a": "3", "b": "4"}])
    assert compose(df) == "a-1_b-2"


def test_compose_pandas_series():
    pd = pytest.importorskip("pandas")
    s = pd.Series({"a": "1", "b": "2"})
    assert compose(s) == "a-1_b-2"


def test_compose_duck_typed_dataframe_without_pandas():
    """Verifies class-name inspection works even if pandas is not imported/installed."""
    mock_df = MagicMock()
    type(mock_df).__name__ = "DataFrame"
    type(mock_df).__module__ = "pandas.core.frame"
    mock_df.__len__.return_value = 1
    mock_df.iloc[0].to_dict.return_value = {"a": "1", "b": "2"}

    assert compose(mock_df) == "a-1_b-2"
    

if __name__ == "__main__":
    test_compose_empty()
    test_compose_dict_basic()
    test_compose_dict_custom_separators()
    test_compose_list()
    test_compose_dict_formatting()
    # test_compose_pandas_dataframe()
    # test_compose_pandas_series()
    # test_compose_duck_typed_dataframe_without_pandas()
    
    