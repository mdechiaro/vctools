#!/usr/bin/python
""" Task Monitor Class """
from __future__ import print_function
import textwrap
import time
import sys
from vctools import Logger

class Tasks(Logger):
    """ Manage VMware Tasks """
    def __init__(self):
        pass

    @classmethod
    def question_and_answer(cls, host, **answered):
        """
        Method handles the questions and answers provided by the program.

        Args:
            host (obj): VirtualMachine object
            answered (dict): A key value pair of already answered questions.
        """

        if host.runtime.question:
            try:
                qid = host.runtime.question.id

                if not qid in answered.keys():
                    # systemd does not provide a mechanism for disabling cdrom lock
                    if 'CD-ROM door' in host.runtime.question.text:
                        choices = {}
                        for option in host.runtime.question.choice.choiceInfo:
                            choices.update({option.key : option.label})

                        for key, val in choices.iteritems():
                            if 'Yes' in val:
                                answer = key
                    else:
                        print('\n')
                        print('\n'.join(textwrap.wrap(host.runtime.question.text, 80)))
                        choices = {}
                        for option in host.runtime.question.choice.choiceInfo:
                            choices.update({option.key : option.label})
                            sys.stdout.write('\t%s: %s' % (option.key, option.label))

                        warn = textwrap.dedent("""\
                            Warning: The VM may be in a suspended
                            state until this question is answered.""").strip()

                        print(textwrap.fill(warn, width=80))

                        while True:
                            answer = raw_input('\nPlease select number: ').strip()

                            # check if answer is an appropriate number
                            if int(answer) <= len(choices.keys()) - 1:
                                break
                            else:
                                continue

                    if answer:
                        host.AnswerVM(qid, str(answer))
                        answered.update({qid:answer})
                        return answered
            # pass onto next iteration during race condition in task_monitor while loop
            except AttributeError:
                pass

        return None

    @classmethod
    def task_monitor(cls, task, question=True, host=False):
        """
        Method monitors the state of called task and outputs the current status.
        Some tasks require that questions be answered before completion, and are
        optional arguments in the case that some tasks don't require them. It
        will continually check for questions while in progress. The VM object is
        required if the question argument is True.

        Args:
            task (obj):      TaskManager object
            question (bool): Enable or Disable Question
            host (obj):      VirtualMachine object
        Returns:
            boolean (bool):  True if successful or False if error
        """
        # keep track of answered questions
        answered = {}

        while task.info.state == 'running':
            while task.info.progress:
                if question and host:
                    result = Tasks.question_and_answer(host, **answered)
                    if result:
                        answered.update(result)
                if isinstance(task.info.progress, int):
                    sys.stdout.write(
                        '\r[' + task.info.state + '] | ' + str(task.info.progress)
                    )
                    sys.stdout.flush()
                    if task.info.progress == 100:
                        sys.stdout.write(
                            '\r[' + task.info.state + '] | ' + str(task.info.progress)
                        )
                        sys.stdout.flush()
                        break
                else:
                    sys.stdout.flush()
                    break

        # pause method to ensure a state of error or success is caught.
        time.sleep(5)

        if task.info.state == 'error':
            # collect all the error messages we can find
            errors = []
            errors.append(task.info.error.msg)

            for items in task.info.error.faultMessage:
                errors.append(items.message)

            sys.stdout.write('\r[' + task.info.state + '] | ' + ' '.join(errors) + '\n')
            Tasks.logger.info('[' + task.info.state + '] | ' + ' '.join(errors))
            sys.stdout.flush()
            return False

        if task.info.state == 'success':
            sys.stdout.write('\r[' + task.info.state + '] | task successfully completed.\n')
            Tasks.logger.info('[ %s ] task successfully completed.', task.info.state)
            sys.stdout.flush()
            return True
