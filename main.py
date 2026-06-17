import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from psycopg2 import Error, IntegrityError

# =====================================================
# КОНФИГУРАЦИЯ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ
# =====================================================
DB_CONFIG = {
    "host": "localhost",
    "database": "zoo",
    "user": "postgres",
    "password": "30112006"
}


# =====================================================
# КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
# =====================================================
class Database:
    def __init__(self, config):
        self.config = config

    def _get_connection(self):
        try:
            conn = psycopg2.connect(**self.config)
            conn.autocommit = False
            return conn
        except Error as e:
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к базе данных:\n{e}")
            return None

    def fetch_all(self, query, params=()):
        conn = self._get_connection()
        if not conn:
            return [], []
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description is None:
                    conn.commit()
                    return [], []
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                conn.commit()
                return columns, rows
        except Error as e:
            conn.rollback()
            messagebox.showerror("Ошибка выполнения", str(e))
            return [], []
        finally:
            conn.close()

    def execute(self, query, params=()):
        conn = self._get_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return True
        except IntegrityError as e:
            conn.rollback()
            if "foreign key" in str(e).lower() or "violates" in str(e).lower():
                messagebox.showwarning("Ошибка удаления",
                                       "Невозможно выполнить действие: запись используется в других таблицах.")
            else:
                messagebox.showerror("Ошибка записи", str(e))
            return False
        except Error as e:
            conn.rollback()
            messagebox.showerror("Ошибка записи", str(e))
            return False
        finally:
            conn.close()

    def get_options(self, query, display_format):
        conn = self._get_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                return [(row[0], display_format.format(*row[1:])) for row in cur.fetchall()]
        except Error:
            return []
        finally:
            conn.close()


