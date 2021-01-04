#!/usr/bin/python3
from flask_mail import Mail, Message


def mail_sender(email, url, app):
    mail = Mail(app)
    msg = Message('Завершение регистрации в Ticket Huiket', recipients=[email])
    message_body = 'Завершите регистрацию пройдя по ссылке <p><a href="{}">Перейдите для регистрации</a></p> \n ' \
                   'Если вы не проходили регистрацию Ticket Huiket, проигнорируйте это сообщение' \
                   'Ссылка на регистрацию будет действительна в течении часа' \
                   'Вы всегда можете пройти регистрацию повторно, если не успели завершить регистрацию ' \
                   'в течении часа'.format(url)

    msg.body = message_body
    mail.send(msg)
