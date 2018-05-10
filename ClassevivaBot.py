# -*- coding: utf-8 -*-
import telebot
import os
import os.path
import argparse
import sqlite3
import classeviva as cv
from sympy import Symbol, solve
ap = argparse.ArgumentParser()
ap.add_argument("-k", "--key", required=True, type=str,
                help="Telegram bot key")
ap.add_argument("-f", "--working-folder", required=False, type=str,
                default=os.getcwd(),
                help="set the bot's working-folder, default is folder from where the bot is executed")
args = vars(ap.parse_args())
bot = telebot.TeleBot(args["key"])
bot_path = args["working_folder"]
incognita_eq = Symbol("x")


def handle_exception(e):
    print(str(e))


def risposta(sender, messaggio):
    try:
        bot.send_chat_action(sender, action="typing")
        bot.send_message(sender, messaggio)
    except Exception as e:
        handle_exception(e)


def risposta_html(sender, messaggio):
    try:
        bot.send_chat_action(sender, action="typing")
        bot.send_message(sender, messaggio, parse_mode="HTML")
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
)
""")


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    risposta(message.chat.id, "/login per accedere \n/periodo per impostare il numero del periodo \n /medie per vedere le medie e che voto per avere la sufficenza ")


@bot.message_handler(commands=['periodo'])
def handle_periodo(message):
    print("add")
    try:
        if len(message.text.split(" ")) < 2:
            risposta(
                message.chat.id, "You may have made a mistake, check your input and try again")
            return
        periodo = message.text.split(" ")[1]
    except Exception as e:
        handle_exception(e)
    exec_query("UPDATE CREDENTIALS \
    SET PERIODO='{}'\
    WHERE CHAT_ID='{}'".format(periodo, message.chat.id))
    risposta(message.chat.id, "periodo aggiornato")


@bot.message_handler(commands=['login'])
def handle_login(message):
    print("login")
    try:
        if len(message.text.split(" ")) < 3:
            risposta(
                message.chat.id, "You may have made a mistake, check your input and try again")
            return
        username = message.text.split(" ")[1]
        print(username)
        password = message.text.split(" ")[2]
        print(password)
    except Exception as e:
        handle_exception(e)
    exec_query("INSERT INTO CREDENTIALS (USERNAME,PASSWORD,CHAT_ID) VALUES('{}','{}','{}')".format(
        username, password, message.chat.id))
    risposta(message.chat.id, "login effettuato correttamente")


@bot.message_handler(commands=['medie'])
def handle_medie(message):
    chatid = message.chat.id
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
        '#stampare che non si è mai fatto il login'
    finally:
        db.close()
    try:
        classeviva_session = cv.Session()
        classeviva_session.username = username[0]
        classeviva_session.password = password[0]
        classeviva_session.login(
            classeviva_session.username, classeviva_session.password)
        voti_json = classeviva_session.grades()
        classeviva_session.logout()
        voti_periodo = []
        voti_periodo_fix = []
        dizionario_voti = {}
        medie = {}
        voti_sufficienza = {}
        output_risposta = ''
        for x in voti_json['grades']:  # ottenimento lista voti
            voti_periodo.append(x)
        # rimozione voti non appartenenti al periodo non voluto
        for x in range(0, len(voti_periodo)):
            if voti_periodo[x]['periodPos'] == periodo[0]:
                voti_periodo_fix.append(voti_periodo[x])
        # aggiunta dei voti alla rispettiva key del dizionario(ogni key ha un array)
        for x in range(0, len(voti_periodo_fix)):
            # toglie i voti blu dalla media
            if voti_periodo_fix[x]['decimalValue'] != None:
                dizionario_voti.setdefault(voti_periodo_fix[x]['subjectDesc'], []).append(
                    voti_periodo_fix[x]['decimalValue'])
        for materia in dizionario_voti:
            for voto in dizionario_voti[materia]:
                if materia in medie:  # i dizionari sono stupidi e se la key non esiste già non si può utilizzare +=
                    medie[materia] += voto
                else:
                    medie[materia] = voto
            voti_sufficienza[materia] = round(solve(
                (incognita_eq + medie[materia]) / (len(dizionario_voti[materia]) + 1) - 6)[0], 2)
            medie[materia] = round(
                medie[materia] / len(dizionario_voti[materia]), 2)

        for materia in voti_sufficienza:
            output_risposta += "per avere la sufficenza in " + \
                str(materia) + " devi prendere " + \
                str(voti_sufficienza[materia]) + "\n"
        output_risposta += "\n\n\n"
        for materia in medie:
            output_risposta += "la media in " + \
                str(materia) + " è " + str(medie[materia]) + "\n"
        risposta_html(message.chat.id, output_risposta)
    except Exception as e:
        handle_exception(e)


while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        handle_exception(e)