# -*- coding: utf-8 -*-
import telebot
import os
import os.path
import argparse
import sqlite3
import classeviva as cv
ap = argparse.ArgumentParser()
ap.add_argument("-k", "--key", required=True, type=str,
                help="Telegram bot key")
ap.add_argument("-f", "--working-folder", required=False, type=str,
                default=os.getcwd(),
                help="set the bot's working-folder")
args = vars(ap.parse_args())
bot = telebot.TeleBot(args["key"])
bot_path = args["working_folder"]
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
        USERNAME  CHAR(60) NOT NULL,
        PASSWORD  CHAR(60)
        PERIODO   TINYINT
        CHAT_ID   CHAR(100)""")


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
        risposta(message.chat.id, "/add username to add an username to check \n/remove username to remove an username \n/list to see which users you are currently following")

@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
        risposta(message.chat.id, "/add username to add an username to check \n/remove username to remove an username \n/list to see which users you are currently following")


@bot.message_handler(commands=['medie'])
def handle_list(message):
        chatid = message.chat.id
        username = []
        password = []
        db = sqlite3.connect(bot_path + '/database.db')
        cursor = db.cursor()
        sql = "SELECT USERNAME,PASSWORD FROM CREDENTIALS \
        WHERE CHAT_ID='{}'".format(chatid)
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                username.append(row[0])
                password.append(row[1])
        except Exception as e:
            handle_exception(e)
            #stampare che non si è mai fatto il login
        finally:
            db.close()
        try:
            classeviva_session=cv.Session
            classeviva_session.username=username[0]
            classeviva_session.password=password[0]
            classeviva_session.login(classeviva_session.username,classeviva_session.password)
            voti_json=classeviva_session.grades()
            classeviva_session.logout()
        except Exception as e:
            handle_exception(e)
while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            handle_exception(e)
