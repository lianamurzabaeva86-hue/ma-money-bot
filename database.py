import sqlite3
import logging
from datetime import datetime, timedelta
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка московского времени
MOSCOW_TZ = pytz.timezone('Europe/Moscow')


class Database:
    def __init__(self, db_path='bot_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()
        self.fix_database_structure()
        self.check_for_triggers()

    def get_moscow_time(self):
        """Получение текущего московского времени"""
        return datetime.now(MOSCOW_TZ)

    def format_moscow_time(self, dt=None):
        """Форматирование времени для SQLite в московском времени"""
        if dt is None:
            dt = self.get_moscow_time()
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def is_working_hours(self):
        """Проверка, рабочие ли сейчас часы (до 20:00 по Москве)"""
        try:
            moscow_time = self.get_moscow_time()
            current_hour = moscow_time.hour
            current_minute = moscow_time.minute
            if current_hour < 20:
                return True
            elif current_hour == 20 and current_minute == 0:
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error checking working hours: {e}")
            return True

    def can_user_interact(self, user_id=None):
        try:
            if not self.is_working_hours():
                moscow_time = self.get_moscow_time()
                current_time_str = moscow_time.strftime('%H:%M')
                if moscow_time.hour < 7:
                    return False, f"⏰ Бот начнёт работу в 7:00 по Москве. Сейчас {current_time_str} МСК"
                if moscow_time.hour >= 20:
                    return False, f"⏰ Бот завершил работу на сегодня. Сейчас {current_time_str} МСК\nЗадания будут доступны завтра с 7:00 утра!"
                return False, f"⏰ Бот временно не работает. Сейчас {current_time_str} МСК"
            return True, ""
        except Exception as e:
            logger.error(f"Error in can_user_interact: {e}")
            return True, ""

    def is_bot_active(self):
        try:
            moscow_time = self.get_moscow_time()
            current_hour = moscow_time.hour
            is_active = 7 <= current_hour < 20
            if not is_active:
                logger.info(f"🕒 Бот неактивен по времени: {moscow_time.strftime('%H:%M')} МСК")
            return is_active
        except Exception as e:
            logger.error(f"Error checking bot activity: {e}")
            return True

    def init_db(self):
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance REAL DEFAULT 0,
                    total_earned REAL DEFAULT 0,
                    ref_count INTEGER DEFAULT 0,
                    ref_earned REAL DEFAULT 0,
                    invited_by INTEGER,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (invited_by) REFERENCES users (user_id)
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocked_referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referral_id INTEGER NOT NULL,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referral_id) REFERENCES users (user_id),
                    UNIQUE(referrer_id, referral_id)
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    price REAL NOT NULL,
                    description TEXT,
                    instruction TEXT,
                    link TEXT,
                    max_completions INTEGER DEFAULT 1,
                    current_completions INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_tasks (
                    user_task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    task_id INTEGER,
                    status TEXT DEFAULT 'assigned',
                    screenshot_file_id TEXT,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    submitted_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (task_id) REFERENCES tasks (task_id)
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS withdrawals (
                    withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    bank_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    username TEXT
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS pinned_ads (
                    ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_text TEXT NOT NULL,
                    ad_link TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_text TEXT NOT NULL,
                    message_type TEXT DEFAULT 'notification',
                    sent_by_admin_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_users INTEGER DEFAULT 0,
                    successful_sends INTEGER DEFAULT 0,
                    failed_sends INTEGER DEFAULT 0
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS advertisements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_text TEXT NOT NULL,
                    ad_link TEXT NOT NULL,
                    reach_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing database: {e}")

    def fix_database_structure(self):
        try:
            print("🔧 Checking database structure...")
            tables_to_check = [
                ('blocked_referrals', '''
                    CREATE TABLE blocked_referrals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        referrer_id INTEGER NOT NULL,
                        referral_id INTEGER NOT NULL,
                        blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                        FOREIGN KEY (referral_id) REFERENCES users (user_id),
                        UNIQUE(referrer_id, referral_id)
                    )
                '''),
                ('pinned_ads', '''
                    CREATE TABLE pinned_ads (
                        ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ad_text TEXT NOT NULL,
                        ad_link TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by INTEGER
                    )
                '''),
                ('broadcasts', '''
                    CREATE TABLE broadcasts (
                        broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_text TEXT NOT NULL,
                        message_type TEXT DEFAULT 'notification',
                        sent_by_admin_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_users INTEGER DEFAULT 0,
                        successful_sends INTEGER DEFAULT 0,
                        failed_sends INTEGER DEFAULT 0
                    )
                '''),
                ('advertisements', '''
                    CREATE TABLE advertisements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ad_text TEXT NOT NULL,
                        ad_link TEXT NOT NULL,
                        reach_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            ]
            for table_name, create_sql in tables_to_check:
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                if not self.cursor.fetchone():
                    print(f"✅ Creating {table_name} table")
                    self.cursor.execute(create_sql)
            table_columns = {
                'pinned_ads': ['created_by'],
                'broadcasts': ['total_users', 'successful_sends', 'failed_sends'],
                'user_tasks': ['submitted_at', 'screenshot_file_id'],
                'users': ['ref_count', 'ref_earned']
            }
            for table_name, columns in table_columns.items():
                self.cursor.execute(f"PRAGMA table_info({table_name})")
                existing_columns = [col[1] for col in self.cursor.fetchall()]
                for column in columns:
                    if column not in existing_columns:
                        print(f"✅ Adding {column} column to {table_name}")
                        if column in ['total_users', 'successful_sends', 'failed_sends', 'ref_count']:
                            self.cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column} INTEGER DEFAULT 0')
                        elif column in ['ref_earned']:
                            self.cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column} REAL DEFAULT 0')
                        elif column == 'created_by':
                            self.cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column} INTEGER')
                        else:
                            self.cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column} TEXT')
            self.conn.commit()
            print("✅ Database structure check completed")
        except Exception as e:
            print(f"❌ Error fixing database structure: {e}")

    def check_for_triggers(self):
        try:
            self.cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
            triggers = self.cursor.fetchall()
            if triggers:
                print("⚠️ Обнаружены триггеры в базе данных:")
                for trigger_name, trigger_sql in triggers:
                    print(f"   🔔 {trigger_name}: {trigger_sql}")
                    if 'current_completions' in trigger_sql:
                        print(f"🚨 Удаляю опасный триггер: {trigger_name}")
                        self.cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
                        self.conn.commit()
            else:
                print("✅ Опасные триггеры не обнаружены")
        except Exception as e:
            print(f"❌ Error checking triggers: {e}")

    # === МЕТОДЫ ДЛЯ РЕКЛАМЫ И РАССЫЛКИ ===
    def save_advertisement(self, ad_text, ad_link, reach_count):
        try:
            moscow_time = self.format_moscow_time()
            self.cursor.execute(
                "INSERT INTO advertisements (ad_text, ad_link, reach_count, created_at) VALUES (?, ?, ?, ?)",
                (ad_text, ad_link, reach_count, moscow_time)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving advertisement: {e}")
            return False

    def get_ads_history(self, limit=5):
        try:
            self.cursor.execute("SELECT * FROM advertisements ORDER BY created_at DESC LIMIT ?", (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting ads history: {e}")
            return []

    def create_pinned_ad(self, ad_text, ad_link, created_by=None):
        try:
            self.deactivate_all_ads()
            moscow_time = self.format_moscow_time()
            self.cursor.execute('''
                INSERT INTO pinned_ads (ad_text, ad_link, created_by, created_at, is_active)
                VALUES (?, ?, ?, ?, TRUE)
            ''', (ad_text, ad_link, created_by, moscow_time))
            ad_id = self.cursor.lastrowid
            self.conn.commit()
            return ad_id, "✅ Реклама успешно создана и активирована"
        except Exception as e:
            logger.error(f"Error creating pinned ad: {e}")
            return None, f"❌ Ошибка при создании рекламы: {e}"

    def get_active_advertisement(self):
        try:
            self.cursor.execute('''
                SELECT * FROM pinned_ads 
                WHERE is_active = TRUE
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting active pinned ad: {e}")
            return None

    def get_all_pinned_ads(self):
        try:
            self.cursor.execute('''
                SELECT pa.*, u.username as created_by_username
                FROM pinned_ads pa
                LEFT JOIN users u ON pa.created_by = u.user_id
                ORDER BY pa.created_at DESC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all pinned ads: {e}")
            return []

    def deactivate_all_ads(self):
        try:
            self.cursor.execute('UPDATE pinned_ads SET is_active = FALSE WHERE is_active = TRUE')
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deactivating all ads: {e}")
            return False

    def get_ad_stats(self):
        try:
            self.cursor.execute('SELECT COUNT(*) FROM pinned_ads')
            total_ads = self.cursor.fetchone()[0]
            self.cursor.execute('SELECT COUNT(*) FROM pinned_ads WHERE is_active = TRUE')
            active_ads = self.cursor.fetchone()[0]
            return {'total_ads': total_ads, 'active_ads': active_ads}
        except Exception as e:
            logger.error(f"Error getting ad stats: {e}")
            return {}

    def get_all_user_ids(self):
        try:
            self.cursor.execute('SELECT user_id FROM users')
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all user IDs: {e}")
            return []

    def create_broadcast(self, message_text, message_type="notification", sent_by_admin_id=None):
        try:
            moscow_time = self.format_moscow_time()
            total_users = len(self.get_all_user_ids())
            self.cursor.execute('''
                INSERT INTO broadcasts (message_text, message_type, sent_by_admin_id, created_at, total_users)
                VALUES (?, ?, ?, ?, ?)
            ''', (message_text, message_type, sent_by_admin_id, moscow_time, total_users))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating broadcast: {e}")
            return None

    def update_broadcast_stats(self, broadcast_id, successful_sends, failed_sends):
        try:
            self.cursor.execute('UPDATE broadcasts SET successful_sends = ?, failed_sends = ? WHERE broadcast_id = ?', (successful_sends, failed_sends, broadcast_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating broadcast stats: {e}")
            return False

    def get_broadcast_history(self, limit=50):
        try:
            self.cursor.execute('SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT ?', (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting broadcast history: {e}")
            return []

    # === УПРАВЛЕНИЕ ЗАДАНИЯМИ ===
    def get_active_tasks_for_user(self, user_id):
        try:
            can_interact, message = self.can_user_interact(user_id)
            if not can_interact:
                return []
            self.cursor.execute('''
                SELECT t.* 
                FROM tasks t
                WHERE t.is_active = 1 
                AND t.current_completions < t.max_completions
                AND t.task_id NOT IN (
                    SELECT task_id FROM user_tasks 
                    WHERE user_id = ? AND status IN ('assigned', 'submitted')
                )
                ORDER BY t.created_at DESC
            ''', (user_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return []

    def create_task(self, title, price, description, instruction, link, max_completions):
        try:
            moscow_time = self.format_moscow_time()
            self.cursor.execute('''
                INSERT INTO tasks (title, price, description, instruction, link, max_completions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, price, description, instruction, link, max_completions, moscow_time))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    def get_task(self, task_id):
        try:
            self.cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    def get_all_tasks(self):
        try:
            self.cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all tasks: {e}")
            return []

    def assign_task_to_user(self, user_id, task_id):
        """Назначение задания — сразу занимаем слот (увеличиваем current_completions)"""
        try:
            can_interact, _ = self.can_user_interact(user_id)
            if not can_interact:
                return None
            if self.get_user_active_task(user_id):
                return None
            task = self.get_task(task_id)
            if not task:
                return None
            current_completions = task[7]
            max_completions = task[6]
            if current_completions >= max_completions:
                return None
            if not self.can_user_take_task(user_id, task_id):
                return None

            self.conn.execute('BEGIN IMMEDIATE')
            try:
                # 🔥 Занимаем слот СРАЗУ
                self.cursor.execute('''
                    UPDATE tasks 
                    SET current_completions = current_completions + 1 
                    WHERE task_id = ? AND current_completions < max_completions
                ''', (task_id,))
                if self.cursor.rowcount == 0:
                    self.conn.rollback()
                    return None

                expires_at = self.get_moscow_time() + timedelta(minutes=15)
                self.cursor.execute('''
                    INSERT INTO user_tasks (user_id, task_id, status, assigned_at, expires_at)
                    VALUES (?, ?, 'assigned', ?, ?)
                ''', (user_id, task_id, self.format_moscow_time(), self.format_moscow_time(expires_at)))
                self.conn.commit()
                return self.cursor.lastrowid
            except Exception:
                self.conn.rollback()
                raise
        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            return None

    def submit_task(self, user_task_id, screenshot_file_id):
        try:
            self.cursor.execute('SELECT user_id FROM user_tasks WHERE user_task_id = ?', (user_task_id,))
            result = self.cursor.fetchone()
            if result:
                user_id = result[0]
                can_interact, message = self.can_user_interact(user_id)
                if not can_interact:
                    return False
            self.cursor.execute('SELECT user_task_id, user_id, task_id, status FROM user_tasks WHERE user_task_id = ?', (user_task_id,))
            task = self.cursor.fetchone()
            if not task:
                return False
            if task[3] != 'assigned':
                return False
            submitted_at_str = self.format_moscow_time()
            self.cursor.execute('''
                UPDATE user_tasks 
                SET status = 'submitted', screenshot_file_id = ?, submitted_at = ?
                WHERE user_task_id = ?
            ''', (screenshot_file_id, submitted_at_str, user_task_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error submitting task: {e}")
            return False

    def get_user_active_task(self, user_id):
        try:
            self.cursor.execute('''
                SELECT * FROM user_tasks 
                WHERE user_id = ? AND status = 'assigned'
                ORDER BY assigned_at DESC LIMIT 1
            ''', (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user active task: {e}")
            return None

    def get_pending_tasks(self):
        try:
            self.cursor.execute('''
                SELECT 
                    ut.user_task_id, 
                    ut.user_id, 
                    ut.task_id, 
                    ut.status, 
                    ut.screenshot_file_id,
                    ut.submitted_at,
                    u.username, 
                    t.title, 
                    t.price
                FROM user_tasks ut
                JOIN users u ON ut.user_id = u.user_id
                JOIN tasks t ON ut.task_id = t.task_id
                WHERE ut.status = 'submitted'
                ORDER BY ut.submitted_at ASC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting pending tasks: {e}")
            return []

    def approve_task(self, user_task_id):
        """Одобрение — НЕ увеличиваем счётчик (он уже увеличен при взятии)"""
        try:
            self.conn.execute('BEGIN TRANSACTION')
            try:
                self.cursor.execute('''
                    SELECT ut.user_id, ut.task_id, ut.status, t.title, t.price
                    FROM user_tasks ut
                    JOIN tasks t ON ut.task_id = t.task_id
                    WHERE ut.user_task_id = ?
                ''', (user_task_id,))
                task_info = self.cursor.fetchone()
                if not task_info:
                    self.conn.rollback()
                    return False
                user_id, task_id, status, title, price = task_info
                if status != 'submitted':
                    self.conn.rollback()
                    return False

                completed_at_str = self.format_moscow_time()
                self.cursor.execute(
                    'UPDATE user_tasks SET status = ?, completed_at = ? WHERE user_task_id = ?',
                    ('approved', completed_at_str, user_task_id)
                )
                self.cursor.execute(
                    'UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?',
                    (price, price, user_id)
                )
                # Проверяем, достигнут ли лимит — деактивируем при необходимости
                self.cursor.execute('SELECT current_completions, max_completions FROM tasks WHERE task_id = ?', (task_id,))
                curr, mx = self.cursor.fetchone()
                if curr >= mx:
                    self.cursor.execute('UPDATE tasks SET is_active = 0 WHERE task_id = ?', (task_id,))
                self.conn.commit()
                return True
            except Exception as e:
                self.conn.rollback()
                raise e
        except Exception as e:
            logger.error(f"Error in approve_task: {e}")
            return False

    def reject_task_with_reason(self, user_task_id, reason):
        """Отклонение — освобождаем слот"""
        try:
            self.conn.execute('BEGIN TRANSACTION')
            try:
                self.cursor.execute('''
                    SELECT ut.task_id, ut.status 
                    FROM user_tasks ut
                    WHERE ut.user_task_id = ?
                ''', (user_task_id,))
                row = self.cursor.fetchone()
                if not row or row[1] != 'submitted':
                    self.conn.rollback()
                    return False
                task_id = row[0]

                # 🔥 Освобождаем слот
                self.cursor.execute('''
                    UPDATE tasks 
                    SET current_completions = MAX(0, current_completions - 1)
                    WHERE task_id = ?
                ''', (task_id,))

                self.cursor.execute('''
                    UPDATE user_tasks 
                    SET status = 'rejected', screenshot_file_id = ?
                    WHERE user_task_id = ?
                ''', (f'REASON: {reason}', user_task_id))
                self.conn.commit()
                return True
            except Exception as e:
                self.conn.rollback()
                raise e
        except Exception as e:
            logger.error(f"Error in reject_task_with_reason: {e}")
            return False

    def get_user_task_info(self, user_task_id):
        try:
            self.cursor.execute('''
                SELECT ut.user_id, t.title, t.price, t.task_id
                FROM user_tasks ut
                JOIN tasks t ON ut.task_id = t.task_id
                WHERE ut.user_task_id = ?
            ''', (user_task_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user task info: {e}")
            return None

    def can_user_take_task(self, user_id, task_id):
        try:
            self.cursor.execute('''
                SELECT COUNT(*) FROM user_tasks 
                WHERE user_id = ? AND task_id = ? AND status = 'assigned'
            ''', (user_id, task_id))
            return self.cursor.fetchone()[0] == 0
        except Exception as e:
            logger.error(f"Error checking if user can take task: {e}")
            return False

    def get_user_pending_tasks(self, user_id):
        try:
            self.cursor.execute('''
                SELECT ut.*, t.title, t.price 
                FROM user_tasks ut 
                JOIN tasks t ON ut.task_id = t.task_id 
                WHERE ut.user_id = ? AND ut.status = "submitted"
            ''', (user_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user pending tasks: {e}")
            return []

    def cleanup_expired_tasks(self):
        """Очистка просроченных заданий с освобождением слотов"""
        try:
            current_time_str = self.format_moscow_time()
            self.cursor.execute('''
                SELECT user_task_id, task_id
                FROM user_tasks 
                WHERE status = 'assigned' AND expires_at < ?
            ''', (current_time_str,))
            expired = self.cursor.fetchall()
            if not expired:
                return 0

            self.conn.execute('BEGIN IMMEDIATE')
            try:
                for user_task_id, task_id in expired:
                    self.cursor.execute('UPDATE tasks SET current_completions = MAX(0, current_completions - 1) WHERE task_id = ?', (task_id,))
                    self.cursor.execute('UPDATE user_tasks SET status = "expired" WHERE user_task_id = ?', (user_task_id,))
                self.conn.commit()
                logger.info(f"🧹 Очищено {len(expired)} просроченных заданий")
                return len(expired)
            except Exception:
                self.conn.rollback()
                raise
        except Exception as e:
            logger.error(f"Error cleaning expired tasks: {e}")
            return 0

    def check_expired_tasks(self):
        """Обёртка для совместимости с внешним кодом."""
        return self.cleanup_expired_tasks()

    # 🔥 ДОБАВЛЕННЫЙ МЕТОД: УДАЛЕНИЕ ЗАДАНИЯ НАВСЕГДА
    def delete_task(self, task_id):
        """Удаляет задание и все связанные записи в user_tasks"""
        try:
            self.cursor.execute('DELETE FROM user_tasks WHERE task_id = ?', (task_id,))
            self.cursor.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False

    # === ПОЛЬЗОВАТЕЛИ ===
    def add_user(self, user_id, username=None, invited_by=None):
        try:
            existing_user = self.get_user(user_id)
            if existing_user:
                return True
            if invited_by and invited_by == user_id:
                invited_by = None
            if invited_by:
                referrer_exists = self.get_user(invited_by)
                if not referrer_exists:
                    invited_by = None
                else:
                    if self.is_referral_blocked(invited_by, user_id):
                        invited_by = None
            moscow_time = self.format_moscow_time()
            if invited_by:
                self.cursor.execute('''
                    INSERT INTO users (user_id, username, invited_by, registered_at) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, invited_by, moscow_time))
                self.increment_ref_count(invited_by)
            else:
                self.cursor.execute('''
                    INSERT INTO users (user_id, username, registered_at) 
                    VALUES (?, ?, ?)
                ''', (user_id, username, moscow_time))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Error adding user {user_id}: {e}")
            return False

    def get_user(self, user_id):
        try:
            self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    def get_all_users(self):
        try:
            self.cursor.execute('SELECT * FROM users ORDER BY registered_at DESC')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def update_user_balance(self, user_id, amount):
        try:
            self.cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return False

    def update_ref_earned(self, user_id, amount):
        try:
            self.cursor.execute('UPDATE users SET ref_earned = ref_earned + ? WHERE user_id = ?', (amount, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating ref earned: {e}")
            return False

    def update_total_earned(self, user_id, amount):
        try:
            self.cursor.execute('UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?', (amount, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating total earned: {e}")
            return False

    # === РЕФЕРАЛЫ ===
    def increment_ref_count(self, user_id):
        try:
            self.cursor.execute('UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error incrementing ref count: {e}")
            return False

    def get_actual_referrals(self, user_id):
        try:
            self.cursor.execute('SELECT user_id, username, registered_at, balance FROM users WHERE invited_by = ?', (user_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting actual referrals: {e}")
            return []

    def get_actual_ref_count(self, user_id):
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE invited_by = ?', (user_id,))
            return self.cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting actual ref count: {e}")
            return 0

    def fix_ref_count(self, user_id):
        try:
            actual_count = self.get_actual_ref_count(user_id)
            self.cursor.execute('UPDATE users SET ref_count = ? WHERE user_id = ?', (actual_count, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error fixing ref count: {e}")
            return False

    def is_referral_blocked(self, referrer_id, referral_id):
        try:
            self.cursor.execute('SELECT COUNT(*) FROM blocked_referrals WHERE referrer_id = ? AND referral_id = ?', (referrer_id, referral_id))
            return self.cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error(f"Error checking blocked referral: {e}")
            return False

    def block_referral(self, referrer_id, referral_id):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO blocked_referrals (referrer_id, referral_id, blocked_at)
                VALUES (?, ?, ?)
            ''', (referrer_id, referral_id, self.format_moscow_time()))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error blocking referral: {e}")
            return False

    def unlink_referral(self, referral_user_id):
        try:
            self.cursor.execute('SELECT invited_by FROM users WHERE user_id = ?', (referral_user_id,))
            row = self.cursor.fetchone()
            if not row or not row[0]:
                return False
            old_inviter = row[0]
            self.block_referral(old_inviter, referral_user_id)
            self.cursor.execute('UPDATE users SET invited_by = NULL WHERE user_id = ?', (referral_user_id,))
            self.fix_ref_count(old_inviter)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error unlinking referral: {e}")
            return False

    # === ВЫВОД СРЕДСТВ ===
    def create_withdrawal_request(self, user_id, amount, bank_details):
        try:
            user_data = self.get_user(user_id)
            username = user_data[1] if user_data else None
            created_at_str = self.format_moscow_time()
            self.cursor.execute('''
                INSERT INTO withdrawals (user_id, amount, bank_details, username, created_at) 
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, bank_details, username, created_at_str))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating withdrawal: {e}")
            return None

    def get_pending_withdrawals(self):
        try:
            self.cursor.execute('''
                SELECT w.*, u.username 
                FROM withdrawals w 
                LEFT JOIN users u ON w.user_id = u.user_id 
                WHERE w.status = "pending" 
                ORDER BY w.created_at ASC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting pending withdrawals: {e}")
            return []

    def get_withdrawal(self, withdrawal_id):
        try:
            self.cursor.execute('SELECT * FROM withdrawals WHERE withdrawal_id = ?', (withdrawal_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting withdrawal: {e}")
            return None

    def update_withdrawal_status(self, withdrawal_id, status):
        try:
            processed_at = self.format_moscow_time() if status in ['approved', 'rejected'] else None
            self.cursor.execute('UPDATE withdrawals SET status = ?, processed_at = ? WHERE withdrawal_id = ?', (status, processed_at, withdrawal_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating withdrawal status: {e}")
            return False

    def get_user_stats(self, user_id):
        try:
            self.cursor.execute('SELECT COUNT(*) FROM user_tasks WHERE user_id = ? AND status = "approved"', (user_id,))
            completed = self.cursor.fetchone()[0]
            self.cursor.execute('SELECT COUNT(*) FROM user_tasks WHERE user_id = ? AND status = "rejected"', (user_id,))
            rejected = self.cursor.fetchone()[0]
            self.cursor.execute('SELECT COUNT(*) FROM user_tasks WHERE user_id = ? AND status = "assigned"', (user_id,))
            active = self.cursor.fetchone()[0]
            self.cursor.execute('SELECT COALESCE(SUM(t.price), 0) FROM user_tasks ut JOIN tasks t ON ut.task_id = t.task_id WHERE ut.user_id = ? AND ut.status = "approved"', (user_id,))
            total_earned = self.cursor.fetchone()[0]
            return {
                'completed_tasks': completed,
                'rejected_tasks': rejected,
                'active_tasks': active,
                'total_earned_from_tasks': total_earned
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                'completed_tasks': 0,
                'rejected_tasks': 0,
                'active_tasks': 0,
                'total_earned_from_tasks': 0.0
            }

    def close(self):
        try:
            self.conn.close()
        except Exception as e:
            logger.error(f"Error closing database: {e}")