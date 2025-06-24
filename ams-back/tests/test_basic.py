import pytest
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


def test_basic_functionality():
    """Basic test to ensure pytest can run successfully."""
    assert True


def test_python_version():
    """Test that we're running on a supported Python version."""
    assert sys.version_info >= (3, 8)


def test_imports():
    """Test that basic Python modules can be imported."""
    import json
    import datetime
    import os
    assert json is not None
    assert datetime is not None
    assert os is not None


class TestBasicMath:
    """Basic math tests to ensure pytest class-based tests work."""
    
    def test_addition(self):
        assert 1 + 1 == 2
    
    def test_subtraction(self):
        assert 5 - 3 == 2
    
    def test_multiplication(self):
        assert 3 * 4 == 12
    
    def test_division(self):
        assert 10 / 2 == 5


@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (4, 8),
])
def test_double_function(input, expected):
    """Test a simple doubling function with parametrized inputs."""
    def double(x):
        return x * 2
    
    assert double(input) == expected


def test_string_operations():
    """Test basic string operations."""
    test_string = "Hello, World!"
    assert len(test_string) == 13
    assert test_string.lower() == "hello, world!"
    assert test_string.upper() == "HELLO, WORLD!"
    assert "World" in test_string


def test_list_operations():
    """Test basic list operations."""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert test_list[0] == 1
    assert test_list[-1] == 5
    assert sum(test_list) == 15


def test_dict_operations():
    """Test basic dictionary operations."""
    test_dict = {"key1": "value1", "key2": "value2"}
    assert len(test_dict) == 2
    assert test_dict["key1"] == "value1"
    assert "key1" in test_dict
    assert list(test_dict.keys()) == ["key1", "key2"]