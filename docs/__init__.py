import datetime
import logging
import threading
import time
import traceback

from mailservice.service.azure_oauth2.authenticate import refresh_access_token
from mailservice.service.mail.function import fetch_mails_by_imap
from mailservice.service.mail.receiver import Mail
from mailservice.util.workerpool import OrEvent, ThreadPool, WorkerThread

logger = logging.getLogger(__name__)


class MailService:
    def __init__(self, num_threads: int, config: dict):
        self.__stop_polling = threading.Event()
        self.worker_pool = ThreadPool(num_threads=num_threads)
        self.config = config
        self.exception_handler = None
        self.last_update_id = 0  # last maild id that was updated to queue: self.list_mail
        self.list_mail = []  # all of new emails

        self.firt_run_time = True  # first time run this service -> set to Fasle
        self.token_last_time_update = (
            datetime.datetime.now()
        )  # last time that access token was refreshed
        self.token_expires_in_seconds = 0  # total expired time of token in seconds
        self.token = None  # access token of o365 to authen Imap

    def polling(self, interval: int = 5):
        while not self.__stop_polling.is_set():
            try:
                self.__threaded_polling(interval=interval)
            except Exception:
                logger.error("Exception traceback:\n%s", traceback.format_exc())
                time.sleep(3)
                continue

    def __threaded_polling(self, interval: int):
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
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received.")
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
        logger.info("Stopped polling.")

    def stop_polling(self):
        self.__stop_polling.set()

    def stop_bot(self):
        self.stop_polling()
        if self.worker_pool:
            self.worker_pool.close()

    # put task to workerpool (put queue)
    def _exec_task(self, task, *args, **kwargs):
        self.worker_pool.put(task, *args, **kwargs)

    def __retrieve_updates(self):
        self._check_exprired_token()
        mails = fetch_mails_by_imap(self.config["USER_NAME"], self.access_token)
        self._process_new_mails(mails)

    def _check_exprired_token(self):
        if self.firt_run_time is True:
            # check if first time run -> refresh access_token without exprired date check
            self.access_token, self.token_expires_in_seconds = refresh_access_token(self.config)
            self.firt_run_time = False
        else:
            # check exprired date
            token_liftime_seconds = (
                datetime.datetime.now() - self.token_last_time_update
            ).total_seconds()
            if (token_liftime_seconds - self.token_expires_in_seconds) < 100:
                self.access_token, self.token_expires_in_seconds = refresh_access_token(
                    self.config
                )
                self.token_last_time_update = datetime.datetime.now()

    def _process_new_mails(self, mails: list[Mail]):
        for mail in mails:
            if mail.id > self.last_update_id:
                self.last_update_id = mail.id
                self.list_mail.append(mail)

    def _mail_handler(self):
        for _mail in self.list_mail:
            self._exec_task()
