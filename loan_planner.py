'''
Simulate the payment of a set of loans to suggest an improved payment plan.

Example
-------
python loan_planner.py -c loans.ini
'''
import argparse
import copy
import sys

import heuristics
import loan_config
import payment_device

DEFAULT_CONFIG_FILE_PATH = 'loans.ini'

class LoanPlanner(object):
    '''
    Class to evaluate loan payment plans using a variety of metrics, taking
    into consideration any user-specified payment changes.
    '''
    def __init__(self, loanConfigFilePath):
        self.loanConfig = loan_config.LoanConfig(loanConfigFilePath)

        self.initialPaymentDevices = dict()
        self.changedPaymentDevices = dict()

        self.bestInitialPlan = None
        self.bestChangedPlan = None

    def __str__(self):
        initialPlan = self.bestInitialPlan
        changedPlan = self.bestChangedPlan

        if not self.loanConfig.parsed():
            return 'Could not parse given config file: %s\n' % (self.loanConfig.loanConfigFilePath)

        if not initialPlan and not changedPlan:
            return 'Could not determine a payment plan for the given loans\n'

        ret = '%s\n' % (self.loanConfig)

        if changedPlan:
            originalLoans = changedPlan.originalLoans
            ret += 'Changes to make:\n\n'

            for loan in [x for x in originalLoans if x.upfrontPayment > 0]:
                ret += '\tMake an initial $%.2f payment to %s\n' % (loan.upfrontPayment, loan.name)

            for loan in [x for x in originalLoans if x.monthlyIncrease > 0]:
                ret += '\tIncrease %s by $%.2f to $%.2f\n' % (loan.name, loan.monthlyIncrease, loan.monthlyPayment)

            ret += '\n'
        else:
            ret += 'No changes to make\n\n'

        ret += 'Payment plan:\n\n'
        ret += '\t%s\n' % (changedPlan if changedPlan else initialPlan)

        if initialPlan:
            ret += 'Without changing payment plan:\n\n%s\n' % (initialPlan.paymentStats)

        if changedPlan:
            ret += 'By using this new plan:\n\n%s\n' % (changedPlan.paymentStats)

        if initialPlan and changedPlan:
            ret += '%s\n' % (initialPlan.paymentStats.compare(changedPlan.paymentStats))

        return ret

    def find_best_plan(self):
        '''
        Simulate the payment of all loans before and after changes to the
        payment plans, using all available metrics. Decide which of all plans
        is the best.
        '''
        if not self.loanConfig.parsed():
            return

        if self._do_initial_payments() and self.loanConfig.any_changes():
            self._do_changed_payments()

    def _do_initial_payments(self):
        '''
        Without making changes to the payment plans, simulate the payment of
        all loans using all available metrics. Return true if any simulations
        were completed successfully.
        '''
        for heuristic in heuristics.ALL_HEURISTICS:
            paymentDevice = payment_device.PaymentDevice(
                self.loanConfig.dateOfBirth, self.loanConfig.loans, heuristic, self.bestInitialPlan)

            if paymentDevice.pay_loans():
                self.initialPaymentDevices[heuristic] = paymentDevice
                self.bestInitialPlan = self._get_best_payment_plan(self.initialPaymentDevices)

        return (len(self.initialPaymentDevices) > 0)

    def _do_changed_payments(self):
        '''
        For all available metrics, make any changes to loan payment plans that
        were specified by the user. Then, simulate the payment of all loans.
        '''
        for heuristic in self.initialPaymentDevices:
            loans = copy.deepcopy(self.loanConfig.loans)

            self._allocate_upfront_payment(loans, heuristic)
            self._allocate_monthly_increase(loans, heuristic)

            paymentDevice = payment_device.PaymentDevice(
                self.loanConfig.dateOfBirth, loans, heuristic, self.bestChangedPlan)

            if paymentDevice.pay_loans():
                self.changedPaymentDevices[heuristic] = paymentDevice
                self.bestChangedPlan = self._get_best_payment_plan(self.changedPaymentDevices)

    def _allocate_upfront_payment(self, loans, heuristic):
        '''
        Use the given metric to modify the given loans using the user-specified
        upfront payment amount.
        '''
        unpaid = lambda x: x.balance > 0
        paid = lambda x: x.balance <= 0

        for dollar in range(int(self.loanConfig.upfrontPayment)):
            loan = heuristic(filter(unpaid, loans), payment_device.PaymentDevice.DAYS_PER_MONTH)
            loan.upfrontPayment += 1
            loan.balance -= 1

        for loan in filter(paid, loans):
            for dollar in range(int(loan.monthlyPayment)):
                loan2 = heuristic(filter(unpaid, loans), payment_device.PaymentDevice.DAYS_PER_MONTH)
                loan2.monthlyIncrease += 1
                loan2.monthlyPayment += 1

    def _allocate_monthly_increase(self, loans, heuristic):
        '''
        Use the given metric to modify the given loans using the user-specified
        monthly payment increase.
        '''
        unpaid = lambda x: x.balance > 0

        for dollar in range(int(self.loanConfig.monthlyIncrease)):
            loan = heuristic(filter(unpaid, loans), payment_device.PaymentDevice.DAYS_PER_MONTH)
            loan.monthlyIncrease += 1
            loan.monthlyPayment += 1

    def _get_best_payment_plan(self, listOfPaymentPlans):
        '''
        Return the best payment plan in the given list of plans.
        '''
        bestPlan = None

        for [heuristic, plan] in listOfPaymentPlans.iteritems():
            amountPaid = plan.paymentStats.amountPaid
            lowestAmountPaid = bestPlan.paymentStats.amountPaid if bestPlan else 0

            if not bestPlan or (amountPaid < lowestAmountPaid):
                bestPlan = plan

        return bestPlan

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)

    parser.add_argument(
        '-c', '--config-file-path', dest='config_file_path',
        default=DEFAULT_CONFIG_FILE_PATH, help='Path to loan configuration file')

    args = parser.parse_args()

    loanPlanner = LoanPlanner(args.config_file_path)
    loanPlanner.find_best_plan()
    print loanPlanner

    return (loanPlanner.bestInitialPlan or loanPlanner.bestChangedPlan)

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
