import collections
import copy
import datetime

from dateutil import relativedelta

import loan_config

def to_months(timeDiff):
    '''
    Convert a relativedelta instance to raw months.
    '''
    months  = timeDiff.years * 12
    months += timeDiff.months
    months += timeDiff.days / loan_config.LoanConfig.DAYS_PER_MONTH

    return int(round(months))

def get_age_on_date(dateOfBirth, date):
    '''
    Determine the age a person would be on the given date.
    '''
    birthday = dateOfBirth.replace(year=date.year)

    if birthday.month > date.month:
        return (date.year - dateOfBirth.year - 1)

    elif birthday.month == date.month:
        if birthday.day > date.day:
            return (date.year - dateOfBirth.year - 1)

    return (date.year - dateOfBirth.year)

class PaymentStats(object):
    '''
    Class to store statistics about a payment device, or a comparison of two
    sets of statistics about payment devices.
    '''
    def __init__(self, dateOfBirth, isRelative=False):
        self.dateOfBirth = dateOfBirth
        self.isRelative = isRelative

        if self.isRelative:
            self.paymentDifference = 0
            self.monthsDifference = 0
        else:
            self.startDate = None
            self.finishDate = None
            self.finishDateStr = ''
            self.amountPaid = 0
            self.monthsPaid = 0
            self.yearsPaid = 0
            self.finishAge = 0

    def __str__(self):
        if self.isRelative:
            ret  = 'New plan saves $%.2f and finishes %d months earlier\n' % (self.paymentDifference, self.monthsDifference)
        else:
            ret  = '\tYou will pay $%.2f over %d months (%.2f years)\n' % (self.amountPaid, self.monthsPaid, self.yearsPaid)
            ret += '\tApproximate finish date: %s (aged %d)\n' % (self.finishDateStr, self.finishAge)

        return ret

    def compare(self, other):
        '''
        Construct a PaymentStats instance to represent the comparison of these
        payment statistics to another set of statistics.
        '''
        timeSaved = relativedelta.relativedelta(self.finishDate, other.finishDate)

        ret = PaymentStats(self.dateOfBirth, True)
        ret.paymentDifference = self.amountPaid - other.amountPaid
        ret.monthsDifference = to_months(timeSaved)

        return ret

