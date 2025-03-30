import sqlite3
from datetime import datetime
DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            country TEXT NOT NULL,
            account TEXT NOT NULL,
            format TEXT NOT NULL,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS formats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            format TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT NOT NULL,
            banned INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, banned FROM users ORDER BY user_id")
    users = cursor.fetchall()
    conn.close()
    return users

def set_ban_status(user_id, banned: bool):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = ? WHERE user_id = ?", (int(banned), user_id))
    conn.commit()
    conn.close()

def get_accounts_by_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT country, account FROM accounts WHERE user_id = ? ORDER BY country", (user_id,))
    accounts = cursor.fetchall()
    conn.close()
    return accounts

def add_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def update_users_table():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(users)')
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN user_id INTEGER UNIQUE')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def add_country(user_id, name):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO countries (user_id, name) VALUES (?, ?)', (user_id, name))
    conn.commit()
    conn.close()

def get_countries(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM countries WHERE user_id = ?', (user_id,))
    countries = cursor.fetchall()
    conn.close()
    return countries

def delete_country(user_id, name):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM countries WHERE user_id = ? AND name = ?', (user_id, name))
    cursor.execute('DELETE FROM accounts WHERE user_id = ? AND country = ?', (user_id, name))
    conn.commit()
    conn.close()

def rename_country(user_id, old_name, new_name):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE countries SET name = ? WHERE user_id = ? AND name = ?', (new_name, user_id, old_name))
    cursor.execute('UPDATE accounts SET country = ? WHERE user_id = ? AND country = ?', (new_name, user_id, old_name))
    conn.commit()
    conn.close()

def add_account(user_id, country, account, account_format):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO accounts (user_id, country, account, format) VALUES (?, ?, ?, ?)', (user_id, country, account, account_format))
    conn.commit()
    conn.close()

def get_accounts(user_id, country, number):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT account FROM accounts WHERE user_id = ? AND country = ? LIMIT ?', (user_id, country, number))
    accounts = cursor.fetchall()
    conn.close()
    return [account[0] for account in accounts]

def delete_account(user_id, country, account):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM accounts WHERE user_id = ? AND country = ? AND account = ?', (user_id, country, account))
    conn.commit()
    conn.close()

def delete_all_accounts(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM accounts WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def add_format(format):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO formats (format) VALUES (?)', (format,))
    conn.commit()
    conn.close()

def get_formats():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT format FROM formats')
    formats = cursor.fetchall()
    conn.close()
    return [format[0] for format in formats]

def delete_format(format):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM formats WHERE format = ?', (format,))
    conn.commit()
    conn.close()

def view_accounts(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT country, account FROM accounts WHERE user_id = ?', (user_id,))
    accounts = cursor.fetchall()
    conn.close()
    return accounts

def get_total_accounts(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM accounts WHERE user_id = ?', (user_id,))
    total = cursor.fetchone()[0]
    conn.close()
    return total

def get_total_accounts_by_country(user_id, country):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM accounts WHERE user_id = ? AND country = ?', (user_id, country))
    total = cursor.fetchone()[0]
    conn.close()
    return total

def get_stats(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT country, COUNT(*) FROM accounts WHERE user_id = ? GROUP BY country', (user_id,))
    stats = cursor.fetchall()
    conn.close()
    return stats

def get_account_dates(user_id, country):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT MIN(date_added), MAX(date_added) FROM accounts WHERE user_id = ? AND country = ?', (user_id, country))
    result = cursor.fetchone()
    conn.close()
    if result and result[0] and result[1]:
        first_added = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        last_added = datetime.strptime(result[1], "%Y-%m-%d %H:%M:%S")
        days_since_first = (datetime.now() - first_added).days
        hours_since_first = (datetime.now() - first_added).seconds // 3600
        days_since_last = (datetime.now() - last_added).days
        hours_since_last = (datetime.now() - last_added).seconds // 3600
        return {
            'first_added': first_added,
            'last_added': last_added,
            'days_since_first': days_since_first,
            'hours_since_first': hours_since_first,
            'days_since_last': days_since_last,
            'hours_since_last': hours_since_last
        }
    return None

def get_all_users():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, banned FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def toggle_ban(username):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT banned FROM users WHERE username = ?', (username,))
    current_status = cursor.fetchone()[0]
    new_status = 0 if current_status == 1 else 1
    cursor.execute('UPDATE users SET banned = ? WHERE username = ?', (new_status, username))
    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    conn.close()
    return total

def get_accounts_by_country(username, country):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT account FROM accounts WHERE user_id = (SELECT user_id FROM users WHERE username = ?) AND country = ?', (username, country))
    accounts = cursor.fetchall()
    conn.close()
    return [account[0] for account in accounts]

def get_user_by_username(username):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_id_by_username(username):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE username = ?', (username,))
    user_id = cursor.fetchone()
    conn.close()
    return user_id[0] if user_id else None

def get_user_by_id(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