# =====================================================
# КЛАСС ДЛЯ ТАБЛИЦЫ С ДЕЙСТВИЯМИ
# =====================================================
class ActionTable:
    def __init__(self, parent, columns, edit_callback, delete_callback):
        self.parent = parent
        self.display_columns = columns
        self.columns = list(columns) + ["Действия"]
        self.edit_callback = edit_callback
        self.delete_callback = delete_callback
        self.data = []
        self.sort_column = None
        self.sort_reverse = False

        container = tk.Frame(parent, bg='#f5f5f5')
        container.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.configure("Custom.Treeview", font=('Inter', 10), rowheight=32, borderwidth=0)
        style.configure("Custom.Treeview.Heading", font=('Inter', 10, 'bold'), relief='flat')

        self.tree = ttk.Treeview(container, columns=self.columns, show="headings",
                                 height=18, style="Custom.Treeview")

        col_widths = {
            "РК": 60, "Номер вольера": 100, "Тип": 100, "Климат. зона": 120,
            "Отапливаемый": 100, "Зоопарк": 150, "ФИО": 180, "Категория": 120,
            "Зарплата": 90, "Возраст": 70, "Дата приёма": 110, "Кличка": 120,
            "Вид": 120, "Дата поступления": 110, "Вольер": 100,
            "Возрастная группа": 140, "Количество особей": 100,
            "Вид корма": 120, "Тип корма": 110, "Объём на складе": 110,
            "Компания": 150, "Адрес": 180, "Специализация": 130,
            "Дата": 100, "Время": 90, "Объём порции": 100,
            "Животное": 120, "Корм": 120, "Сотрудник": 180,
            "Доступ к вольерам": 180, "Задачи": 200,
            "Диагноз": 150, "Дата начала": 110, "Дата окончания": 110,
            "Изолирован": 100, "Действия": 100,
            "РК_вольера": 80, "РК_сотрудника": 80, "РК_поставщика": 80,
            "РК_зоопарка": 80, "РК_корма": 80, "РК_лечения": 80,
            "РК_животного": 80
        }

        for col in self.columns:
            self.tree.heading(col, text=col)
            width = col_widths.get(col, 120)
            if col == "Действия":
                self.tree.column(col, width=width, anchor="center", stretch=False)
            elif col in ["РК", "Зарплата", "Возраст", "Количество особей", "Объём порции", "Объём на складе"]:
                self.tree.column(col, width=width, anchor="center")
            elif col in ["Дата", "Дата приёма", "Дата поступления", "Дата начала", "Дата окончания", "Время"]:
                self.tree.column(col, width=width, anchor="center")
            elif col in ["Отапливаемый", "Изолирован", "Тип", "Тип корма", "Категория"]:
                self.tree.column(col, width=width, anchor="center")
            else:
                self.tree.column(col, width=width, anchor="w")

        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure('odd', background='#fafafa')
        self.tree.tag_configure('even', background='#ffffff')
        self.tree.bind('<ButtonRelease-1>', self._on_click)

    def _on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == f"#{len(self.columns)}":
                item = self.tree.identify_row(event.y)
                if item:
                    values = self.tree.item(item, 'values')
                    if values and len(values) > 0:
                        row_id = values[0]
                        bbox = self.tree.bbox(item, column)
                        if bbox:
                            x_in_cell = event.x - bbox[0]
                            if x_in_cell < 50:
                                self.edit_callback(row_id)
                            else:
                                self.delete_callback(row_id)

    def _sort_by_column(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False

        if self.data:
            col_index = self.display_columns.index(col)
            try:
                self.data.sort(key=lambda x: float(x[col_index]) if x[col_index] and str(x[col_index]).replace('.', '').replace('-', '').isdigit() else 0,
                               reverse=self.sort_reverse)
            except:
                self.data.sort(key=lambda x: str(x[col_index]).lower() if x[col_index] else "",
                               reverse=self.sort_reverse)
            self._refresh_display()

    def _refresh_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, row in enumerate(self.data):
            tag = 'odd' if i % 2 == 0 else 'even'
            values = list(row) + ["✏️  🗑️"]
            self.tree.insert("", tk.END, values=values, tags=(tag,))

    def refresh(self, data):
        self.data = data
        self._refresh_display()


# =====================================================
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# =====================================================
class ZooApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Зоопарк")
        self.root.geometry("1600x900")
        self.root.configure(bg='#f5f5f5')

        self.db = Database(DB_CONFIG)
        self.current_frame = None
        self.nav_btns = []

        self._setup_layout()
        self._load_home()

    def _setup_layout(self):
        self.sidebar = tk.Frame(self.root, bg='#ffffff', width=260, relief='flat')
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        self.sidebar.pack_propagate(False)

        logo_frame = tk.Frame(self.sidebar, bg='#ffffff')
        logo_frame.pack(fill=tk.X, pady=(20, 15))
        tk.Label(logo_frame, text="🐘", font=('Inter', 32), bg='#ffffff').pack()
        tk.Label(logo_frame, text="Зоопарк", font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack()

        tk.Frame(self.sidebar, height=1, bg='#eeeeee').pack(fill=tk.X, padx=20, pady=10)

        # Основные таблицы
        main_tables = [
            ("🏠 Главная", self._load_home),
            ("🏚 Вольеры", self._load_voliers),
            ("👨‍💼 Сотрудники", self._load_employees),
            ("🦁 Животные", self._load_animals),
            ("👶 Потомство", self._load_offspring),
            ("🍖 Корма", self._load_feeds),
            ("🏢 Поставщики", self._load_suppliers),
            ("📋 Меню на день", self._load_menu),
        ]

        # Связующие таблицы
        link_tables = [
            ("🔗 Вольер_Сотрудник", self._load_volier_employee),
            ("🔗 Поставщик_Зоопарк", self._load_supplier_zoo),
            ("🔗 Корм_Поставщик", self._load_feed_supplier),
            ("🔗 Животное_Лечение", self._load_animal_treatment),
            ("🔗 Лечение_Сотрудник", self._load_treatment_employee),
        ]

        # Остальные разделы
        other_sections = [
            ("🎓 Проф. направленность", self._load_prof_dir),
            ("🏥 Лечение", self._load_treatments),
            ("📊 Запросы", self._load_queries),
            ("💻 SQL Консоль", self._load_sql_console)
        ]

        # Создаём кнопки с разделителями
        for text, cmd in main_tables:
            self._create_nav_button(text, cmd)

        tk.Label(self.sidebar, text="—— Связующие таблицы ——", font=('Inter', 9),
                 bg='#ffffff', fg='#888888').pack(pady=(10, 5))

        for text, cmd in link_tables:
            self._create_nav_button(text, cmd)

        tk.Label(self.sidebar, text="—— Дополнительно ——", font=('Inter', 9),
                 bg='#ffffff', fg='#888888').pack(pady=(10, 5))

        for text, cmd in other_sections:
            self._create_nav_button(text, cmd)

        self.content_area = tk.Frame(self.root, bg='#f5f5f5')
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.status_bar = tk.Label(self.root, text="Готов к работе", font=('Inter', 9),
                                   bg='#f5f5f5', fg='#aaaaaa', anchor='w')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)

    def _create_nav_button(self, text, cmd):
        btn = tk.Button(self.sidebar, text=text, command=cmd,
                       font=('Inter', 10), anchor='w', padx=20, pady=8,
                       bg='#ffffff', fg='#555555', relief='flat',
                       activebackground='#f0f0f0', activeforeground='#2c3e50',
                       cursor='hand2', bd=0)
        btn.pack(fill=tk.X)
        self.nav_btns.append(btn)

    def _clear_content(self, active_btn_idx=None):
        if self.current_frame:
            self.current_frame.destroy()

        self.current_frame = tk.Frame(self.content_area, bg='#f5f5f5')
        self.current_frame.pack(fill=tk.BOTH, expand=True)

        for i, btn in enumerate(self.nav_btns):
            btn.config(bg='#ffffff', fg='#555555')
            if active_btn_idx is not None and i == active_btn_idx:
                btn.config(bg='#f0f0f0', fg='#2c3e50')

    def _set_status(self, msg):
        self.status_bar.config(text=msg)
        self.root.update_idletasks()

    def _create_header(self, title, btn_text, btn_command):
        header = tk.Frame(self.current_frame, bg='#f5f5f5')
        header.pack(fill=tk.X, pady=(0, 20))

        tk.Label(header, text=title, font=('Inter', 24, 'bold'),
                 bg='#f5f5f5', fg='#2c3e50').pack(side=tk.LEFT)

        btn_frame = tk.Frame(header, bg='#f5f5f5')
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text=f"+ {btn_text}", command=btn_command,
                  bg='#ffffff', fg='#2c3e50', font=('Inter', 10, 'bold'),
                  padx=20, pady=8, relief='flat', cursor='hand2',
                  activebackground='#f0f0f0', bd=1, highlightthickness=1,
                  highlightcolor='#dddddd', highlightbackground='#dddddd').pack(side=tk.LEFT)

        return header

    def _create_modal_window(self, title, width, height):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry(f"{width}x{height}")
        win.configure(bg='#ffffff')
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        return win

    # =====================================================
    # ГЛАВНАЯ СТРАНИЦА
    # =====================================================
    def _load_home(self):
        self._clear_content(0)
        self._set_status("Загрузка главной страницы...")

        welcome_frame = tk.Frame(self.current_frame, bg='#ffffff', relief='flat', bd=1,
                                highlightthickness=1, highlightcolor='#eeeeee', highlightbackground='#eeeeee')
        welcome_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(welcome_frame, text="🐘", font=('Inter', 48), bg='#ffffff').pack(pady=(30, 10))
        tk.Label(welcome_frame, text="Добро пожаловать!", font=('Inter', 24, 'bold'),
                 bg='#ffffff', fg='#2c3e50').pack()
        tk.Label(welcome_frame, text="Система управления зоопарком",
                 font=('Inter', 12), bg='#ffffff', fg='#888888').pack(pady=(5, 30))

        stats_frame = tk.Frame(self.current_frame, bg='#f5f5f5')
        stats_frame.pack(fill=tk.X)

        stats_data = [
            ("🏚", "Вольеров", "SELECT COUNT(*) FROM Вольер"),
            ("🦁", "Животных", "SELECT COUNT(*) FROM Животное"),
            ("👨‍💼", "Сотрудников", "SELECT COUNT(*) FROM Сотрудник"),
            ("🏢", "Поставщиков", "SELECT COUNT(*) FROM Поставщик_кормов"),
            ("🔗", "Связующих записей", "SELECT (SELECT COUNT(*) FROM Вольер_Сотрудник) + (SELECT COUNT(*) FROM Поставщик_кормов_Зоопарк) + (SELECT COUNT(*) FROM Корм_Поставщик_кормов) + (SELECT COUNT(*) FROM Животное_Лечение) + (SELECT COUNT(*) FROM Лечение_Сотрудник)")
        ]

        for i, (icon, title_text, query) in enumerate(stats_data):
            _, rows = self.db.fetch_all(query)
            count = rows[0][0] if rows else 0

            card = tk.Frame(stats_frame, bg='#ffffff', relief='flat', bd=1,
                           highlightthickness=1, highlightcolor='#eeeeee', highlightbackground='#eeeeee')
            card.grid(row=0, column=i, padx=10, sticky='nsew')
            card.grid_propagate(False)
            card.configure(width=200, height=120)

            tk.Label(card, text=icon, font=('Inter', 28), bg='#ffffff').pack(pady=(15, 5))
            tk.Label(card, text=str(count), font=('Inter', 28, 'bold'), bg='#ffffff', fg='#2c3e50').pack()
            tk.Label(card, text=title_text, font=('Inter', 11), bg='#ffffff', fg='#888888').pack()

        for i in range(5):
            stats_frame.columnconfigure(i, weight=1)

        self._set_status("Главная страница загружена")

    # =====================================================
    # ВОЛЬЕРЫ
    # =====================================================
    def _load_voliers(self):
        self._clear_content(1)
        self._set_status("Загрузка вольеров...")

        self._create_header("Вольеры", "Добавить вольер", self._add_volier)
        columns = ["РК", "Номер вольера", "Тип", "Климат. зона", "Отапливаемый", "Зоопарк"]

        self.volier_table = ActionTable(self.current_frame, columns, self._edit_volier, self._delete_volier)
        self._refresh_voliers()

    def _refresh_voliers(self):
        _, rows = self.db.fetch_all("""
            SELECT В.РК, В.Номер_вольера, В.Тип, В.Климатическая_зона,
                   CASE WHEN В.Отапливаемый THEN 'Да' ELSE 'Нет' END, З.Название
            FROM Вольер В
            LEFT JOIN Зоопарк З ON В.РК_зоопарка = З.РК
            ORDER BY В.РК
        """)
        self.volier_table.refresh(rows)

    def _add_volier(self):
        self._volier_form("Добавление вольера")

    def _edit_volier(self, rid):
        _, rows = self.db.fetch_all("SELECT Номер_вольера, Тип, Климатическая_зона, Отапливаемый, РК_зоопарка FROM Вольер WHERE РК = %s", (rid,))
        if rows:
            self._volier_form("Редактирование вольера", rid, rows[0])

    def _delete_volier(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить вольер ID: {rid}?"):
            if self.db.execute("DELETE FROM Вольер WHERE РК = %s", (rid,)):
                self._refresh_voliers()
                self._set_status(f"Вольер {rid} удалён")

    def _volier_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 450)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        fields = {}
        labels = ["Номер вольера:", "Тип:", "Климатическая зона:"]

        for i, label in enumerate(labels):
            tk.Label(win, text=label, font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
            entry = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
            entry.pack(padx=20, pady=(0, 10))
            if data and i < len(data):
                entry.insert(0, str(data[i]) if data[i] is not None else "")
            fields[label] = entry

        tk.Label(win, text="Отапливаемый:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        heating_var = tk.BooleanVar()
        if data and len(data) > 3 and data[3]:
            heating_var.set(data[3] in (True, 1, 't'))
        tk.Checkbutton(win, text="Да", variable=heating_var, bg='#ffffff', font=('Inter', 11)).pack(anchor='w', padx=20, pady=(0, 10))

        tk.Label(win, text="Зоопарк:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        zoos = self.db.get_options("SELECT РК, Название FROM Зоопарк", "{}")
        zoo_combo = ttk.Combobox(win, values=[f"{z[0]} - {z[1]}" for z in zoos], state="readonly", width=35)
        zoo_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 4:
            for z in zoos:
                if z[0] == data[4]:
                    zoo_combo.set(f"{z[0]} - {z[1]}")
                    break

        def save():
            try:
                values = (
                    fields["Номер вольера:"].get().strip(),
                    fields["Тип:"].get().strip(),
                    fields["Климатическая зона:"].get().strip(),
                    heating_var.get(),
                    int(zoo_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("""
                        UPDATE Вольер SET Номер_вольера=%s, Тип=%s, Климатическая_зона=%s,
                        Отапливаемый=%s, РК_зоопарка=%s WHERE РК=%s
                    """, (*values, rid))
                else:
                    self.db.execute("""
                        INSERT INTO Вольер (Номер_вольера, Тип, Климатическая_зона, Отапливаемый, РК_зоопарка)
                        VALUES (%s, %s, %s, %s, %s)
                    """, values)
                win.destroy()
                self._refresh_voliers()
                self._set_status("Вольер сохранён")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # СОТРУДНИКИ
    # =====================================================
    def _load_employees(self):
        self._clear_content(2)
        self._set_status("Загрузка сотрудников...")

        self._create_header("Сотрудники", "Добавить сотрудника", self._add_employee)
        columns = ["РК", "ФИО", "Категория", "Зарплата", "Возраст", "Дата приёма", "Зоопарк"]

        self.emp_table = ActionTable(self.current_frame, columns, self._edit_employee, self._delete_employee)
        self._refresh_employees()

    def _refresh_employees(self):
        _, rows = self.db.fetch_all("""
            SELECT С.РК, С.ФИО, С.Категория, С.Зарплата, С.Возраст,
                   TO_CHAR(С.Дата_попадания_в_зоопарк, 'DD.MM.YYYY'), З.Название
            FROM Сотрудник С
            LEFT JOIN Зоопарк З ON С.РК_зоопарка = З.РК
            ORDER BY С.РК
        """)
        self.emp_table.refresh(rows)

    def _add_employee(self):
        self._employee_form("Добавление сотрудника")

    def _edit_employee(self, rid):
        _, rows = self.db.fetch_all("""
            SELECT ФИО, Категория, Зарплата, Возраст, Дата_попадания_в_зоопарк, РК_зоопарка
            FROM Сотрудник WHERE РК = %s
        """, (rid,))
        if rows:
            self._employee_form("Редактирование сотрудника", rid, rows[0])

    def _delete_employee(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить сотрудника ID: {rid}?"):
            if self.db.execute("DELETE FROM Сотрудник WHERE РК = %s", (rid,)):
                self._refresh_employees()
                self._set_status(f"Сотрудник {rid} удалён")

    def _employee_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 500)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        fields = {}
        labels = ["ФИО:", "Категория:", "Зарплата:", "Возраст:", "Дата приёма (ГГГГ-ММ-ДД):"]

        for i, label in enumerate(labels):
            tk.Label(win, text=label, font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
            entry = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
            entry.pack(padx=20, pady=(0, 10))
            if data and i < len(data):
                entry.insert(0, str(data[i]) if data[i] is not None else "")
            fields[label] = entry

        tk.Label(win, text="Зоопарк:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        zoos = self.db.get_options("SELECT РК, Название FROM Зоопарк", "{}")
        zoo_combo = ttk.Combobox(win, values=[f"{z[0]} - {z[1]}" for z in zoos], state="readonly", width=35)
        zoo_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 5:
            for z in zoos:
                if z[0] == data[5]:
                    zoo_combo.set(f"{z[0]} - {z[1]}")
                    break

        def save():
            try:
                values = (
                    fields["ФИО:"].get().strip(),
                    fields["Категория:"].get().strip(),
                    float(fields["Зарплата:"].get()),
                    int(fields["Возраст:"].get()),
                    fields["Дата приёма (ГГГГ-ММ-ДД):"].get().strip(),
                    int(zoo_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("""
                        UPDATE Сотрудник SET ФИО=%s, Категория=%s, Зарплата=%s,
                        Возраст=%s, Дата_попадания_в_зоопарк=%s, РК_зоопарка=%s
                        WHERE РК=%s
                    """, (*values, rid))
                else:
                    self.db.execute("""
                        INSERT INTO Сотрудник (ФИО, Категория, Зарплата, Возраст, Дата_попадания_в_зоопарк, РК_зоопарка)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, values)
                win.destroy()
                self._refresh_employees()
                self._set_status("Сотрудник сохранён")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # ЖИВОТНЫЕ
    # =====================================================
    def _load_animals(self):
        self._clear_content(3)
        self._set_status("Загрузка животных...")

        self._create_header("Животные", "Добавить животное", self._add_animal)
        columns = ["РК", "Кличка", "Вид", "Тип", "Дата поступления", "Вольер"]

        self.animal_table = ActionTable(self.current_frame, columns, self._edit_animal, self._delete_animal)
        self._refresh_animals()

    def _refresh_animals(self):
        _, rows = self.db.fetch_all("""
            SELECT Ж.РК, Ж.Кличка, Ж.Вид, Ж.Тип,
                   TO_CHAR(Ж.Дата_попадания_в_зоопарк, 'DD.MM.YYYY'), В.Номер_вольера
            FROM Животное Ж
            LEFT JOIN Вольер В ON Ж.РК_вольера = В.РК
            ORDER BY Ж.РК
        """)
        self.animal_table.refresh(rows)

    def _add_animal(self):
        self._animal_form("Добавление животного")

    def _edit_animal(self, rid):
        _, rows = self.db.fetch_all("""
            SELECT Кличка, Вид, Тип, Дата_попадания_в_зоопарк, РК_вольера
            FROM Животное WHERE РК = %s
        """, (rid,))
        if rows:
            self._animal_form("Редактирование животного", rid, rows[0])

    def _delete_animal(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить животное ID: {rid}?"):
            if self.db.execute("DELETE FROM Животное WHERE РК = %s", (rid,)):
                self._refresh_animals()
                self._set_status(f"Животное {rid} удалено")

    def _animal_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 450)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        fields = {}
        labels = ["Кличка:", "Вид:", "Тип (Хищник/Травоядное):", "Дата поступления (ГГГГ-ММ-ДД):"]

        for i, label in enumerate(labels):
            tk.Label(win, text=label, font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
            entry = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
            entry.pack(padx=20, pady=(0, 10))
            if data and i < len(data):
                entry.insert(0, str(data[i]) if data[i] is not None else "")
            fields[label] = entry

        tk.Label(win, text="Вольер:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        voliers = self.db.get_options("SELECT РК, Номер_вольера FROM Вольер", "{}")
        volier_combo = ttk.Combobox(win, values=[f"{v[0]} - {v[1]}" for v in voliers], state="readonly", width=35)
        volier_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 4:
            for v in voliers:
                if v[0] == data[4]:
                    volier_combo.set(f"{v[0]} - {v[1]}")
                    break

        def save():
            try:
                values = (
                    fields["Кличка:"].get().strip(),
                    fields["Вид:"].get().strip(),
                    fields["Тип (Хищник/Травоядное):"].get().strip(),
                    fields["Дата поступления (ГГГГ-ММ-ДД):"].get().strip(),
                    int(volier_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("""
                        UPDATE Животное SET Кличка=%s, Вид=%s, Тип=%s,
                        Дата_попадания_в_зоопарк=%s, РК_вольера=%s WHERE РК=%s
                    """, (*values, rid))
                else:
                    self.db.execute("""
                        INSERT INTO Животное (Кличка, Вид, Тип, Дата_попадания_в_зоопарк, РК_вольера)
                        VALUES (%s, %s, %s, %s, %s)
                    """, values)
                win.destroy()
                self._refresh_animals()
                self._set_status("Животное сохранено")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # ПОТОМСТВО
    # =====================================================
    def _load_offspring(self):
        self._clear_content(4)
        self._set_status("Загрузка потомства...")

        self._create_header("Потомство", "Добавить запись", self._add_offspring)
        columns = ["РК", "Возраст", "Количество особей", "Вольер"]

        self.offspring_table = ActionTable(self.current_frame, columns, self._edit_offspring, self._delete_offspring)
        self._refresh_offspring()

    def _refresh_offspring(self):
        _, rows = self.db.fetch_all("""
            SELECT П.РК, П.Возраст, П.Количество_особей, В.Номер_вольера
            FROM Потомство П
            LEFT JOIN Вольер В ON П.РК_вольера = В.РК
            ORDER BY П.РК
        """)
        self.offspring_table.refresh(rows)

    def _add_offspring(self):
        self._offspring_form("Добавление потомства")

    def _edit_offspring(self, rid):
        _, rows = self.db.fetch_all("SELECT Возраст, Количество_особей, РК_вольера FROM Потомство WHERE РК = %s", (rid,))
        if rows:
            self._offspring_form("Редактирование потомства", rid, rows[0])

    def _delete_offspring(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить запись ID: {rid}?"):
            if self.db.execute("DELETE FROM Потомство WHERE РК = %s", (rid,)):
                self._refresh_offspring()
                self._set_status(f"Запись {rid} удалена")

    def _offspring_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 350)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Возрастная группа:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_age = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_age.pack(padx=20, pady=(0, 10))
        if data:
            entry_age.insert(0, str(data[0]) if data[0] else "")

        tk.Label(win, text="Количество особей:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_count = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_count.pack(padx=20, pady=(0, 10))
        if data:
            entry_count.insert(0, str(data[1]) if data[1] else "")

        tk.Label(win, text="Вольер:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        voliers = self.db.get_options("SELECT РК, Номер_вольера FROM Вольер", "{}")
        volier_combo = ttk.Combobox(win, values=[f"{v[0]} - {v[1]}" for v in voliers], state="readonly", width=35)
        volier_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 2:
            for v in voliers:
                if v[0] == data[2]:
                    volier_combo.set(f"{v[0]} - {v[1]}")
                    break

        def save():
            try:
                values = (
                    entry_age.get().strip(),
                    int(entry_count.get().strip()),
                    int(volier_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("UPDATE Потомство SET Возраст=%s, Количество_особей=%s, РК_вольера=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Потомство (Возраст, Количество_особей, РК_вольера) VALUES (%s, %s, %s)", values)
                win.destroy()
                self._refresh_offspring()
                self._set_status("Запись сохранена")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # КОРМА
    # =====================================================
    def _load_feeds(self):
        self._clear_content(5)
        self._set_status("Загрузка кормов...")

        self._create_header("Корма", "Добавить корм", self._add_feed)
        columns = ["РК", "Вид", "Тип корма", "Объём на складе"]

        self.feed_table = ActionTable(self.current_frame, columns, self._edit_feed, self._delete_feed)
        self._refresh_feeds()

    def _refresh_feeds(self):
        _, rows = self.db.fetch_all("SELECT РК, Вид, Тип_корма, Объем_на_складе FROM Корм ORDER BY РК")
        self.feed_table.refresh(rows)

    def _add_feed(self):
        self._feed_form("Добавление корма")

    def _edit_feed(self, rid):
        _, rows = self.db.fetch_all("SELECT Вид, Тип_корма, Объем_на_складе FROM Корм WHERE РК = %s", (rid,))
        if rows:
            self._feed_form("Редактирование корма", rid, rows[0])

    def _delete_feed(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить корм ID: {rid}?"):
            if self.db.execute("DELETE FROM Корм WHERE РК = %s", (rid,)):
                self._refresh_feeds()
                self._set_status(f"Корм {rid} удалён")

    def _feed_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 350)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Вид корма:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_name = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_name.pack(padx=20, pady=(0, 10))
        if data:
            entry_name.insert(0, str(data[0]) if data[0] else "")

        tk.Label(win, text="Тип корма:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        type_combo = ttk.Combobox(win, values=["Растительный", "Живой", "Мясо", "Комбикорм"], state="readonly", width=37)
        type_combo.pack(padx=20, pady=(0, 10))
        if data and data[1]:
            type_combo.set(data[1])

        tk.Label(win, text="Объём на складе (кг):", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_volume = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_volume.pack(padx=20, pady=(0, 20))
        if data and data[2]:
            entry_volume.insert(0, str(data[2]))

        def save():
            try:
                values = (
                    entry_name.get().strip(),
                    type_combo.get(),
                    float(entry_volume.get().strip())
                )
                if rid:
                    self.db.execute("UPDATE Корм SET Вид=%s, Тип_корма=%s, Объем_на_складе=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Корм (Вид, Тип_корма, Объем_на_складе) VALUES (%s, %s, %s)", values)
                win.destroy()
                self._refresh_feeds()
                self._set_status("Корм сохранён")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # ПОСТАВЩИКИ
    # =====================================================
    def _load_suppliers(self):
        self._clear_content(6)
        self._set_status("Загрузка поставщиков...")

        self._create_header("Поставщики кормов", "Добавить поставщика", self._add_supplier)
        columns = ["РК", "Компания", "Адрес", "Специализация"]

        self.supplier_table = ActionTable(self.current_frame, columns, self._edit_supplier, self._delete_supplier)
        self._refresh_suppliers()

    def _refresh_suppliers(self):
        _, rows = self.db.fetch_all("SELECT РК, Компания, Адрес, Специализация FROM Поставщик_кормов ORDER BY РК")
        self.supplier_table.refresh(rows)

    def _add_supplier(self):
        self._supplier_form("Добавление поставщика")

    def _edit_supplier(self, rid):
        _, rows = self.db.fetch_all("SELECT Компания, Адрес, Специализация FROM Поставщик_кормов WHERE РК = %s", (rid,))
        if rows:
            self._supplier_form("Редактирование поставщика", rid, rows[0])

    def _delete_supplier(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить поставщика ID: {rid}?"):
            if self.db.execute("DELETE FROM Поставщик_кормов WHERE РК = %s", (rid,)):
                self._refresh_suppliers()
                self._set_status(f"Поставщик {rid} удалён")

    def _supplier_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 400)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Компания:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_company = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_company.pack(padx=20, pady=(0, 10))
        if data:
            entry_company.insert(0, str(data[0]) if data[0] else "")

        tk.Label(win, text="Адрес:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_address = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_address.pack(padx=20, pady=(0, 10))
        if data:
            entry_address.insert(0, str(data[1]) if data[1] else "")

        tk.Label(win, text="Специализация:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_spec = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_spec.pack(padx=20, pady=(0, 20))
        if data:
            entry_spec.insert(0, str(data[2]) if data[2] else "")

        def save():
            try:
                values = (
                    entry_company.get().strip(),
                    entry_address.get().strip(),
                    entry_spec.get().strip()
                )
                if rid:
                    self.db.execute("UPDATE Поставщик_кормов SET Компания=%s, Адрес=%s, Специализация=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Поставщик_кормов (Компания, Адрес, Специализация) VALUES (%s, %s, %s)", values)
                win.destroy()
                self._refresh_suppliers()
                self._set_status("Поставщик сохранён")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # МЕНЮ НА ДЕНЬ
    # =====================================================
    def _load_menu(self):
        self._clear_content(7)
        self._set_status("Загрузка меню на день...")

        self._create_header("Меню на день", "Добавить запись", self._add_menu)
        columns = ["РК", "Дата", "Время", "Объём порции", "Животное", "Корм"]

        self.menu_table = ActionTable(self.current_frame, columns, self._edit_menu, self._delete_menu)
        self._refresh_menu()

    def _refresh_menu(self):
        _, rows = self.db.fetch_all("""
            SELECT М.РК, М.Дата, М.Время, М.Объем_порции, Ж.Кличка, К.Вид
            FROM Меню_на_день М
            LEFT JOIN Животное Ж ON М.РК_животного = Ж.РК
            LEFT JOIN Корм К ON М.РК_корма = К.РК
            ORDER BY М.РК
        """)
        self.menu_table.refresh(rows)

    def _add_menu(self):
        self._menu_form("Добавление записи в меню")

    def _edit_menu(self, rid):
        _, rows = self.db.fetch_all("SELECT Дата, Время, Объем_порции, РК_животного, РК_корма FROM Меню_на_день WHERE РК = %s", (rid,))
        if rows:
            self._menu_form("Редактирование записи", rid, rows[0])

    def _delete_menu(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить запись ID: {rid}?"):
            if self.db.execute("DELETE FROM Меню_на_день WHERE РК = %s", (rid,)):
                self._refresh_menu()
                self._set_status(f"Запись {rid} удалена")

    def _menu_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 450)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Дата (ГГГГ-ММ-ДД):", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_date = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_date.pack(padx=20, pady=(0, 10))
        if data:
            entry_date.insert(0, str(data[0]) if data[0] else "")

        tk.Label(win, text="Время (ЧЧ:ММ:СС):", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_time = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_time.pack(padx=20, pady=(0, 10))
        if data:
            entry_time.insert(0, str(data[1]) if data[1] else "")

        tk.Label(win, text="Объём порции (кг):", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_volume = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_volume.pack(padx=20, pady=(0, 10))
        if data:
            entry_volume.insert(0, str(data[2]) if data[2] else "")

        tk.Label(win, text="Животное:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        animals = self.db.get_options("SELECT РК, Кличка FROM Животное", "{}")
        animal_combo = ttk.Combobox(win, values=[f"{a[0]} - {a[1]}" for a in animals], state="readonly", width=35)
        animal_combo.pack(padx=20, pady=(0, 10))
        if data and len(data) > 3:
            for a in animals:
                if a[0] == data[3]:
                    animal_combo.set(f"{a[0]} - {a[1]}")
                    break

        tk.Label(win, text="Корм:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        feeds = self.db.get_options("SELECT РК, Вид FROM Корм", "{}")
        feed_combo = ttk.Combobox(win, values=[f"{f[0]} - {f[1]}" for f in feeds], state="readonly", width=35)
        feed_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 4:
            for f in feeds:
                if f[0] == data[4]:
                    feed_combo.set(f"{f[0]} - {f[1]}")
                    break

        def save():
            try:
                values = (
                    entry_date.get().strip(),
                    entry_time.get().strip(),
                    float(entry_volume.get().strip()),
                    int(animal_combo.get().split(" - ")[0]),
                    int(feed_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("""
                        UPDATE Меню_на_день SET Дата=%s, Время=%s, Объем_порции=%s,
                        РК_животного=%s, РК_корма=%s WHERE РК=%s
                    """, (*values, rid))
                else:
                    self.db.execute("""
                        INSERT INTO Меню_на_день (Дата, Время, Объем_порции, РК_животного, РК_корма)
                        VALUES (%s, %s, %s, %s, %s)
                    """, values)
                win.destroy()
                self._refresh_menu()
                self._set_status("Запись сохранена")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # СВЯЗУЮЩАЯ ТАБЛИЦА: Вольер_Сотрудник
    # =====================================================
    def _load_volier_employee(self):
        self._clear_content(8)
        self._set_status("Загрузка связей Вольер-Сотрудник...")

        self._create_header("Вольер ⟷ Сотрудник", "Добавить связь", self._add_volier_employee)
        columns = ["РК", "РК вольера", "Номер вольера", "РК сотрудника", "ФИО сотрудника"]

        self.ve_table = ActionTable(self.current_frame, columns, self._edit_volier_employee, self._delete_volier_employee)
        self._refresh_volier_employee()

    def _refresh_volier_employee(self):
        _, rows = self.db.fetch_all("""
            SELECT ВС.РК, ВС.РК_вольера, В.Номер_вольера, ВС.РК_сотрудника, С.ФИО
            FROM Вольер_Сотрудник ВС
            LEFT JOIN Вольер В ON ВС.РК_вольера = В.РК
            LEFT JOIN Сотрудник С ON ВС.РК_сотрудника = С.РК
            ORDER BY ВС.РК
        """)
        self.ve_table.refresh(rows)

    def _add_volier_employee(self):
        self._volier_employee_form("Добавление связи")

    def _edit_volier_employee(self, rid):
        _, rows = self.db.fetch_all("SELECT РК_вольера, РК_сотрудника FROM Вольер_Сотрудник WHERE РК = %s", (rid,))
        if rows:
            self._volier_employee_form("Редактирование связи", rid, rows[0])

    def _delete_volier_employee(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить связь ID: {rid}?"):
            if self.db.execute("DELETE FROM Вольер_Сотрудник WHERE РК = %s", (rid,)):
                self._refresh_volier_employee()
                self._set_status(f"Связь {rid} удалена")

    def _volier_employee_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 300)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Вольер:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        voliers = self.db.get_options("SELECT РК, Номер_вольера FROM Вольер", "{}")
        volier_combo = ttk.Combobox(win, values=[f"{v[0]} - {v[1]}" for v in voliers], state="readonly", width=35)
        volier_combo.pack(padx=20, pady=(0, 10))
        if data:
            for v in voliers:
                if v[0] == data[0]:
                    volier_combo.set(f"{v[0]} - {v[1]}")
                    break

        tk.Label(win, text="Сотрудник:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        employees = self.db.get_options("SELECT РК, ФИО FROM Сотрудник", "{}")
        emp_combo = ttk.Combobox(win, values=[f"{e[0]} - {e[1]}" for e in employees], state="readonly", width=35)
        emp_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 1:
            for e in employees:
                if e[0] == data[1]:
                    emp_combo.set(f"{e[0]} - {e[1]}")
                    break

        def save():
            try:
                values = (
                    int(volier_combo.get().split(" - ")[0]),
                    int(emp_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("UPDATE Вольер_Сотрудник SET РК_вольера=%s, РК_сотрудника=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Вольер_Сотрудник (РК_вольера, РК_сотрудника) VALUES (%s, %s)", values)
                win.destroy()
                self._refresh_volier_employee()
                self._set_status("Связь сохранена")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # СВЯЗУЮЩАЯ ТАБЛИЦА: Поставщик_кормов_Зоопарк
    # =====================================================
    def _load_supplier_zoo(self):
        self._clear_content(9)
        self._set_status("Загрузка связей Поставщик-Зоопарк...")

        self._create_header("Поставщик ⟷ Зоопарк", "Добавить связь", self._add_supplier_zoo)
        columns = ["РК", "РК поставщика", "Компания", "РК зоопарка", "Зоопарк"]

        self.sz_table = ActionTable(self.current_frame, columns, self._edit_supplier_zoo, self._delete_supplier_zoo)
        self._refresh_supplier_zoo()

    def _refresh_supplier_zoo(self):
        _, rows = self.db.fetch_all("""
            SELECT ПЗ.РК, ПЗ.РК_поставщика, П.Компания, ПЗ.РК_зоопарка, З.Название
            FROM Поставщик_кормов_Зоопарк ПЗ
            LEFT JOIN Поставщик_кормов П ON ПЗ.РК_поставщика = П.РК
            LEFT JOIN Зоопарк З ON ПЗ.РК_зоопарка = З.РК
            ORDER BY ПЗ.РК
        """)
        self.sz_table.refresh(rows)

    def _add_supplier_zoo(self):
        self._supplier_zoo_form("Добавление связи")

    def _edit_supplier_zoo(self, rid):
        _, rows = self.db.fetch_all("SELECT РК_поставщика, РК_зоопарка FROM Поставщик_кормов_Зоопарк WHERE РК = %s", (rid,))
        if rows:
            self._supplier_zoo_form("Редактирование связи", rid, rows[0])

    def _delete_supplier_zoo(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить связь ID: {rid}?"):
            if self.db.execute("DELETE FROM Поставщик_кормов_Зоопарк WHERE РК = %s", (rid,)):
                self._refresh_supplier_zoo()
                self._set_status(f"Связь {rid} удалена")

    def _supplier_zoo_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 300)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Поставщик:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        suppliers = self.db.get_options("SELECT РК, Компания FROM Поставщик_кормов", "{}")
        sup_combo = ttk.Combobox(win, values=[f"{s[0]} - {s[1]}" for s in suppliers], state="readonly", width=35)
        sup_combo.pack(padx=20, pady=(0, 10))
        if data:
            for s in suppliers:
                if s[0] == data[0]:
                    sup_combo.set(f"{s[0]} - {s[1]}")
                    break

        tk.Label(win, text="Зоопарк:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        zoos = self.db.get_options("SELECT РК, Название FROM Зоопарк", "{}")
        zoo_combo = ttk.Combobox(win, values=[f"{z[0]} - {z[1]}" for z in zoos], state="readonly", width=35)
        zoo_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 1:
            for z in zoos:
                if z[0] == data[1]:
                    zoo_combo.set(f"{z[0]} - {z[1]}")
                    break

        def save():
            try:
                values = (
                    int(sup_combo.get().split(" - ")[0]),
                    int(zoo_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("UPDATE Поставщик_кормов_Зоопарк SET РК_поставщика=%s, РК_зоопарка=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Поставщик_кормов_Зоопарк (РК_поставщика, РК_зоопарка) VALUES (%s, %s)", values)
                win.destroy()
                self._refresh_supplier_zoo()
                self._set_status("Связь сохранена")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # СВЯЗУЮЩАЯ ТАБЛИЦА: Корм_Поставщик_кормов
    # =====================================================
    def _load_feed_supplier(self):
        self._clear_content(10)
        self._set_status("Загрузка связей Корм-Поставщик...")

        self._create_header("Корм ⟷ Поставщик", "Добавить связь", self._add_feed_supplier)
        columns = ["РК", "РК корма", "Вид корма", "РК поставщика", "Поставщик"]

        self.fs_table = ActionTable(self.current_frame, columns, self._edit_feed_supplier, self._delete_feed_supplier)
        self._refresh_feed_supplier()

    def _refresh_feed_supplier(self):
        _, rows = self.db.fetch_all("""
            SELECT КП.РК, КП.РК_корма, К.Вид, КП.РК_поставщика, П.Компания
            FROM Корм_Поставщик_кормов КП
            LEFT JOIN Корм К ON КП.РК_корма = К.РК
            LEFT JOIN Поставщик_кормов П ON КП.РК_поставщика = П.РК
            ORDER BY КП.РК
        """)
        self.fs_table.refresh(rows)

    def _add_feed_supplier(self):
        self._feed_supplier_form("Добавление связи")

    def _edit_feed_supplier(self, rid):
        _, rows = self.db.fetch_all("SELECT РК_корма, РК_поставщика FROM Корм_Поставщик_кормов WHERE РК = %s", (rid,))
        if rows:
            self._feed_supplier_form("Редактирование связи", rid, rows[0])

    def _delete_feed_supplier(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить связь ID: {rid}?"):
            if self.db.execute("DELETE FROM Корм_Поставщик_кормов WHERE РК = %s", (rid,)):
                self._refresh_feed_supplier()
                self._set_status(f"Связь {rid} удалена")

    def _feed_supplier_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 300)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Корм:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        feeds = self.db.get_options("SELECT РК, Вид FROM Корм", "{}")
        feed_combo = ttk.Combobox(win, values=[f"{f[0]} - {f[1]}" for f in feeds], state="readonly", width=35)
        feed_combo.pack(padx=20, pady=(0, 10))
        if data:
            for f in feeds:
                if f[0] == data[0]:
                    feed_combo.set(f"{f[0]} - {f[1]}")
                    break

        tk.Label(win, text="Поставщик:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        suppliers = self.db.get_options("SELECT РК, Компания FROM Поставщик_кормов", "{}")
        sup_combo = ttk.Combobox(win, values=[f"{s[0]} - {s[1]}" for s in suppliers], state="readonly", width=35)
        sup_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 1:
            for s in suppliers:
                if s[0] == data[1]:
                    sup_combo.set(f"{s[0]} - {s[1]}")
                    break

        def save():
            try:
                values = (
                    int(feed_combo.get().split(" - ")[0]),
                    int(sup_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("UPDATE Корм_Поставщик_кормов SET РК_корма=%s, РК_поставщика=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Корм_Поставщик_кормов (РК_корма, РК_поставщика) VALUES (%s, %s)", values)
                win.destroy()
                self._refresh_feed_supplier()
                self._set_status("Связь сохранена")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # СВЯЗУЮЩАЯ ТАБЛИЦА: Животное_Лечение
    # =====================================================
    def _load_animal_treatment(self):
        self._clear_content(11)
        self._set_status("Загрузка связей Животное-Лечение...")

        self._create_header("Животное ⟷ Лечение", "Добавить связь", self._add_animal_treatment)
        columns = ["РК", "РК животного", "Кличка", "РК лечения", "Диагноз"]

        self.at_table = ActionTable(self.current_frame, columns, self._edit_animal_treatment, self._delete_animal_treatment)
        self._refresh_animal_treatment()

    def _refresh_animal_treatment(self):
        _, rows = self.db.fetch_all("""
            SELECT ЖЛ.РК, ЖЛ.РК_животного, Ж.Кличка, ЖЛ.РК_лечения, Л.Диагноз
            FROM Животное_Лечение ЖЛ
            LEFT JOIN Животное Ж ON ЖЛ.РК_животного = Ж.РК
            LEFT JOIN Лечение Л ON ЖЛ.РК_лечения = Л.РК
            ORDER BY ЖЛ.РК
        """)
        self.at_table.refresh(rows)

    def _add_animal_treatment(self):
        self._animal_treatment_form("Добавление связи")

    def _edit_animal_treatment(self, rid):
        _, rows = self.db.fetch_all("SELECT РК_животного, РК_лечения FROM Животное_Лечение WHERE РК = %s", (rid,))
        if rows:
            self._animal_treatment_form("Редактирование связи", rid, rows[0])

    def _delete_animal_treatment(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить связь ID: {rid}?"):
            if self.db.execute("DELETE FROM Животное_Лечение WHERE РК = %s", (rid,)):
                self._refresh_animal_treatment()
                self._set_status(f"Связь {rid} удалена")

    def _animal_treatment_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 300)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Животное:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        animals = self.db.get_options("SELECT РК, Кличка FROM Животное", "{}")
        animal_combo = ttk.Combobox(win, values=[f"{a[0]} - {a[1]}" for a in animals], state="readonly", width=35)
        animal_combo.pack(padx=20, pady=(0, 10))
        if data:
            for a in animals:
                if a[0] == data[0]:
                    animal_combo.set(f"{a[0]} - {a[1]}")
                    break

        tk.Label(win, text="Лечение:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        treatments = self.db.get_options("SELECT РК, Диагноз FROM Лечение", "{}")
        treat_combo = ttk.Combobox(win, values=[f"{t[0]} - {t[1]}" for t in treatments], state="readonly", width=35)
        treat_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 1:
            for t in treatments:
                if t[0] == data[1]:
                    treat_combo.set(f"{t[0]} - {t[1]}")
                    break

        def save():
            try:
                values = (
                    int(animal_combo.get().split(" - ")[0]),
                    int(treat_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("UPDATE Животное_Лечение SET РК_животного=%s, РК_лечения=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Животное_Лечение (РК_животного, РК_лечения) VALUES (%s, %s)", values)
                win.destroy()
                self._refresh_animal_treatment()
                self._set_status("Связь сохранена")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # СВЯЗУЮЩАЯ ТАБЛИЦА: Лечение_Сотрудник
    # =====================================================
    def _load_treatment_employee(self):
        self._clear_content(12)
        self._set_status("Загрузка связей Лечение-Сотрудник...")

        self._create_header("Лечение ⟷ Сотрудник", "Добавить связь", self._add_treatment_employee)
        columns = ["РК", "РК лечения", "Диагноз", "РК сотрудника", "ФИО сотрудника"]

        self.te_table = ActionTable(self.current_frame, columns, self._edit_treatment_employee, self._delete_treatment_employee)
        self._refresh_treatment_employee()

    def _refresh_treatment_employee(self):
        _, rows = self.db.fetch_all("""
            SELECT ЛС.РК, ЛС.РК_лечения, Л.Диагноз, ЛС.РК_сотрудника, С.ФИО
            FROM Лечение_Сотрудник ЛС
            LEFT JOIN Лечение Л ON ЛС.РК_лечения = Л.РК
            LEFT JOIN Сотрудник С ON ЛС.РК_сотрудника = С.РК
            ORDER BY ЛС.РК
        """)
        self.te_table.refresh(rows)

    def _add_treatment_employee(self):
        self._treatment_employee_form("Добавление связи")

    def _edit_treatment_employee(self, rid):
        _, rows = self.db.fetch_all("SELECT РК_лечения, РК_сотрудника FROM Лечение_Сотрудник WHERE РК = %s", (rid,))
        if rows:
            self._treatment_employee_form("Редактирование связи", rid, rows[0])

    def _delete_treatment_employee(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить связь ID: {rid}?"):
            if self.db.execute("DELETE FROM Лечение_Сотрудник WHERE РК = %s", (rid,)):
                self._refresh_treatment_employee()
                self._set_status(f"Связь {rid} удалена")

    def _treatment_employee_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 300)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Лечение:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        treatments = self.db.get_options("SELECT РК, Диагноз FROM Лечение", "{}")
        treat_combo = ttk.Combobox(win, values=[f"{t[0]} - {t[1]}" for t in treatments], state="readonly", width=35)
        treat_combo.pack(padx=20, pady=(0, 10))
        if data:
            for t in treatments:
                if t[0] == data[0]:
                    treat_combo.set(f"{t[0]} - {t[1]}")
                    break

        tk.Label(win, text="Сотрудник (ветеринар):", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        employees = self.db.get_options("SELECT РК, ФИО FROM Сотрудник WHERE Категория = 'Ветеринар'", "{}")
        emp_combo = ttk.Combobox(win, values=[f"{e[0]} - {e[1]}" for e in employees], state="readonly", width=35)
        emp_combo.pack(padx=20, pady=(0, 20))
        if data and len(data) > 1:
            for e in employees:
                if e[0] == data[1]:
                    emp_combo.set(f"{e[0]} - {e[1]}")
                    break

        def save():
            try:
                values = (
                    int(treat_combo.get().split(" - ")[0]),
                    int(emp_combo.get().split(" - ")[0])
                )
                if rid:
                    self.db.execute("UPDATE Лечение_Сотрудник SET РК_лечения=%s, РК_сотрудника=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Лечение_Сотрудник (РК_лечения, РК_сотрудника) VALUES (%s, %s)", values)
                win.destroy()
                self._refresh_treatment_employee()
                self._set_status("Связь сохранена")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # ПРОФЕССИОНАЛЬНАЯ НАПРАВЛЕННОСТЬ
    # =====================================================
    def _load_prof_dir(self):
        self._clear_content(13)
        self._set_status("Загрузка профессиональной направленности...")

        self._create_header("Проф. направленность", "Добавить запись", self._add_prof_dir)
        columns = ["РК", "Сотрудник", "Доступ к вольерам", "Задачи"]

        self.prof_table = ActionTable(self.current_frame, columns, self._edit_prof_dir, self._delete_prof_dir)
        self._refresh_prof_dir()

    def _refresh_prof_dir(self):
        _, rows = self.db.fetch_all("""
            SELECT П.РК, С.ФИО, П.Доступ_к_вольерам, П.Задачи
            FROM Проф_направленность П
            LEFT JOIN Сотрудник С ON П.РК_сотрудника = С.РК
            ORDER BY П.РК
        """)
        self.prof_table.refresh(rows)

    def _add_prof_dir(self):
        self._prof_dir_form("Добавление записи")

    def _edit_prof_dir(self, rid):
        _, rows = self.db.fetch_all("SELECT РК_сотрудника, Доступ_к_вольерам, Задачи FROM Проф_направленность WHERE РК = %s", (rid,))
        if rows:
            self._prof_dir_form("Редактирование записи", rid, rows[0])

    def _delete_prof_dir(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить запись ID: {rid}?"):
            if self.db.execute("DELETE FROM Проф_направленность WHERE РК = %s", (rid,)):
                self._refresh_prof_dir()
                self._set_status(f"Запись {rid} удалена")

    def _prof_dir_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 400)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Сотрудник:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        employees = self.db.get_options("SELECT РК, ФИО FROM Сотрудник", "{}")
        emp_combo = ttk.Combobox(win, values=[f"{e[0]} - {e[1]}" for e in employees], state="readonly", width=35)
        emp_combo.pack(padx=20, pady=(0, 10))
        if data:
            for e in employees:
                if e[0] == data[0]:
                    emp_combo.set(f"{e[0]} - {e[1]}")
                    break

        tk.Label(win, text="Доступ к вольерам:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_access = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_access.pack(padx=20, pady=(0, 10))
        if data:
            entry_access.insert(0, str(data[1]) if data[1] else "")

        tk.Label(win, text="Задачи:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_tasks = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_tasks.pack(padx=20, pady=(0, 20))
        if data:
            entry_tasks.insert(0, str(data[2]) if data[2] else "")

        def save():
            try:
                values = (
                    int(emp_combo.get().split(" - ")[0]),
                    entry_access.get().strip(),
                    entry_tasks.get().strip()
                )
                if rid:
                    self.db.execute("UPDATE Проф_направленность SET РК_сотрудника=%s, Доступ_к_вольерам=%s, Задачи=%s WHERE РК=%s", (*values, rid))
                else:
                    self.db.execute("INSERT INTO Проф_направленность (РК_сотрудника, Доступ_к_вольерам, Задачи) VALUES (%s, %s, %s)", values)
                win.destroy()
                self._refresh_prof_dir()
                self._set_status("Запись сохранена")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # ЛЕЧЕНИЕ
    # =====================================================
    def _load_treatments(self):
        self._clear_content(14)
        self._set_status("Загрузка лечения...")

        self._create_header("Лечение животных", "Добавить лечение", self._add_treatment)
        columns = ["РК", "Диагноз", "Дата начала", "Дата окончания", "Изолирован"]

        self.treatment_table = ActionTable(self.current_frame, columns, self._edit_treatment, self._delete_treatment)
        self._refresh_treatments()

    def _refresh_treatments(self):
        _, rows = self.db.fetch_all("""
            SELECT Л.РК, Л.Диагноз, Л.Дата_начала,
                   COALESCE(TO_CHAR(Л.Дата_окончания, 'DD.MM.YYYY'), 'В процессе'),
                   CASE WHEN Л.Изолирован THEN 'Да' ELSE 'Нет' END
            FROM Лечение Л
            ORDER BY Л.РК
        """)
        self.treatment_table.refresh(rows)

    def _add_treatment(self):
        self._treatment_form("Добавление лечения")

    def _edit_treatment(self, rid):
        _, rows = self.db.fetch_all("SELECT Диагноз, Дата_начала, Дата_окончания, Изолирован FROM Лечение WHERE РК = %s", (rid,))
        if rows:
            self._treatment_form("Редактирование лечения", rid, rows[0])

    def _delete_treatment(self, rid):
        if messagebox.askyesno("Подтверждение", f"Удалить лечение ID: {rid}?"):
            self.db.execute("DELETE FROM Животное_Лечение WHERE РК_лечения = %s", (rid,))
            if self.db.execute("DELETE FROM Лечение WHERE РК = %s", (rid,)):
                self._refresh_treatments()
                self._set_status(f"Лечение {rid} удалено")

    def _treatment_form(self, title, rid=None, data=None):
        win = self._create_modal_window(title, 450, 450)

        tk.Label(win, text=title, font=('Inter', 16, 'bold'), bg='#ffffff', fg='#2c3e50').pack(pady=20)

        tk.Label(win, text="Диагноз:", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_diagnosis = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_diagnosis.pack(padx=20, pady=(0, 10))
        if data:
            entry_diagnosis.insert(0, str(data[0]) if data[0] else "")

        tk.Label(win, text="Дата начала (ГГГГ-ММ-ДД):", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_start = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_start.pack(padx=20, pady=(0, 10))
        if data:
            entry_start.insert(0, str(data[1]) if data[1] else "")

        tk.Label(win, text="Дата окончания (ГГГГ-ММ-ДД):", font=('Inter', 11), bg='#ffffff', fg='#555555').pack(anchor='w', padx=20, pady=(5, 0))
        entry_end = tk.Entry(win, width=40, font=('Inter', 11), relief='solid', bd=1, highlightthickness=0)
        entry_end.pack(padx=20, pady=(0, 10))
        if data and data[2]:
            entry_end.insert(0, str(data[2]))

        isolated_var = tk.BooleanVar()
        if data and data[3]:
            isolated_var.set(data[3] in (True, 1, 't'))
        tk.Checkbutton(win, text="Изолирован в стационаре", variable=isolated_var,
                      bg='#ffffff', font=('Inter', 11)).pack(anchor='w', padx=20, pady=(0, 20))

        def save():
            try:
                end_date = entry_end.get().strip() if entry_end.get().strip() else None
                if rid:
                    self.db.execute("""
                        UPDATE Лечение SET Диагноз=%s, Дата_начала=%s,
                        Дата_окончания=%s, Изолирован=%s WHERE РК=%s
                    """, (entry_diagnosis.get().strip(), entry_start.get().strip(),
                          end_date, isolated_var.get(), rid))
                else:
                    self.db.execute("""
                        INSERT INTO Лечение (Диагноз, Дата_начала, Дата_окончания, Изолирован)
                        VALUES (%s, %s, %s, %s)
                    """, (entry_diagnosis.get().strip(), entry_start.get().strip(),
                          end_date, isolated_var.get()))
                win.destroy()
                self._refresh_treatments()
                self._set_status("Лечение сохранено")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(win, text="Сохранить", command=save, bg='#2c3e50', fg='white',
                  font=('Inter', 11, 'bold'), padx=30, pady=8, relief='flat', cursor='hand2').pack(pady=20)

    # =====================================================
    # ЗАПРОСЫ
    # =====================================================
    def _load_queries(self):
        self._clear_content(15)
        self._set_status("Загрузка запросов...")

        header_frame = tk.Frame(self.current_frame, bg='#f5f5f5')
        header_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(header_frame, text="Аналитические запросы", font=('Inter', 20, 'bold'),
                 bg='#f5f5f5', fg='#2c3e50').pack(side=tk.LEFT)

        queries = [
            {"name": "1. Ветеринары с зарплатой больше...", "params": [{"name": "Мин. зарплата", "default": 60000}],
             "func": self._query_vets_by_salary, "desc": "Поиск ветеринаров с зарплатой выше указанной суммы"},
            {"name": "2. Дрессировщики в зоопарке...", "params": [{"name": "Зоопарк", "default": "Московский зоопарк"}],
             "func": self._query_trainers_by_zoo, "desc": "Поиск дрессировщиков в указанном зоопарке"},
            {"name": "3. Кормление хищников в...", "params": [{"name": "Время", "default": "09:00:00"}],
             "func": self._query_predators_by_time, "desc": "Поиск кормления хищников в указанное время"},
            {"name": "4. Животные с диагнозом...", "params": [{"name": "Диагноз", "default": "Вирусная инфекция"}],
             "func": self._query_animals_by_diagnosis, "desc": "Поиск животных с указанным диагнозом"},
            {"name": "5. Животные в вольере...", "params": [{"name": "Вольер", "default": "VOL001"}],
             "func": self._query_animals_by_volier, "desc": "Поиск животных в указанном вольере"},
            {"name": "6. Количество животных по типам", "params": [],
             "func": self._query_animals_count_by_type, "desc": "Статистика по типам животных"},
            {"name": "7. Средняя зарплата по категориям", "params": [],
             "func": self._query_avg_salary_by_category, "desc": "Статистика зарплат по категориям"},
            {"name": "8. Объём кормов по типам", "params": [],
             "func": self._query_feed_volume_by_type, "desc": "Статистика кормов по типам"},
            {"name": "9. Сотрудники с зарплатой в диапазоне...", "params": [{"name": "Мин.", "default": 40000}, {"name": "Макс.", "default": 70000}],
             "func": self._query_employees_by_salary_range, "desc": "Поиск сотрудников с зарплатой от X до Y"},
            {"name": "10. Корма с объёмом меньше...", "params": [{"name": "Макс. объём", "default": 200}],
             "func": self._query_feeds_by_volume, "desc": "Поиск кормов с объёмом меньше указанного"},
            {"name": "11. Животные на лечении", "params": [],
             "func": self._query_animals_in_treatment, "desc": "Список всех животных на лечении"}
        ]

        canvas = tk.Canvas(self.current_frame, bg='#f5f5f5', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.current_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f5f5f5')

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for q in queries:
            self._create_query_card(scrollable_frame, q)

    def _create_query_card(self, parent, query):
        card = tk.Frame(parent, bg='#ffffff', relief='flat', bd=1,
                       highlightthickness=1, highlightcolor='#eeeeee', highlightbackground='#eeeeee')
        card.pack(fill=tk.X, pady=8, padx=5)

        tk.Label(card, text=query["name"], font=('Inter', 12, 'bold'),
                 bg='#ffffff', fg='#2c3e50').pack(anchor='w', padx=15, pady=(12, 5))
        tk.Label(card, text=query["desc"], font=('Inter', 10),
                 bg='#ffffff', fg='#888888').pack(anchor='w', padx=15, pady=(0, 10))

        params_frame = tk.Frame(card, bg='#ffffff')
        params_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        param_entries = []
        for param in query["params"]:
            tk.Label(params_frame, text=f"{param['name']}:", font=('Inter', 10),
                     bg='#ffffff', fg='#555555').pack(side=tk.LEFT, padx=5)
            entry = tk.Entry(params_frame, width=15, font=('Inter', 10),
                           relief='solid', bd=1, highlightthickness=0)
            entry.insert(0, str(param["default"]))
            entry.pack(side=tk.LEFT, padx=5)
            param_entries.append(entry)

        def execute():
            params = [e.get().strip() for e in param_entries]
            self._execute_query(query, params)

        btn_frame = tk.Frame(card, bg='#ffffff')
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        tk.Button(btn_frame, text="▶ Выполнить запрос", command=execute,
                  bg='#2c3e50', fg='white', font=('Inter', 10, 'bold'),
                  padx=20, pady=6, relief='flat', cursor='hand2').pack(side=tk.LEFT)

    def _execute_query(self, query, params):
        win = tk.Toplevel(self.root)
        win.title(f"Результат: {query['name']}")
        win.geometry("900x500")
        win.configure(bg='#ffffff')

        frame = tk.Frame(win, bg='#ffffff')
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tree = ttk.Treeview(frame, show="headings", height=18)
        scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        try:
            cols, rows = query["func"](*params) if params else query["func"]()
            if cols:
                tree["columns"] = cols
                for col in cols:
                    tree.heading(col, text=col.replace('_', ' ').title())
                    tree.column(col, width=120, anchor="center")
                for row in rows:
                    tree.insert("", tk.END, values=row)
                status = tk.Label(win, text=f"✅ Найдено записей: {len(rows)}", font=('Inter', 10), bg='#ffffff')
            else:
                status = tk.Label(win, text="ℹ️ Запрос не вернул данных", font=('Inter', 10), bg='#ffffff', fg='#888888')
        except Exception as e:
            status = tk.Label(win, text=f"❌ Ошибка: {str(e)}", font=('Inter', 10), bg='#ffffff', fg='#e74c3c')

        status.pack(fill=tk.X, padx=20, pady=(0, 20))

    # =====================================================
    # ФУНКЦИИ ЗАПРОСОВ
    # =====================================================
    def _query_vets_by_salary(self, min_salary):
        return self.db.fetch_all("SELECT ФИО, Зарплата FROM Сотрудник WHERE Категория = 'Ветеринар' AND Зарплата > %s", (min_salary,))

    def _query_trainers_by_zoo(self, zoo_name):
        return self.db.fetch_all("SELECT С.ФИО, С.Категория, З.Название FROM Сотрудник С JOIN Зоопарк З ON С.РК_зоопарка = З.РК WHERE С.Категория = 'Дрессировщик' AND З.Название = %s", (zoo_name,))

    def _query_predators_by_time(self, time):
        return self.db.fetch_all("SELECT Ж.Кличка, К.Вид, М.Объем_порции FROM Животное Ж JOIN Меню_на_день М ON Ж.РК = М.РК_животного JOIN Корм К ON М.РК_корма = К.РК WHERE Ж.Тип = 'Хищник' AND М.Время = %s", (time,))

    def _query_animals_by_diagnosis(self, diagnosis):
        return self.db.fetch_all("SELECT Ж.Кличка, Ж.Вид, Л.Диагноз FROM Животное Ж JOIN Животное_Лечение ЖЛ ON Ж.РК = ЖЛ.РК_животного JOIN Лечение Л ON ЖЛ.РК_лечения = Л.РК WHERE Л.Диагноз = %s", (diagnosis,))

    def _query_animals_by_volier(self, volier_number):
        return self.db.fetch_all("SELECT Ж.Кличка, Ж.Вид, Ж.Тип, В.Номер_вольера FROM Животное Ж JOIN Вольер В ON Ж.РК_вольера = В.РК WHERE В.Номер_вольера = %s", (volier_number,))

    def _query_animals_count_by_type(self):
        return self.db.fetch_all("SELECT Тип, COUNT(*) FROM Животное GROUP BY Тип")

    def _query_avg_salary_by_category(self):
        return self.db.fetch_all("SELECT Категория, ROUND(AVG(Зарплата)) FROM Сотрудник GROUP BY Категория")

    def _query_feed_volume_by_type(self):
        return self.db.fetch_all("SELECT Тип_корма, SUM(Объем_на_складе) FROM Корм GROUP BY Тип_корма")

    def _query_employees_by_salary_range(self, min_salary, max_salary):
        return self.db.fetch_all("SELECT ФИО, Категория, Зарплата FROM Сотрудник WHERE Зарплата BETWEEN %s AND %s ORDER BY Зарплата", (min_salary, max_salary))

    def _query_feeds_by_volume(self, max_volume):
        return self.db.fetch_all("SELECT Вид, Тип_корма, Объем_на_складе FROM Корм WHERE Объем_на_складе < %s ORDER BY Объем_на_складе", (max_volume,))

    def _query_animals_in_treatment(self):
        return self.db.fetch_all("""
            SELECT Ж.Кличка, Ж.Вид, Л.Диагноз, Л.Дата_начала
            FROM Животное Ж
            JOIN Животное_Лечение ЖЛ ON Ж.РК = ЖЛ.РК_животного
            JOIN Лечение Л ON ЖЛ.РК_лечения = Л.РК
            ORDER BY Л.Дата_начала DESC
        """)

    # =====================================================
    # SQL КОНСОЛЬ
    # =====================================================
    def _load_sql_console(self):
        self._clear_content(16)
        self._set_status("SQL Консоль готова")

        tk.Label(self.current_frame, text="SQL Консоль", font=('Inter', 20, 'bold'),
                 bg='#f5f5f5', fg='#2c3e50').pack(pady=(0, 10))

        main_frame = tk.Frame(self.current_frame, bg='#f5f5f5')
        main_frame.pack(fill=tk.BOTH, expand=True)

        input_frame = tk.Frame(main_frame, bg='#ffffff', relief='flat', bd=1,
                              highlightthickness=1, highlightcolor='#eeeeee', highlightbackground='#eeeeee')
        input_frame.pack(fill=tk.X, pady=(0, 20))

        self.sql_text = tk.Text(input_frame, height=10, font=('Consolas', 11), wrap=tk.WORD,
                                bg='#fafafa', fg='#333333', relief='flat', bd=0)
        self.sql_text.pack(fill=tk.X, padx=15, pady=15)

        btn_frame = tk.Frame(input_frame, bg='#ffffff')
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        tk.Button(btn_frame, text="Выполнить", command=self._execute_custom_sql,
                  bg='#2c3e50', fg='white', font=('Inter', 10, 'bold'),
                  padx=20, pady=6, relief='flat', cursor='hand2').pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Очистить", command=lambda: self.sql_text.delete(1.0, tk.END),
                  bg='#ffffff', fg='#888888', font=('Inter', 10),
                  padx=20, pady=6, relief='flat', cursor='hand2',
                  bd=1, highlightthickness=1).pack(side=tk.LEFT, padx=10)

        result_frame = tk.Frame(main_frame, bg='#ffffff', relief='flat', bd=1,
                               highlightthickness=1, highlightcolor='#eeeeee', highlightbackground='#eeeeee')
        result_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(result_frame, text="Результат:", font=('Inter', 11, 'bold'),
                 bg='#ffffff', fg='#2c3e50').pack(anchor='w', padx=15, pady=(15, 10))

        self.console_tree = ttk.Treeview(result_frame, show="headings", height=12)
        scrollbar_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.console_tree.yview)
        scrollbar_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.console_tree.xview)
        self.console_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.console_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 15))
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X, padx=15)

        self.console_status = tk.Label(result_frame, text="Ожидание запроса...",
                                       font=('Inter', 9), bg='#ffffff', fg='#888888', anchor='w')
        self.console_status.pack(fill=tk.X, padx=15, pady=(0, 15))

    def _execute_custom_sql(self):
        query = self.sql_text.get(1.0, tk.END).strip()
        if not query:
            messagebox.showwarning("Внимание", "Введите SQL-запрос")
            return

        for col in self.console_tree["columns"]:
            self.console_tree.heading(col, text="")
            self.console_tree.column(col, width=0)
        self.console_tree["columns"] = ()
        for item in self.console_tree.get_children():
            self.console_tree.delete(item)

        try:
            if query.strip().upper().startswith("SELECT"):
                cols, rows = self.db.fetch_all(query)
                if cols:
                    self.console_tree["columns"] = cols
                    for col in cols:
                        self.console_tree.heading(col, text=str(col).replace('_', ' ').title())
                        self.console_tree.column(col, width=150, anchor="center")
                    for row in rows:
                        self.console_tree.insert("", tk.END, values=row)
                    self.console_status.config(text=f"✅ SELECT выполнен. Строк: {len(rows)}", fg="#2c3e50")
                else:
                    self.console_status.config(text="ℹ️ Запрос не вернул данных", fg="#888888")
            else:
                success = self.db.execute(query)
                if success:
                    self.console_status.config(text="✅ запрос выполнен успешно", fg="#2c3e50")
                else:
                    self.console_status.config(text="❌ Ошибка выполнения", fg="#e74c3c")
        except Exception as e:
            self.console_status.config(text=f"❌ Ошибка: {str(e)}", fg="#e74c3c")


# =====================================================
# ЗАПУСК
# =====================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = ZooApp(root)
    root.mainloop()