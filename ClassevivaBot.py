# -*- coding: utf-8 -*-
import argparse
import logging
import os
import os.path
import sqlite3
import threading
from datetime import date

import classeviva as cv
import telegram
from sympy import Symbol, solve
from telegram.ext import CommandHandler, Updater

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

ap = argparse.ArgumentParser()
ap.add_argument(
    "-k", "--key", required=True, type=str, help="Telegram bot key")
ap.add_argument(
    "-f",
    "--working-folder",
    required=False,
    type=str,
    default=os.getcwd(),
    help="set the bot's working-folder, default is folder from where the bot is executed"
)
args = vars(ap.parse_args())
updater = Updater(token=args["key"])
dispatcher = updater.dispatcher
bot_path = args["working_folder"]
incognita_eq = Symbol("x")


def handle_exception(e):
    print(str(e))


def risposta(sender, messaggio, bot):
    try:
        bot.send_chat_action(chat_id=sender, action="typing")
        bot.send_message(chat_id=sender, text=messaggio)
    except Exception as e:
        handle_exception(e)


def risposta_html(sender, messaggio, bot):
    try:
        bot.send_chat_action(chat_id=sender, action="typing")
        bot.send_message(chat_id=sender, text=messaggio,
                         parse_mode=telegram.ParseMode.HTML)
    except Exception as e:
        handle_exception(e)


def exec_query(query):
    # Open database connection
    db = sqlite3.connect(bot_path + '/database.db')
    # prepare a cursor object using cursor() method
    cursor = db.cursor()
    # Prepare SQL query to INSERT a record into the database.
    try:
        # Execute the SQL command
        cursor.execute(query)
        # Commit your changes in the database
        db.commit()
    except Exception as e:
        # Rollback in case there is any error
        handle_exception(e)
        db.rollback()
    # disconnect from server
    db.close()


# default table creation
exec_query("""CREATE TABLE IF NOT EXISTS CREDENTIALS (
  USERNAME CHAR(60) NOT NULL,
  PASSWORD CHAR(60),
  PERIODO TINYINT DEFAULT 1,
  CHAT_ID CHAR(100)
)""")


def calcola_medie(username, password, periodo):
    classeviva_session = cv.Session()
    classeviva_session.username = username
    classeviva_session.password = password
    try:
        classeviva_session.login(classeviva_session.username,
                                 classeviva_session.password)
    except cv.errors.AuthenticationFailedError:
        raise ValueError("Login error")

    voti_json = classeviva_session.grades()
    classeviva_session.logout()
    if voti_json['grades'] == []:
        raise ValueError('No grades')
    voti_periodo = []
    voti_periodo_fix = []
    dizionario_voti = {}
    medie = {}
    medie_vecchie = {}
    voti_sufficienza = {}
    voti_nuovi = []
    output_risposta = ''
    for x in voti_json['grades']:  # ottenimento lista voti
        voti_periodo.append(x)
    # rimozione voti non appartenenti al periodo non voluto
    for x in range(0, len(voti_periodo)):
        if voti_periodo[x]['periodPos'] == periodo:
            voti_periodo_fix.append(voti_periodo[x])
    # aggiunta dei voti alla rispettiva key del dizionario(ogni key ha un array)
    for x in range(0, len(voti_periodo_fix)):
        # toglie i voti blu dalla media
        if voti_periodo_fix[x]['decimalValue'] != None:
            dizionario_voti.setdefault(
                voti_periodo_fix[x]['subjectDesc'], []).append(
                    (voti_periodo_fix[x]['decimalValue'],
                     voti_periodo_fix[x]['evtDate']))
    # medie nuove
    for materia in dizionario_voti:
        for tupla_voto in dizionario_voti[materia]:
            if materia in medie:  # i dizionari sono stupidi e se la key non esiste già non si può utilizzare +=
                medie[materia] += tupla_voto[0]
            else:
                medie[materia] = tupla_voto[0]
        voti_sufficienza[materia] = round(
            solve((incognita_eq + medie[materia]) /
                  (len(dizionario_voti[materia]) + 1) - 6)[0], 2)
        medie[materia] = round(medie[materia] / len(dizionario_voti[materia]),
                               2)

    # trovare voti nuovi
    for materia in dizionario_voti:
        if dizionario_voti[materia][len(dizionario_voti[materia])
                                    - 1][1].split("-")[2] == date.today().day:
            voti_nuovi.append(materia)
    # calcolare media vecchia
    if voti_nuovi != []:
        for materia in dizionario_voti:
            if materia in voti_nuovi:
                dizionario_voti[materia] = dizionario_voti[materia][:-1]
                # rimuove l'ultimo elemento dall'array del voto(in quanto l'ultimo voto dovrebbe essere quello nuovo)
            else:
                dizionario_voti.pop(materia)
                # rimuove la materia nelle quali non sono cambiati i voti
        for materia in dizionario_voti:
            for tupla_voto in dizionario_voti[materia]:
                if materia in medie_vecchie:
                    # i dizionari sono stupidi e se la key non esiste già non si può utilizzare +=
                    medie_vecchie[materia] += tupla_voto[0]
                else:
                    medie_vecchie[materia] = tupla_voto[0]
            medie_vecchie[materia] = round(
                medie_vecchie[materia] / len(dizionario_voti[materia]), 2)

    def sign_replace(x):
        if ".25" in str(x):
            return str(x).replace(".25", "+")
        elif ".75" in str(x):
            return str(int(str(x).replace(".75", ""))+1)+"-"
        else:
            return str(x)

    for materia in voti_sufficienza:
        output_risposta += "Per avere la sufficenza in " + \
            "<b>" + str(materia) + "</b>" + " devi prendere " + \
            "<b>" + sign_replace(voti_sufficienza[materia]) + "</b>" + "\n"
    output_risposta += "\n\n\n"

    for materia in medie:
        output_risposta += "La media in " + \
            "<b>" + str(materia) + "</b>" + " è " + "<b>" + \
            sign_replace(medie[materia]) + "</b>" + "\n"

    return output_risposta, medie_vecchie


