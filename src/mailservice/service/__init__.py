import datetime
import logging
import re
import threading
import time
import traceback

from mailservice.exception.azure_authen import AzureAuthenticationException
from mailservice.service.azure_oauth2.authenticate import refresh_access_token
from mailservice.service.mail.function import fetch_mails_by_imap, mark_seen_and_move
from mailservice.service.mail.receiver import Mail
from mailservice.util.workerpool import OrEvent, ThreadPool, WorkerThread


class MailService:
    def __init__(self, num_threads: int, config: dict, logger: logging.Logger):
        self.logger = logger
        self.__stop_polling = threading.Event()
        self.worker_pool = ThreadPool(num_threads=num_threads)
        self.config = config  # configuration loaded from config file input
        self.exception_handler = None
        self.last_update_id = 0  # last maild id that was updated to queue: self.list_mail
        self.list_mail = []  # store all imcoming email (that need to be handled)

        self.mail_handlers = (
            []
        )  # list of handlers : [{"function":"", "subject_regex_pattern":""}, ]

        self.firt_run_time = True  # first time run this service -> set to Fasle
        self.token_last_time_update = (
            datetime.datetime.now()
        )  # last time that access token was refreshed
        self.token_expires_in_seconds = 0  # total expired time of token in seconds
        self.access_token = None  # access token of o365 to authen Imap

    def polling(self, interval: int = 5, exception_stop: bool = False):
        """
        call __threaded_polling
        Args:
            interval (int): interval time between 2 times get update
            exception_stop (bool): stop if  AzureAuthenticationException. True -> stop, False -> retry even Azure Exception
        """
        while not self.__stop_polling.is_set():
            try:
                self.__threaded_polling(interval=interval, exception_stop=exception_stop)
            except Exception:
                self.logger.error("Exception traceback:\n%s", traceback.format_exc())
                time.sleep(3)
                continue

    def __threaded_polling(self, interval: int, exception_stop: bool):
        """
        generate polling thread and call __retrieve_updates
        """
        self.__stop_polling.clear()
        error_interval = 0.25

        polling_thread = WorkerThread(name="PollingThread")
        or_event = OrEvent(
            polling_thread.done_event,
            polling_thread.exception_event,
            self.worker_pool.exception_event,
        )
        while not self.__stop_polling.wait(interval):
            or_event.clear()
            try:
                polling_thread.put(self.__retrieve_updates)
                or_event.wait()  # wait for polling thread finish, polling thread error or thread pool error
                polling_thread.raise_exceptions()
                self.worker_pool.raise_exceptions()
                error_interval = 0.25

            except AzureAuthenticationException as e:
                if self.exception_handler is not None:
                    handled = self.exception_handler.handle(e)
                else:
                    handled = False
                if not handled:
                    self.logger.error(e)
                    if exception_stop:
                        self.__stop_polling.set()
                        self.logger.info("Exception occurred. Stopping.")
                    else:
                        # polling_thread.clear_exceptions()
                        # self.worker_pool.clear_exceptions()
                        self.logger.info(f"Waiting for {error_interval} seconds until retry")
                        time.sleep(error_interval)
                        error_interval *= 2
                else:
                    # polling_thread.clear_exceptions()
                    # self.worker_pool.clear_exceptions()
                    time.sleep(error_interval)
                polling_thread.clear_exceptions()  # *
                self.worker_pool.clear_exceptions()  # *

            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt received.")
                self.__stop_polling.set()
                break

            except Exception as e:
                if self.exception_handler is not None:
                    handled = self.exception_handler.handle(e)
                else:
                    handled = False
                if not handled:
                    polling_thread.stop()
                    polling_thread.clear_exceptions()  # *
                    self.worker_pool.clear_exceptions()  # *
                    raise e
                else:
                    polling_thread.clear_exceptions()
                    self.worker_pool.clear_exceptions()
                    time.sleep(error_interval)

        polling_thread.stop()
        polling_thread.clear_exceptions()  # *
        self.worker_pool.clear_exceptions()  # *
        self.logger.info("Stopped polling.")

    def _stop_polling(self):
        self.__stop_polling.set()

    def stop_bot(self):
        """
        Stop bot
        """
        self._stop_polling()
        if self.worker_pool:
            self.worker_pool.close()

    # put task to workerpool (put queue)
    def _exec_task(self, task, *args, **kwargs):
        self.worker_pool.put(task, *args, **kwargs)

    def __retrieve_updates(self):
        self._check_expired_token()
        mails = self.get_updates()
        self._process_new_updates(mails)
        self._process_new_messages()

    def _check_expired_token(self):
        if self.firt_run_time is True:
            # check if first time run -> refresh access_token without checking exprired date
            self.access_token, self.token_expires_in_seconds = refresh_access_token(self.config)
            self.firt_run_time = False
            self.logger.debug(
                "This is first time, get access token and set firt_run_time -> false"
            )
        else:
            # check expired date
            token_liftime_seconds = (
                datetime.datetime.now() - self.token_last_time_update
            ).total_seconds()
            if (self.token_expires_in_seconds - token_liftime_seconds) < 100:
                self.logger.debug(
                    "access token was expired, life time: " + str(token_liftime_seconds) + "s"
                )
                self.logger.debug(
                    "self.token_expires_in_seconds: " + str(self.token_expires_in_seconds) + "s"
                )
                self.access_token, self.token_expires_in_seconds = refresh_access_token(
                    self.config
                )
                self.token_last_time_update = datetime.datetime.now()
                self.logger.debug(
                    "access token was expired, update time: "
                    + self.token_last_time_update.strftime("%m/%d/%Y, %H:%M:%S")
                )

    def get_updates(self):
        """
        Fetch all unread email from mail box
        """
        mails = fetch_mails_by_imap(self.config["USER_NAME"], self.access_token, self.logger)
        return mails

    def _process_new_updates(self, mails: list[Mail]):
        """
        add new email to the self.list_mail(email queue), base on the mail id
        """
        if len(mails) > 0:
            self.logger.debug("There are " + str(len(mails)) + " unread mails in mail box")
            for mail in mails:
                self.logger.debug("mail.id " + str(mail.id))
                self.logger.debug("self.last_update_id " + str(self.last_update_id))
                if int(mail.id) > self.last_update_id:
                    self.last_update_id = int(mail.id)
                    self.list_mail.append(mail)
                    self.logger.debug(
                        "update mail id: "
                        + str(mail.id)
                        + ", subject: "
                        + mail.subject
                        + ", sender: "
                        + mail.sender
                    )
        else:
            self.logger.debug("there are no new email")
        self.logger.debug("number of email in self.list_mail: " + str(len(self.list_mail)))

    def _process_new_messages(self):
        """
        For each email in self.list_mail:  check mail subject is matched with 1 subject_regex_pattern and function
        """
        for mail in self.list_mail:
            has_matched_hander = False
            for message_handler in self.mail_handlers:
                if self.regex_mail_subject(mail.subject, message_handler["subject_regex_pattern"]):
                    has_matched_hander = True
                    self.logger.debug(
                        "matching mail:"
                        + str(mail.subject)
                        + " ,handler: "
                        + str(message_handler["subject_regex_pattern"])
                    )
                    self._exec_task(message_handler["function"], mail)
                    break

            if has_matched_hander is False:
                self.logger.error(
                    "mail id: "
                    + str(mail.id)
                    + ", subject: "
                    + mail.subject
                    + ", sender: "
                    + mail.sender
                    + " no matched handler"
                )
                self.completed_mail(mail=mail, is_success=False)
            self.list_mail.remove(mail)

    def completed_mail(self, mail: Mail, is_success: bool):
        """
        Mark email as read and remove this mail from self.list_mail
        """
        if is_success:
            mark_seen_and_move(
                self.config["USER_NAME"], self.access_token, int(mail.id), "done", self.logger
            )
            self.logger.info(
                "mail id: "
                + str(mail.id)
                + ", subject: "
                + mail.subject
                + ", sender: "
                + mail.sender
                + ": done"
            )
        else:
            mark_seen_and_move(
                self.config["USER_NAME"], self.access_token, int(mail.id), "failed", self.logger
            )
            self.logger.info(
                "mail id: "
                + str(mail.id)
                + ", subject: "
                + mail.subject
                + ", sender: "
                + mail.sender
                + ": failed",
                self.logger,
            )

    @staticmethod
    def regex_mail_subject(subject, pattern):
        pattern = re.compile(pattern)
        return bool(re.search(pattern, subject))

    def mail_handler(self, subject_regex_pattern=None):
        def decorator(handler):
            handler_dict = self._build_handler_dict(handler, regex_pattern=subject_regex_pattern)
            self.add_mail_handler(handler_dict)
            return handler

        return decorator

    def add_mail_handler(self, handler_dict):
        """
        Adds a message handler
        :param handler_dict:
        :return:
        """
        self.mail_handlers.append(handler_dict)

    @staticmethod
    def _build_handler_dict(handler, regex_pattern):
        """
        Builds a dictionary for a handler
        :param handler: function
        :param regex_pattern: regex pattern of mail subject
        :return:
        """
        return {"function": handler, "subject_regex_pattern": regex_pattern}
