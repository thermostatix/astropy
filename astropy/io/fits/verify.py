# Licensed under a 3-clause BSD style license - see PYFITS.rst

import operator
import warnings

from astropy.utils import indent
from astropy.utils.exceptions import AstropyUserWarning

__all__ = ['VerifyError', 'VerifyWarning']


class VerifyError(Exception):
    """
    Verify exception class.
    """


class VerifyWarning(AstropyUserWarning):
    """
    Verify warning class.
    """


VERIFY_OPTIONS = ['ignore', 'warn', 'exception', 'fix', 'silentfix',
                  'fix+ignore', 'fix+warn', 'fix+exception',
                  'silentfix+ignore', 'silentfix+warn', 'silentfix+exception']


class _Verify:
    """
    Shared methods for verification.
    """

    def run_option(self, option='warn', err_text='', fix_text='Fixed.',
                   fix=None, fixable=True):
        """
        Execute the verification with selected option.
        """

        text = err_text

        if option in ['warn', 'exception']:
            fixable = False
        # fix the value
        elif not fixable:
            text = f'Unfixable error: {text}'
        else:
            if fix:
                fix()
            text += '  ' + fix_text

        return (fixable, text)

    def verify(self, option='warn'):
        """
        Verify all values in the instance.

        Parameters
        ----------
        option : str
            Output verification option.  Must be one of ``"fix"``,
            ``"silentfix"``, ``"ignore"``, ``"warn"``, or
            ``"exception"``.  May also be any combination of ``"fix"`` or
            ``"silentfix"`` with ``"+ignore"``, ``"+warn"``, or ``"+exception"``
            (e.g. ``"fix+warn"``).  See :ref:`verify` for more info.
        """

        opt = option.lower()
        if opt not in VERIFY_OPTIONS:
            raise ValueError(f'Option {option!r} not recognized.')

        if opt == 'ignore':
            return

        errs = self._verify(opt)

        # Break the verify option into separate options related to reporting of
        # errors, and fixing of fixable errors
        if '+' in opt:
            fix_opt, report_opt = opt.split('+')
        elif opt in ['fix', 'silentfix']:
            # The original default behavior for 'fix' and 'silentfix' was to
            # raise an exception for unfixable errors
            fix_opt, report_opt = opt, 'exception'
        else:
            fix_opt, report_opt = None, opt

        if fix_opt == 'silentfix' and report_opt == 'ignore':
            # Fixable errors were fixed, but don't report anything
            return

        if fix_opt == 'silentfix':
            # Don't print out fixable issues; the first element of each verify
            # item is a boolean indicating whether or not the issue was fixable
            line_filter = lambda x: not x[0]
        elif fix_opt == 'fix' and report_opt == 'ignore':
            # Don't print *unfixable* issues, but do print fixed issues; this
            # is probably not very useful but the option exists for
            # completeness
            line_filter = operator.itemgetter(0)
        else:
            line_filter = None

        unfixable = False
        messages = []
        for fixable, message in errs.iter_lines(filter=line_filter):
            if fixable is not None:
                unfixable = not fixable
            messages.append(message)

        if messages:
            messages.insert(0, 'Verification reported errors:')
            messages.append('Note: astropy.io.fits uses zero-based indexing.\n')

            if fix_opt == 'silentfix' and not unfixable:
                return
            elif report_opt == 'warn' or (fix_opt == 'fix' and not unfixable):
                for line in messages:
                    warnings.warn(line, VerifyWarning)
            else:
                raise VerifyError('\n' + '\n'.join(messages))


class _ErrList(list):
    """
    Verification errors list class.  It has a nested list structure
    constructed by error messages generated by verifications at
    different class levels.
    """

    def __init__(self, val=(), unit='Element'):
        super().__init__(val)
        self.unit = unit

    def __str__(self):
        return '\n'.join(item[1] for item in self.iter_lines())

    def iter_lines(self, filter=None, shift=0):
        """
        Iterate the nested structure as a list of strings with appropriate
        indentations for each level of structure.
        """

        element = 0
        # go through the list twice, first time print out all top level
        # messages
        for item in self:
            if not isinstance(item, _ErrList):
                if filter is None or filter(item):
                    yield item[0], indent(item[1], shift=shift)

        # second time go through the next level items, each of the next level
        # must present, even it has nothing.
        for item in self:
            if isinstance(item, _ErrList):
                next_lines = item.iter_lines(filter=filter, shift=shift + 1)
                try:
                    first_line = next(next_lines)
                except StopIteration:
                    first_line = None

                if first_line is not None:
                    if self.unit:
                        # This line is sort of a header for the next level in
                        # the hierarchy
                        yield None, indent(f'{self.unit} {element}:',
                                           shift=shift)
                    yield first_line

                for line in next_lines:
                    yield line

                element += 1