class PaymentDevice(object):
    '''
    Class to simulate paying loans over time.
    '''
    ONE_DAY_DELTA = relativedelta.relativedelta(days=1)
    ONE_MONTH_DELTA = relativedelta.relativedelta(months=1)

    # If this year is reached, stop the simulation
    MAX_YEAR = 3000

    def __init__(self, dateOfBirth, loans, allocationDecider, bestDevice=None):
        self.originalLoans = list()
        self.loans = None

        self.allocationDecider = allocationDecider
        self.bestDevice = bestDevice

        self.paymentStats = PaymentStats(dateOfBirth)
        self.paymentPlan = list()

        for loan in loans:
            if loan.balance <= 0:
                self.paymentPlan.append('Loan %s finished in 0 months\n\n' % (loan.name))
            self.originalLoans.append(loan)

    def __str__(self):
        return '\t'.join(self.paymentPlan)

    def pay_loans(self):
        '''
        Make monthly loan payments until all loans are paid off. When a loan is
        paid, reallocate that loan's monthly payment to another loan. Return a
        boolean indicating if the simulation was successful.
        '''
        self.loans = copy.deepcopy([x for x in self.originalLoans if (x.balance > 0)])
        status = (len(self.loans) > 0)

        self.paymentStats.startDate = datetime.datetime.now()
        currentDate = self.paymentStats.startDate

        while self.loans and status:
            [paidLoans, currentDate] = self._make_payments_until_loan_paid(currentDate)
            status = self._handle_paid_loans(paidLoans, currentDate)

        if status:
            self._collect_payment_stats(currentDate)

        return status

    def _make_payments_until_loan_paid(self, currentDate):
        '''
        Make loan payments starting at the current date, while moving forward a
        day at a time. Stop when one or more loans have been paid off, or if
        this device has already paid more than the given best device.. Return a
        list of those paid loans and the date they were paid off.
        '''
        paidLoans = list()

        while not paidLoans and (currentDate.year < PaymentDevice.MAX_YEAR):
            if self._should_prune_plan():
                self.paymentPlan.append('Prune plan at $%.2f' % (self.paymentStats.amountPaid))
                break

            paidLoans = self._make_payments_on_date(currentDate)
            currentDate += PaymentDevice.ONE_DAY_DELTA

        return [paidLoans, currentDate]

    def _make_payments_on_date(self, paymentDate):
        '''
        Make a single payment to all loans which have a payment due on the
        given date. Return a list of any loans that have been paid off.
        '''
        loans = [x for x in self.loans if x.paymentDay == paymentDate.day]

        lastPaymentDate = paymentDate - PaymentDevice.ONE_MONTH_DELTA
        daysSinceLastPayment = (paymentDate - lastPaymentDate).days

        paidLoans = list()

        for loan in loans:
            if self._make_loan_payment(loan, daysSinceLastPayment):
                self.loans.remove(loan)
                paidLoans.append(loan)

        return paidLoans

    def _make_loan_payment(self, loan, daysSinceLastPayment):
        '''
        Make a payment on a loan, handling accrued interest. Return boolean to
        indicate if the loan is paid off.
        '''
        loan.balance += loan.get_interest_accrued(daysSinceLastPayment)
        payment = loan.get_payment_amount()

        self.paymentStats.amountPaid += payment
        loan.balance -= payment

        return (loan.balance <= 0.0)

    def _should_prune_plan(self):
        '''
        If this payment device was given a best plan so far, compare the amount
        currently paid in this plan to decide if the simulation should just end
        early.
        '''
        if not self.bestDevice:
            return False

        return (self.paymentStats.amountPaid > self.bestDevice.paymentStats.amountPaid)

    def _handle_paid_loans(self, paidLoans, currentDate):
        '''
        Handle all given paid loans, if any. Return boolean to indicate if any
        paid loans were handled.
        '''
        timeSoFar = relativedelta.relativedelta(currentDate, self.paymentStats.startDate)

        if not paidLoans:
            self.paymentPlan.append('Reached end of time without paying all loans\n')
            return False

        for loan in paidLoans:
            self._handle_paid_loan(loan, timeSoFar)

        return True

    def _handle_paid_loan(self, paidLoan, timeSoFar):
        '''
        Handle a single paid loan. Decide which loan should receive the paid
        loan's monthly payment.
        '''
        self.paymentPlan.append('Loan %s finished in %d months\n' % (paidLoan.name, to_months(timeSoFar)))
        increasedLoans = collections.defaultdict(int)

        # Only consider loans which have a balance greater than its payment
        getEligibleLoans = lambda : [x for x in self.loans if (x.balance > x.monthlyPayment)]

        for dollar in range(int(paidLoan.monthlyPayment)):
            loans = getEligibleLoans()

            if loans:
                loan = self.allocationDecider(loans, loan_config.LoanConfig.DAYS_PER_MONTH)

                increasedLoans[loan] += 1
                loan.monthlyPayment += 1

        for loan, increase in increasedLoans.iteritems():
            self.paymentPlan.append('Increase %s by $%.2f to $%.2f\n' % \
                (loan.name, increase, loan.monthlyPayment))

        self.paymentPlan.append('\n')

    def _collect_payment_stats(self, currentDate):
        '''
        Set the payment statistics after the payment simulation has finished.
        '''
        timeDiff = relativedelta.relativedelta(currentDate, self.paymentStats.startDate)

        self.paymentStats.finishDate = currentDate
        self.paymentStats.finishDateStr = currentDate.strftime(loan_config.LoanConfig.DATE_FORMAT)
        self.paymentStats.monthsPaid = to_months(timeDiff)
        self.paymentStats.yearsPaid = self.paymentStats.monthsPaid / 12.0
        self.paymentStats.finishAge = get_age_on_date(self.paymentStats.dateOfBirth, currentDate)
