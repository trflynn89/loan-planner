import inspect
import random
import sys

# All heuristic functions must end with the string "_heuristic" and have the
# the following prototype:
#
#   loan = my_heuristic(loans, daysSinceLastPayment)
#
# They should use some metric on the given loans and time difference to decide
# which loan should have its monthly payment increased.

def first_loan_heuristic(loans, daysSinceLastPayment):
    '''
    Return the first loan in the list.
    '''
    return loans[0]

def random_heuristic(loans, daysSinceLastPayment):
    '''
    Return a random loan.
    '''
    index = random.randint(1, len(loans))
    return loans[index - 1]

def max_balance_heuristic(loans, daysSinceLastPayment):
    '''
    Return the loan with the highest balance.
    '''
    maxBalanceLoan = None
    maxBalance = -1

    for loan in loans:
        if loan.balance > maxBalance:
            maxBalance = loan.balance
            maxBalanceLoan = loan

    return maxBalanceLoan

def max_interest_rate_heuristic(loans, daysSinceLastPayment):
    '''
    Return the loan with the highest interest rate.
    '''
    maxInterestLoan = None
    maxInterest = -1

    for loan in loans:
        # First check interest
        if loan.interestRate > maxInterest:
            maxInterest = loan.interestRate
            maxInterestLoan = loan

        # Settle tie with balance
        elif loan.interestRate == maxInterest:
            if loan.balance > maxInterestLoan.balance:
                maxInterestLoan = loan

    return maxInterestLoan

def max_interest_accrual_heuristic(loans, daysSinceLastPayment):
    '''
    Return the loan which accrues the most interest in a year.
    '''
    maxInterestLoan = None
    maxInterest = -1

    for loan in loans:
        interest = loan.get_interest_accrued(365.0)

        if interest > maxInterest:
            maxInterest = interest
            maxInterestLoan = loan

    return maxInterestLoan

def max_ipr_heuristic(loans, daysSinceLastPayment):
    '''
    Return the loan with the highest interest-to-monthly-payment ratio.
    '''
    maxIPRLoan = None
    maxIPR = -1

    for loan in loans:
        ipr = loan.get_interest_to_payment_ratio(daysSinceLastPayment)

        if ipr > maxIPR:
            maxIPR = ipr
            maxIPRLoan = loan

    return maxIPRLoan

def min_percent_payment_applied_heuristic(loans, daysSinceLastPayment):
    '''
    Return the loan with the lowest percentage of its monthly payment applied
    to the loan's principal.
    '''
    minPctLoan = None
    minPct = sys.maxint

    for loan in loans:
        interest = loan.get_interest_accrued(daysSinceLastPayment)
        pct = (loan.monthlyPayment - interest) / loan.monthlyPayment

        if pct < minPct:
            minPct = pct
            minPctLoan = loan

    return minPctLoan

def is_heuristic_function(obj):
    '''
    Return true if the given object represents a heuristic function.
    '''
    return (inspect.isfunction(obj) and obj.__name__.endswith('_heuristic'))

ALL_HEURISTICS = inspect.getmembers(sys.modules[__name__], is_heuristic_function)
ALL_HEURISTICS = [heuristic[1] for heuristic in ALL_HEURISTICS]
