'''
loan_config
'''
import ConfigParser
import datetime

class Loan(object):
    '''
    Class to store data pertaining to a loan.
    '''
    def __init__(self, name, balance, interestRate, monthlyPayment, paymentDay):
        self.name = name
        self.balance = balance
        self.interestRate = interestRate / 100.0
        self.monthlyPayment = monthlyPayment
        self.paymentDay = paymentDay

        self.monthlyIncrease = 0
        self.upfrontPayment = 0

    def get_payment_amount(self):
        '''
        Return the monthly payment amount, or the loan balance if the balance
        is less than the monthly payment.
        '''
        return self.monthlyPayment if (self.monthlyPayment < self.balance) else self.balance

    def get_interest_accrued(self, daysAccrued):
        '''
        Calculate the amount of interest accrued in the given number of days.
        '''
        return ((self.balance * self.interestRate) * (daysAccrued /  365.0))

    def get_interest_to_payment_ratio(self, daysAccrued):
        '''
        Calcuate the ratio of the interest paid over a period of time to the
        monthly payment.
        '''
        interestAccrued = self.get_interest_accrued(daysAccrued)
        return (interestAccrued / self.monthlyPayment)

class LoanConfig(object):
    '''
    Configuration options for the loan planner.
    '''
    OPTIONS = 'Options'

    DATE_FORMAT = '%m/%d/%Y'

    UPFRONT_PAYMENT = 'UpfrontPayment'
    MONTHLY_INCREASE = 'MonthlyIncrease'
    DATE_OF_BIRTH = 'DateOfBirth'

    BALANCE = 'Balance'
    INTEREST_RATE = 'InterestRate'
    MONTHLY_PAYMENT = 'MonthlyPayment'
    PAYMENT_DAY = 'PaymentDay'

    # Average number of days per month according to Gregorian calendar
    DAYS_PER_MONTH = 30.436875

    DEFAULTS = {
        UPFRONT_PAYMENT : '0',
        MONTHLY_INCREASE : '0',
        DATE_OF_BIRTH : '1/1/1900',

        BALANCE : '0',
        INTEREST_RATE : '0',
        MONTHLY_PAYMENT : '0',
        PAYMENT_DAY : '1'
    }

    def __init__(self, loanConfigFilePath):
        self.loanConfigFilePath = loanConfigFilePath

        self.upfrontPayment = float()
        self.monthlyIncrease = float()
        self.dateOfBirth = str()
        self.totalBalance = float()
        self.totalMonthlyPayment = float()
        self.loans = [ ]

        self._parse_config_file()

    def __str__(self):
        totalBalance = sum(loan.balance for loan in self.loans)
        totalMonthlyPayment = sum(loan.monthlyPayment for loan in self.loans)

        ret  = 'Total loan balance: $%.2f\n' % (totalBalance)
        ret += 'Upfront payment: $%.2f\n' % (self.upfrontPayment)
        ret += 'Monthly payment increase: $%.2f\n' % (self.monthlyIncrease)
        ret += 'Current monthly payment: $%.2f\n' % (totalMonthlyPayment)
        ret += 'New monthly payment: $%.2f\n' % (totalMonthlyPayment + self.monthlyIncrease)

        loans = list()

        for loan in self.loans:
            name = loan.name
            balance = loan.balance
            interestRate = loan.interestRate * 100.0
            interestAccrued = loan.get_interest_accrued(LoanConfig.DAYS_PER_MONTH)

            loans.append((name, balance, interestRate, interestAccrued))

        loans.sort(key=lambda k: (k[2], k[1]), reverse=True)
        ret += '\nCurrent loans:\n\n'

        for loan in loans:
            ret += '\t{:s}: ${:.2f} at {:.2f}% (${:.2f})\n'.format(*loan)

        return ret

    def any_changes(self):
        '''
        Return true if there were any plan changes in the global options.
        '''
        return (self.upfrontPayment > 0) or (self.monthlyIncrease > 0)

    def parsed(self):
        '''
        Return true if the INI file has been parsed successfully.
        '''
        return (len(self.loans) > 0)

    def _parse_config_file(self):
        '''
        Parse the INI file with all configuration and loan data.
        '''
        parser = ConfigParser.SafeConfigParser(LoanConfig.DEFAULTS)
        parser.read(self.loanConfigFilePath)

        # Parse global options
        if parser.has_section(LoanConfig.OPTIONS):
            self._parse_loan_options(parser)

        # Parse each loan
        for loanName in parser.sections():
            self._parse_loan(parser, loanName)

    def _parse_loan_options(self, parser):
        '''
        Parse the [Options] section in the config file.
        '''
        self.upfrontPayment = parser.getfloat(LoanConfig.OPTIONS, LoanConfig.UPFRONT_PAYMENT)
        self.monthlyIncrease = parser.getfloat(LoanConfig.OPTIONS, LoanConfig.MONTHLY_INCREASE)
        self.dateOfBirth = parser.get(LoanConfig.OPTIONS, LoanConfig.DATE_OF_BIRTH)
        self.dateOfBirth = datetime.datetime.strptime(self.dateOfBirth, LoanConfig.DATE_FORMAT)

        parser.remove_section(LoanConfig.OPTIONS)

    def _parse_loan(self, parser, loanName):
        '''
        Parse a [Loan Name] section in the config file.
        '''
        balance = parser.getfloat(loanName, LoanConfig.BALANCE)
        interestRate = parser.getfloat(loanName, LoanConfig.INTEREST_RATE)
        monthlyPayment = parser.getfloat(loanName, LoanConfig.MONTHLY_PAYMENT)
        paymentDay = parser.getint(loanName, LoanConfig.PAYMENT_DAY)

        loan = Loan(loanName, balance, interestRate, monthlyPayment, paymentDay)
        self.loans.append(loan)
