import json
import logging
import sys
import traceback

from mailservice import MailService
from mailservice.service.bot import bcpkgbot, iabot, pverdocu
from mailservice.service.mail.function import send_error_to_admin
from mailservice.service.mail.receiver import Mail
from mailservice.util.common import get_credential, raw_string

USAGE = "Wrong parameter"
logger = logging.getLogger(__name__)


def main(config: dict) -> None:
    try:
        ms = MailService(num_threads=2, config=config)

        @ms.mail_handler(subject_regex_pattern="^pver")
        def trigger_pverbot(mail: Mail):
            try:
                username, password = get_credential(config["A360_BOT_PVER"])
                bot = pverdocu.PverDocuBot(mail.message, username, password)
                bot.trigger_bot(queue_id="11")
                ms.completed_mail(mail, True)
            except:
                logger.exception("failed to handle PVER Docu email")
                ms.completed_mail(mail, False)
                error_msg = "Pver-Docu bot - Mail content: " + str(mail.message).rstrip()
                send_error_to_admin(config["STMP_BOT_CREDENTIAL"], error_msg)

        @ms.mail_handler(subject_regex_pattern="^navigator-impactanalysis")
        def trigger_nav_iabot(mail: Mail):
            try:
                username, password = get_credential(config["A360_BOT_PMB1HC"])
                bot = iabot.IaBot(mail.message, username, password)
                bot.trigger_bot(mail.sender)
                ms.completed_mail(mail, True)
            except:
                logger.exception("failed to handle Impact Analysis email")
                ms.completed_mail(mail, False)
                error_msg = (
                    "Navigator-ImpactAnalysis bot - Mail content: " + str(mail.message).rstrip()
                )
                send_error_to_admin(config["STMP_BOT_CREDENTIAL"], error_msg)

        @ms.mail_handler(subject_regex_pattern="^navigator-pvertealeaves")
        def trigger_tealeaves_bot(mail: Mail):
            try:
                username, password = get_credential(config["A360_BOT_PMB1HC"])
                bcpkgbot.trigger_tealeaves_bot(
                    message=mail.message,
                    mail_to=mail.sender,
                    bot_username=username,
                    bot_pw=password,
                )
                ms.completed_mail(mail, True)
            except:
                logger.exception("failed to handle Pver Tealeaves email")
                ms.completed_mail(mail, False)
                error_msg = (
                    "Navigator-PverTealeaves bot - Mail content: " + str(mail.message).rstrip()
                )
                send_error_to_admin(config["STMP_BOT_CREDENTIAL"], error_msg)

        @ms.mail_handler(subject_regex_pattern="^navigator-bcprocman")
        def trigger_procman_bot(mail: Mail):
            try:
                username, password = get_credential(config["A360_BOT_PMB1HC"])
                bcpkgbot.trigger_procman_bot(
                    message=mail.message,
                    mail_to=mail.sender,
                    bot_username=username,
                    bot_pw=password,
                )
                ms.completed_mail(mail, True)
            except:
                logger.exception("failed to handle Navigator-BCProcman email")
                ms.completed_mail(mail, False)
                error_msg = "Navigator-BCProcman bot - Mail content: " + str(mail.message).rstrip()
                send_error_to_admin(config["STMP_BOT_CREDENTIAL"], error_msg)

        polling_interval = int(config["POLLING_INTERVAL"])

        ms.polling(interval=polling_interval)

    except Exception:
        print(traceback.format_exc())


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(USAGE)
    else:
        print("Starting mail service.....")
        if args[0] == "-conf":
            print("Loading configuration.....")
            config_file = raw_string(args[1])
            with open(config_file) as f:
                conf_txt = f.read()
            config = json.loads(conf_txt)
            main(config=config)