def start(bot, update):
    risposta_html(
        update.message.chat.id,
        "/login <i>username</i> <i>password</i> per accedere\n/logout per disconnettersi\n/periodo per impostare il numero del periodo \n /medie per vedere le medie e che voto per avere la sufficenza ", bot
    )


def periodo(bot, update, args):
    try:
        periodo = None
        chatid = update.message.chat.id
        if len(args) > 1:
            risposta(
                chatid,
                "You may have made a mistake, check your input and try again", bot
            )
            return
        periodo = args[0]
    except Exception as e:
        handle_exception(e)
    exec_query("UPDATE CREDENTIALS \
        SET PERIODO='{}'\
        WHERE CHAT_ID='{}'".format(periodo, chatid))
    risposta(chatid, "periodo aggiornato", bot)


def login(bot, update, args):
    print("login")
    chatid = update.message.chat.id
    try:
        if len(args) > 2:
            risposta(
                chatid,
                "You may have made a mistake, check your input and try again", bot
            )
            return
        username = args[0]
        password = args[1]
    except Exception as e:
        handle_exception(e)
    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()
    sql = "SELECT USERNAME,PASSWORD,PERIODO FROM CREDENTIALS \
        WHERE CHAT_ID='{}'".format(chatid)
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()
    if results == []:
        exec_query(
            "INSERT INTO CREDENTIALS (USERNAME,PASSWORD,CHAT_ID) VALUES('{}','{}','{}')".
            format(username, password, chatid))
        risposta(
            chatid,
            "login effettuato correttamente, il periodo impostato è il primo", bot
        )
    else:
        risposta(chatid, "Il login è già stato effettuato", bot)


def logout(bot, update):
    print("remove")
    chatid = update.message.chat.id
    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()
    sql = "SELECT USERNAME,PASSWORD,PERIODO FROM CREDENTIALS \
        WHERE CHAT_ID='{}'".format(chatid)
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()
    if results == []:
        risposta(
            chatid,
            "Non è mai stato effettuato il login, niente da rimuovere", bot)
        return
    try:
        exec_query(
            "DELETE FROM CREDENTIALS WHERE CHAT_ID='{}'".format(chatid))
        risposta(chatid, "Logout effettuato correttamente", bot)
    except Exception as e:
        handle_exception(e)
        risposta(
            chatid,
            "Si è verificato un errore o non è mai stato effettuato il login", bot
        )


def medie(bot, update):
    chatid = update.message.chat.id
    username = []
    password = []
    periodo = []
    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()
    sql = "SELECT USERNAME,PASSWORD,PERIODO FROM CREDENTIALS \
        WHERE CHAT_ID='{}'".format(chatid)
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            username.append(row[0])
            password.append(row[1])
            periodo.append(row[2])
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()
    if results == []:
        risposta(
            chatid,
            "Non è mai stato fatto il login, effettualo attraverso il comando apposito", bot
        )
        return
    output_risposta = []
    try:
        output_risposta = calcola_medie(
            username[0], password[0], periodo[0])[0]
        risposta_html(chatid, output_risposta, bot)
    except ValueError as e:
        error_value = e.args[0]
        if error_value == "No grades":
            risposta(
                chatid, "Errore, probabilmente non ci sono voti sul registro", bot)
        elif error_value == "Login error":
            risposta(
                chatid, "Errore, probabilmente le tue credenziali sono errate, fai il logout e riprova", bot)


def telegram_bot():

    while True:
        try:
            updater.start_polling()
        except Exception as e:
            handle_exception(e)


def check_voti():
    pass


start_handler = CommandHandler(('start', 'help'), start)
dispatcher.add_handler(start_handler)

periodo_handler = CommandHandler('periodo', periodo, pass_args=True)
dispatcher.add_handler(periodo_handler)

login_handler = CommandHandler('login', login, pass_args=True)
dispatcher.add_handler(login_handler)

logout_handler = CommandHandler('logout', logout)
dispatcher.add_handler(logout_handler)

medie_handler = CommandHandler('medie', medie)
dispatcher.add_handler(medie_handler)


threads = []
check_voti_thread = threading.Thread(target=check_voti)
telegram_bot_thread = threading.Thread(target=telegram_bot)
threads.append(check_voti_thread)
threads.append(telegram_bot_thread)
check_voti_thread.start()
telegram_bot_thread.start()
