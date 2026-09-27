import pytest
from src.calculator import Calculator


# Shared Calculator instance for all tests
@pytest.fixture
def calc():
    return Calculator()


# Addition tests
class TestAddition:
    def test_add_two_positive_numbers(self, calc):
        assert calc.add(3, 5) == 8

    def test_add_negative_numbers(self, calc):
        assert calc.add(-3, -5) == -8

    def test_add_positive_and_negative(self, calc):
        assert calc.add(10, -3) == 7

    def test_add_with_zero(self, calc):
        assert calc.add(5, 0) == 5

    def test_add_floats(self, calc):
        assert abs(calc.add(1.5, 2.3) - 3.8) < 0.0001


# Subtraction tests
class TestSubtraction:
    def test_subtract_basic(self, calc):
        assert calc.subtract(10, 4) == 6

    def test_subtract_resulting_negative(self, calc):
        assert calc.subtract(3, 10) == -7


# Multiplication tests
class TestMultiplication:
    def test_multiply_basic(self, calc):
        assert calc.multiply(4, 5) == 20

    def test_multiply_by_zero(self, calc):
        assert calc.multiply(100, 0) == 0

    def test_multiply_negatives(self, calc):
        assert calc.multiply(-3, -4) == 12


# Division tests
class TestDivision:
    def test_divide_basic(self, calc):
        assert calc.divide(10, 2) == 5

    def test_divide_resulting_float(self, calc):
        assert calc.divide(7, 2) == 3.5

    def test_divide_by_zero_raises_error(self, calc):
        with pytest.raises(ValueError, match='Cannot divide by zero'):
            calc.divide(10, 0)


# Other operation tests
class TestOtherOperations:
    def test_power_basic(self, calc):
        assert calc.power(2, 10) == 1024

    def test_power_zero_exponent(self, calc):
        assert calc.power(999, 0) == 1

    def test_is_positive_true(self, calc):
        assert calc.is_positive(5)

    def test_is_positive_false(self, calc):
        assert not calc.is_positive(-1)

    def test_is_positive_zero(self, calc):
        assert not calc.is_positive(0)
