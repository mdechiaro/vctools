#!/usr/bin/python
""" Check for standard format in git message """
from __future__ import print_function
import subprocess
import sys
import re

class GitCommitCheck(object):
    """ Validates subject and body of commit message """
    def __init__(self, commit):
        self.commit = commit

    @staticmethod
    def validate_subject(commit, subject):
        """
        Validate subject

        commit (str) Commit hash
        message (str) Commit subject

        Returns
            errors (list) A list of errors
        """
        errors = []
        first_word = subject.split()[0]
        if not first_word[0].isupper():
            errors.append('Capitalize first letter of subject ({})'.format(first_word))
        if subject.split()[0].endswith(('ed', 's', 'ing')):
            errors.append('Use imperative present tense in subject ({})'.format(first_word))
        if len(subject.strip()) > 50:
            errors.append('Max characters exceeds 50 in subject ({})'.format(len(subject)))
        if subject.endswith(('.', '?', '!', ':', ';', ',')):
            errors.append(
                'Do not use punctuation at the end of subject ({})'.format(commit)
            )
        if re.match(r'^(I|i)\s', subject):
            errors.append(
                'Do not use personal pronouns. ({})'.format(first_word)
            )
        if errors:
            return errors
        return None

    @staticmethod
    def validate_body(commit, message):
        """
        Validate message body

        commit (str) Commit hash
        message (str) Commit body

        Returns
            errors (list) A list of errors
        """
        errors = []
        lines = message.split('\n')
        for num, line in enumerate(lines):
            if num == 0:
                if line.strip():
                    errors.append('Should be blank (line {} {})'.format(num, commit))
            if line.strip():
                if len(line) > 72:
                    errors.append(
                        'Exceeds max characters of 72 (line {0} {1})'.format(num, commit)
                    )
                if re.match(r'^-', line) and not re.match(r'^--', line):
                    if not re.match(r'^-\s', line):
                        errors.append(
                            '- should be separated by whitespace (line {0} {1})'.format(num, commit)
                        )
                if re.match(r'^\s+-', line.strip()):
                    errors.append(
                        'Do not indent the bullet point (line {0} {1})'.format(num, commit)
                    )
        if errors:
            return errors
        return None

    def main(self):
        """
        Check commit message and exit accordingly:

          exit 0 success
          exit 1 fail
        """
        subject = subprocess.check_output(
            list('git log --format=%s {} -1'.format(self.commit).split())
        )
        body = subprocess.check_output(
            list('git log --format=%b {} -1'.format(self.commit).split())
        )
        subject_results = self.validate_subject(self.commit, subject)
        if subject_results:
            print(
                'subject errors:\n{0}'.format(
                    '\n'.join(subject_results)
                )
            )
            if body.strip():
                body_results = self.validate_body(self.commit, body)
                if body_results:
                    print(
                        'body errors:\n{0}'.format(
                            '\n'.join(body_results)
                        )
                    )
            sys.exit(1)
        sys.exit(0)

if __name__ == '__main__':
    git_check = GitCommitCheck(sys.argv[1])
    sys.exit(git_check.main())
