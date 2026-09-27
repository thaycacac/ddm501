'''
calculator.py -- Basic computation module
CI/CD demo project with GitHub Actions
'''


class Calculator:
    '''Class performing basic mathematical operations.'''

    def add(self, a: float, b: float) -> float:
        '''Add two numbers.'''
        return a + b

    def subtract(self, a: float, b: float) -> float:
        '''Subtract b from a.'''
        return a - b

    def multiply(self, a: float, b: float) -> float:
        '''Multiply two numbers.'''
        return a * b

    def divide(self, a: float, b: float) -> float:
        '''Divide a by b. Raises ValueError if b = 0.'''
        if b == 0:
            raise ValueError('Cannot divide by zero!')
        return a / b

    def power(self, base: float, exponent: float) -> float:
        '''Calculate base raised to the power of exponent.'''
        return base ** exponent

    def is_positive(self, n: float) -> bool:
        '''Check if a number is positive.'''
        return n > 0
