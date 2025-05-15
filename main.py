from PyQt6.QtWidgets import * #(QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                            #QMessageBox, QTableWidget, QTableWidgetItem, QDialog, QHBoxLayout,
                             #QAbstractItemView,  QSpinBox, QDateTimeEdit, QComboBox)
from PyQt6.QtCore import Qt
import sqlite3
import bcrypt
import sys
from datetime import datetime

def create_db():
    connection = sqlite3.connect('marketplace.db')
    cursor = connection.cursor()

    # Таблица Пользователей
    cursor.execute(""" CREATE TABLE IF NOT EXISTS users ( id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT NOT NULL,
        last_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, phone_number TEXT NOT NULL UNIQUE, password_hash BLOB NOT NULL ) """)

    # Таблица Продавцов
    cursor.execute(""" CREATE TABLE IF NOT EXISTS sellers ( id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_name TEXT NOT NULL, business_email TEXT NOT NULL UNIQUE, business_phone TEXT NOT NULL UNIQUE,
        legal_address TEXT, password_hash BLOB NOT NULL) """)

    # Таблица Категорий товаров
    cursor.execute(""" CREATE TABLE IF NOT EXISTS categories ( id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE ) """)

    # Таблица Товаров 
    cursor.execute(""" CREATE TABLE IF NOT EXISTS products ( id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL,
        title TEXT NOT NULL, description TEXT NOT NULL, price DECIMAL(10, 2) NOT NULL, quantity INTEGER NOT NULL,
        seller_id INTEGER NOT NULL, FOREIGN KEY (category_id) REFERENCES categories(id),
        FOREIGN KEY (seller_id) REFERENCES sellers(id) ) """)

    # Таблица Отзывов
    cursor.execute(""" CREATE TABLE IF NOT EXISTS reviews ( id INTEGER PRIMARY KEY AUTOINCREMENT, buyer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL, rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5), comment TEXT,
        FOREIGN KEY (buyer_id) REFERENCES users(id), FOREIGN KEY (product_id) REFERENCES products(id) ) """)

    # Таблица Продаж
    cursor.execute("""CREATE TABLE IF NOT EXISTS sales ( id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL, sale_price DECIMAL(10, 2) NOT NULL, sold_quantity INTEGER NOT NULL, applied_promotion_id INTEGER,
        sale_date DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (buyer_id) REFERENCES users(id), FOREIGN KEY (applied_promotion_id) REFERENCES promotions(id) );""")

    # Таблица Акций
    cursor.execute(""" CREATE TABLE IF NOT EXISTS promotions ( id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        discount_percent INTEGER NOT NULL CHECK(discount_percent >= 0 AND discount_percent < 100),
        valid_from DATETIME NOT NULL, valid_to DATETIME NOT NULL ) """)

    # Промежуточная таблица товаров-участников акции
    cursor.execute(""" CREATE TABLE IF NOT EXISTS promotion_items ( promotion_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
        FOREIGN KEY (promotion_id) REFERENCES promotions(id), FOREIGN KEY (product_id) REFERENCES products(id), PRIMARY KEY(promotion_id, product_id) ) """)

    connection.commit()
    connection.close()



style_sheet = """
    /* Основной стиль для всей программы */
    QWidget
    {
        background-color: #F0F0F0;
        color: #333333;
        font-family: Arial, Helvetica, sans-serif;
    }
    QPushButton
    {
        background-color: #AFAFAF;
        color: black;
        padding: 10px 10px;
        border-radius: 10px;
        min-width: 100px;
        max-height: 40px;
        font-weight: bold;
    }
    QPushButton:hover
    {
        background-color: #999999;
    }
    QLineEdit
    {
        background-color: white;
        border: 1px solid #DADADA;
        border-radius: 5px;
        padding: 5px;
    }
    QTableWidget
    {
        selection-background-color: #CFCFCF;
        gridline-color: #DDDDDD;
        alternate-background-color: #EEEEEE;
    }
    QLabel
    {
        font-size: 16px;
        margin-bottom: 10px;
    }
    QDialog
    {
        background-color: #F0F0F0;
    }
    QScrollBar:horizontal
    {
        height: 10px;
        background: #F0F0F0;
        margin: 0px 5px 0px 5px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal
    {
        background: #AFAFAF;
        border-radius: 5px;
        min-width: 20px;
    }
    QComboBox
    {
        background-color: white;
        border: 1px solid #DADADA;
        border-radius: 5px;
        padding: 5px;
        min-width: 150px;
        font-size: 14px;
    }

    QComboBox::drop-down
    {
        subcontrol-position: right center;
        width: 20px;
        border-left: 1px solid #DADADA;
        background-color: transparent;
    }
"""


def get_max_discount_for_product(product_id):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()

    # Запрашиваем максимальную скидку среди всех акций, применяемых к этому товару
    cursor.execute(""" SELECT MAX(pr.discount_percent) FROM promotion_items pi INNER JOIN promotions pr ON pi.promotion_id
            = pr.id WHERE pi.product_id = ? AND pr.valid_from <= ? AND pr.valid_to >= ? """,
        (product_id, datetime.now(), datetime.now()))

    result = cursor.fetchone()
    max_discount = result[0] if result and result[0] is not None else 0
    conn.close()
    return max_discount

def get_discounted_price(product_id):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()

    # Получаем оригинальную цену товара
    cursor.execute("SELECT price FROM products WHERE id=?", (product_id,))
    original_price = cursor.fetchone()[0]

    # Получаем максимальную скидку для товара
    max_discount = get_max_discount_for_product(product_id)

    # Высчитываем цену с учетом скидки
    final_price = original_price * (1 - max_discount / 100)
    conn.close()
    return final_price


    
class MainMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.windows = {}  # Словарь для хранения ссылок на окна
        self.initUI()
        self.update_revenue()
    
    def initUI(self):
        self.setWindowTitle("Маркетплейс")
        layout = QVBoxLayout()
        
        title_label = QLabel("<h1>Добро пожаловать!</h1>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                
        revenue_label = QLabel(f"<b>Доход маркетплейса составил уже:</b> {self.get_total_revenue():,.2f} руб!")
        revenue_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        login_button = QPushButton("Войти")
        login_button.clicked.connect(self.openLoginWindow)
        
        registration_button = QPushButton("Регистрация")
        registration_button.clicked.connect(self.openRegistrationWindow)

        layout.addWidget(title_label)
        layout.addWidget(revenue_label)
        layout.addStretch()
        layout.addWidget(login_button)
        layout.addWidget(registration_button)
        layout.addStretch()
        
        self.setLayout(layout)

    def update_revenue(self):
        total_revenue = self.get_total_revenue()
        for widget in self.children():
            if isinstance(widget, QLabel) and "<b>Доход маркетплейса:" in widget.text():
                widget.setText(f"<b>Доход маркетплейса:</b> {total_revenue:,.2f} руб.")

    def get_total_revenue(self):
        comission = 0.006
        try:
            conn = sqlite3.connect('marketplace.db')
            c = conn.cursor()
            
            # Вычислим общую сумму продаж и применим процент комиссии
            c.execute("""
                SELECT SUM(sale_price * sold_quantity) FROM sales
            """)
            result = c.fetchone()[0]
            return round(result * comission, 2) if result else 0.0
        except Exception as e:
            print(e)
            return 0.0
        finally:
            conn.close()
    
    def openLoginWindow(self):
        if 'login' not in self.windows:
            self.windows['login'] = LoginWindow(self)
        self.windows['login'].show()
        self.hide()

    def openRegistrationWindow(self):
        if 'registration' not in self.windows:
            self.windows['registration'] = RegistrationWindow(self)
        self.windows['registration'].show()
        self.hide()

    def showAgain(self):
        self.show()
        self.update_revenue()

class LoginWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent  # Ссылка на родительское окно
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Вход на маркетплейс")
        layout = QVBoxLayout()

        self.lbl_email = QLabel("Email:")
        self.txt_email = QLineEdit()
        self.lbl_password = QLabel("Пароль:")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)

        btn_login = QPushButton("Войти")
        btn_login.clicked.connect(lambda: self.login(self.txt_email.text(), self.txt_password.text())) 

        layout.addWidget(self.lbl_email)
        layout.addWidget(self.txt_email)
        layout.addWidget(self.lbl_password)
        layout.addWidget(self.txt_password)
        layout.addWidget(btn_login)

        self.setLayout(layout)

    def login(self, email, password):
        try:
            if not email.strip() or not password.strip():
                QMessageBox.warning(self, "Ошибка", "Заполните все поля.")
                return

            conn = sqlite3.connect('marketplace.db')
            cursor = conn.cursor()

            # Проверка пользователя
            cursor.execute("SELECT password_hash FROM users WHERE email=?", (email,))
            user_result = cursor.fetchone()

            flag = 0

            if user_result:
                hashed_password = user_result[0]
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                    user_id = cursor.fetchone()[0]
                    self.openBuyerDashboard(user_id)
                    flag = 1

            # Проверка продавца
            cursor.execute("SELECT password_hash FROM sellers WHERE business_email=?", (email,))
            seller_result = cursor.fetchone()

            if seller_result:
                hashed_password = seller_result[0]
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                    cursor.execute("SELECT id FROM sellers WHERE business_email=?", (email,))
                    seller_id = cursor.fetchone()[0]
                    self.openSellerDashboard(seller_id)
                    flag = 1

            if flag == 0:
                QMessageBox.warning(self, "Ошибка", "Неверный email или пароль.")
                return  # Остаемся на экране, если произошла ошибка

            conn.close()

            # ОЧИСТКА ПОЛЕЙ
            self.txt_email.clear()
            self.txt_password.clear()

        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Возникла ошибка: {str(e)}")
            traceback.print_exc()
        
    def openBuyerDashboard(self, user_id):
        # Переходим в панель покупателя
        self.buyer_dashboard = BuyerDashboard(user_id, self.parent)
        self.buyer_dashboard.show()
        self.hide()
        
    def openSellerDashboard(self, seller_id):
        # Создаем окно панели продавца и сохраняем ссылку на него
        self.dashboard = SellerDashboard(seller_id, self.parent)
        self.dashboard.show()
        self.hide()  # Скрываем окно входа

class BuyerDashboard(QWidget):
    def __init__(self, user_id, main_menu):
        super().__init__()
        self.user_id = user_id
        self.main_menu = main_menu
        self.shopping_cart = ShoppingCart(self.user_id)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Панель покупателя")
        self.setMinimumSize(800, 600)

        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        logout_btn = QPushButton("Выход")
        logout_btn.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_btn)

        settings_btn = QPushButton("Настройки профиля")
        settings_btn.clicked.connect(self.openUserProfileSettings)  
        sidebar_layout.addWidget(settings_btn)

        cart_btn = QPushButton("Моя корзина")
        cart_btn.clicked.connect(self.show_cart)
        sidebar_layout.addWidget(cart_btn)

        history_btn = QPushButton("История покупок")
        history_btn.clicked.connect(self.show_purchase_history)
        sidebar_layout.addWidget(history_btn)

        review_btn = QPushButton("Оставить отзыв")
        review_btn.clicked.connect(self.show_review_management)
        sidebar_layout.addWidget(review_btn)

        self.categories_combo = QComboBox()
        self.categories_combo.addItems(self.fetch_categories())  
        self.categories_combo.currentIndexChanged.connect(self.filterByCategory)
        sidebar_layout.addWidget(self.categories_combo)
    
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Поиск по названию...")
        search_bar.textChanged.connect(self.searchProducts)
        sidebar_layout.addWidget(search_bar)

        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.HLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        sidebar_layout.addWidget(separator_line)

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(8) 
        self.products_table.setHorizontalHeaderLabels([ 
            "ID товара", "Название", "Категория", "Описание", "Цена", "Количество", "Средняя оценка", "Акция"
        ])
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.products_table.doubleClicked.connect(self.showProductDetails)
        central_layout.addWidget(self.products_table)


        self.loadAllProducts()

        main_layout = QHBoxLayout()
        main_layout.addWidget(sidebar_widget, stretch=1)
        main_layout.addWidget(central_widget, stretch=4)

        self.setLayout(main_layout)
        
    def fetch_categories(self):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Извлекаем все уникальные категории
        cursor.execute("SELECT name FROM categories ORDER BY name ASC;")
        rows = cursor.fetchall()

        # Преобразовываем результат в простой список имен категорий
        categories_list = ["Все"] + [row[0] for row in rows]

        conn.close()
        return categories_list
    
    def loadAllProducts(self):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        cursor.execute(""" SELECT p.id, p.title, c.name AS category_name, p.description, p.price, p.quantity, COALESCE(AVG(r.rating), 0)
            AS avg_rating, pr.name AS promotion_name FROM products p LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN promotion_items pi ON p.id = pi.product_id LEFT JOIN promotions pr ON pi.promotion_id = pr.id LEFT JOIN reviews r
            ON p.id = r.product_id GROUP BY p.id """)
        rows = cursor.fetchall()

        # Настройка размера таблицы под количество строк
        self.products_table.setRowCount(len(rows))

        # Перебор всех записей и заполнение таблицы
        row_num = 0
        for row_data in rows:
            columns = [
                str(row_data[0]),             
                row_data[1],                 
                row_data[2],                 
                row_data[3][:50],               
                get_discounted_price(row_data[0]),  
                str(row_data[5]),               
                f"{row_data[6]:.2f}",            
                row_data[7] or "Нет акции"     
            ]

            # Заполняем таблицу
            for col_num, value in enumerate(columns):
                item = QTableWidgetItem(str(value))
                self.products_table.setItem(row_num, col_num, item)
            row_num += 1

        conn.close()


    def filterByCategory(self, index):
        if index == 0:
            self.loadAllProducts()
            return

        # Иначе фильтруем товары по выбранной категории
        category_name = self.categories_combo.currentText()
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Сначала находим ID категории по её имени
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        category_id = cursor.fetchone()[0]

        # Затем фильтруем товары по этому ID
        cursor.execute(""" SELECT p.id, p.title, c.name AS category_name, p.description, p.price, p.quantity, COALESCE(AVG(r.rating), 0)
            AS avg_rating, pr.name AS promotion_name FROM products p LEFT JOIN categories c ON p.category_id = c.id LEFT JOIN promotion_items pi
            ON p.id = pi.product_id LEFT JOIN promotions pr ON pi.promotion_id = pr.id LEFT JOIN reviews r ON p.id = r.product_id WHERE p.category_id = ?
            GROUP BY p.id """, (category_id,))

        rows = cursor.fetchall()

        # Обновляем таблицу товаров
        self.products_table.setRowCount(len(rows))
        row_num = 0
        for row_data in rows:
            columns = [
                str(row_data[0]),
                row_data[1],
                row_data[2],
                row_data[3][:50],                   
                get_discounted_price(row_data[0]),   
                str(row_data[5]),
                f"{row_data[6]:.2f}",
                row_data[7] or "Нет акции"
            ]

            for col_num, value in enumerate(columns):
                item = QTableWidgetItem(str(value))
                self.products_table.setItem(row_num, col_num, item)
            row_num += 1

        conn.close()
    def openUserProfileSettings(self):
        try:
            profile_settings_dialog = UserProfileSettingsDialog(self.user_id)
            profile_settings_dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Что-то пошло не так: {e}")

    def searchProducts(self, text):
        # Сначала определяем текущую категорию
        current_category = self.categories_combo.currentText()

        # Если текущая категория равна "Все", ищем во всей базе
        if current_category == "Все":
            where_clause = "WHERE LOWER(p.title) LIKE LOWER(?)"
        else:
            # Иначе фильтруем ещё и по выбранной категории
            cursor.execute("SELECT id FROM categories WHERE name = ?", (current_category,))
            category_id = cursor.fetchone()[0]
            where_clause = f"WHERE LOWER(p.title) LIKE LOWER(?) AND p.category_id={category_id}"

        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Составляем запрос с учётом текущей категории
        cursor.execute(f""" SELECT p.id, p.title, c.name AS category_name, p.description, p.price, p.quantity, COALESCE(AVG(r.rating), 0)
            AS avg_rating, pr.name AS promotion_name FROM products p LEFT JOIN categories c ON p.category_id = c.id LEFT JOIN promotion_items pi
            ON p.id = pi.product_id LEFT JOIN promotions pr ON pi.promotion_id = pr.id LEFT JOIN reviews r ON p.id = r.product_id {where_clause}
            GROUP BY p.id """, ('%' + text.strip().lower() + '%',))

        rows = cursor.fetchall()

        # Обновляем таблицу товаров
        self.products_table.setRowCount(len(rows))
        row_num = 0
        for row_data in rows:
            columns = [
                str(row_data[0]),
                row_data[1],
                row_data[2],
                row_data[3][:50],                    
                get_discounted_price(row_data[0]),   
                str(row_data[5]),
                f"{row_data[6]:.2f}",
                row_data[7] or "Нет акции"
            ]

            for col_num, value in enumerate(columns):
                item = QTableWidgetItem(str(value))
                self.products_table.setItem(row_num, col_num, item)
            row_num += 1

        conn.close()


    def showProductDetails(self):
        selected_row = self.products_table.currentRow()
        if selected_row != -1:
            try:
                product_id = int(self.products_table.item(selected_row, 0).text())
                detail_dialog = ProductDetailDialog(product_id, shopping_cart=self.shopping_cart, parent=self)
                detail_dialog.exec()
            except Exception as ex:
                QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {ex}")

    def show_cart(self):
        try:
            cart = ShoppingCart(self.user_id)
            cart_window = CartWindow(self.shopping_cart, parent=self)
            cart_window.exec()
            self.loadAllProducts()
        except Exception as ex:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {ex}")

    def show_purchase_history(self):
        try:
            history_window = PurchaseHistoryWindow(self.user_id, parent=self)
            history_window.exec()
        except Exception as ex:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {ex}")
            
    def show_review_management(self):
        try:
            conn = sqlite3.connect('marketplace.db')
            review_window = ReviewManagementWindow(self.user_id, conn, parent=self)
            review_window.exec()
            conn.close()
        except Exception as ex:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {ex}")

    def logout(self):
        # Возврат на главное окно (не создается новое окно)
        self.main_menu.showAgain()
        self.hide()

class ReviewManagementWindow(QDialog):
    def __init__(self, user_id, conn, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.conn = conn
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Таблица для отображения отзывов
        self.reviews_table = QTableWidget()
        self.reviews_table.setColumnCount(5)
        self.reviews_table.setHorizontalHeaderLabels(["ID отзыва", "Товар", "Оценка", "Комментарий", "Действия"])
        self.reviews_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.reviews_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.reviews_table.verticalHeader().hide()
        self.reviews_table.setAlternatingRowColors(True)
        self.reviews_table.setSortingEnabled(True)


        self.reviews_table.horizontalHeader().setStretchLastSection(True)
        # Загрузка отзывов пользователя
        self.load_reviews()

        # Добавляем таблицу в главный макет
        layout.addWidget(self.reviews_table)

        # Кнопка для добавления отзыва
        add_review_button = QPushButton("Добавить отзыв")
        add_review_button.clicked.connect(self.add_review)
        layout.addWidget(add_review_button)

        # Кнопка для закрытия окна
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)
        self.setWindowTitle("Управление моими отзывами")
        self.resize(800, 600)

    def load_reviews(self):
        cursor = self.conn.cursor()
        cursor.execute(""" SELECT r.id, p.title, r.rating, r.comment FROM reviews r JOIN products p ON r.product_id = p.id WHERE r.buyer_id = ? """, (self.user_id,))
        reviews = cursor.fetchall()

        self.reviews_table.setRowCount(len(reviews))
        for row_idx, review in enumerate(reviews):
            review_id, product_title, rating, comment = review

            # Ячейки для каждой колонки
            id_item = QTableWidgetItem(str(review_id))
            product_item = QTableWidgetItem(product_title)
            rating_item = QTableWidgetItem(str(rating))
            comment_item = QTableWidgetItem(comment)

            # Добавляем ячейки в таблицу
            self.reviews_table.setItem(row_idx, 0, id_item)
            self.reviews_table.setItem(row_idx, 1, product_item)
            self.reviews_table.setItem(row_idx, 2, rating_item)
            self.reviews_table.setItem(row_idx, 3, comment_item)

            self.reviews_table.setRowHeight(row_idx, 40)
            
            # Действия (редактировать и удалить)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            actions_layout.setContentsMargins(0, 0, 0, 0)

            edit_button = QPushButton("Редактировать")
            edit_button.clicked.connect(lambda checked, rid=review_id: self.edit_review(rid))
            actions_layout.addWidget(edit_button)

            delete_button = QPushButton("Удалить")
            delete_button.clicked.connect(lambda checked, rid=review_id: self.delete_review(rid))
            actions_layout.addWidget(delete_button)

            # Ставим виджет с кнопками в ячейку таблицы
            cell_widget = QWidget()
            cell_widget.setLayout(actions_layout)
            self.reviews_table.setCellWidget(row_idx, 4, cell_widget)

    def edit_review(self, review_id):
        # Открывает окно редактирования отзыва
        edit_dialog = EditReviewDialog(review_id, self.conn, parent=self)
        edit_dialog.exec()

    def delete_review(self, review_id):
        reply = QMessageBox.question(self, "Удаление отзыва", "Вы точно хотите удалить этот отзыв?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM reviews WHERE id=?", (review_id,))
            self.conn.commit()
            QMessageBox.information(self, "Удалено", "Отзыв успешно удалён.")
            self.load_reviews()

    def add_review(self):
        # Откроем форму добавления отзыва
        add_review_dialog = AddReviewForm(self.user_id, self.conn, parent=self)
        add_review_dialog.exec()
        self.load_reviews()

class EditReviewDialog(QDialog):
    def __init__(self, review_id, conn, parent=None):
        super().__init__(parent)
        self.review_id = review_id
        self.conn = conn
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        # Загружаем данные отзыва
        cursor = self.conn.cursor()
        cursor.execute("SELECT rating, comment FROM reviews WHERE id=?", (self.review_id,))
        review_data = cursor.fetchone()
        if review_data:
            rating, comment = review_data
        else:
            QMessageBox.warning(self, "Ошибка", "Отзыв не найден.")
            self.close()
            return

        # Поле рейтинга
        self.rating_spinbox = QSpinBox()
        self.rating_spinbox.setRange(1, 5)
        self.rating_spinbox.setValue(rating)
        layout.addRow("Оценка:", self.rating_spinbox)

        # Поле комментария
        self.comment_field = QLineEdit()
        self.comment_field.setText(comment)
        layout.addRow("Комментарий:", self.comment_field)

        # Кнопка сохранить
        save_button = QPushButton("Сохранить изменения")
        save_button.clicked.connect(self.save_changes)
        layout.addWidget(save_button)

        self.setLayout(layout)
        self.setWindowTitle("Редактирование отзыва")

    def save_changes(self):
        rating = self.rating_spinbox.value()
        comment = self.comment_field.text().strip()

        cursor = self.conn.cursor()
        cursor.execute("UPDATE reviews SET rating=?, comment=? WHERE id=?", (rating, comment, self.review_id))
        self.conn.commit()
        QMessageBox.information(self, "Обновлено", "Отзыв успешно обновлён.")
        self.parent().load_reviews()  # Обновляем список отзывов родителя
        self.accept()

class AddReviewForm(QDialog):
    def __init__(self, user_id, conn, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.conn = conn
        self.product_id = None  # Переменная для хранения идентификатора товара
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        # Список товаров, которые пользователь купил
        self.purchased_products_combobox = QComboBox()
        self.load_purchased_products()
        layout.addRow("Выберите товар:", self.purchased_products_combobox)

        # Поле для выбора оценки (от 1 до 5)
        self.rating_spinbox = QSpinBox()
        self.rating_spinbox.setRange(1, 5)
        layout.addRow("Оценка:", self.rating_spinbox)

        # Поле для ввода комментария
        self.comment_field = QLineEdit()
        layout.addRow("Комментарий:", self.comment_field)

        # Кнопка для отправки отзыва
        submit_button = QPushButton("Добавить отзыв")
        submit_button.clicked.connect(self.submit_review)
        layout.addWidget(submit_button)

        self.setLayout(layout)
        self.setWindowTitle("Добавить отзыв")

    def load_purchased_products(self):
        # Загружаем товары, которые пользователь купил
        cursor = self.conn.cursor()
        cursor.execute(""" SELECT DISTINCT p.id, p.title FROM sales s JOIN products p ON s.product_id = p.id WHERE s.buyer_id = ? """, (self.user_id,))
        purchased_products = cursor.fetchall()

        # Заполняем комбинационный бокс (dropdown list)
        for prod_id, title in purchased_products:
            self.purchased_products_combobox.addItem(title, prod_id)
            
        if len(purchased_products) > 0:
            self.select_product(0)
        # Установка сигнала на изменение выбора
        self.purchased_products_combobox.currentIndexChanged.connect(self.select_product)

    def select_product(self, index):
        # Сохраняем выбранный идентификатор товара
        self.product_id = self.purchased_products_combobox.itemData(index)

    def submit_review(self):
        # Получаем данные отзыва
        rating = self.rating_spinbox.value()
        comment = self.comment_field.text().strip()

        # Проверяем, выбран ли товар
        if not self.product_id:
            QMessageBox.warning(self, "Ошибка", "Выберите товар для отзыва.")
            return

        # Проверяем, есть ли уже отзыв от этого пользователя на этот товар
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM reviews WHERE buyer_id=? AND product_id=?", (self.user_id, self.product_id))
        existing_review = cursor.fetchone()

        if existing_review:
            QMessageBox.warning(self, "Ошибка", "Вы уже оставили отзыв на этот товар.")
            return

        # Добавляем отзыв в базу данных
        cursor.execute("INSERT INTO reviews (buyer_id, product_id, rating, comment) VALUES (?,?,?,?)",
                       (self.user_id, self.product_id, rating, comment))
        self.conn.commit()
        QMessageBox.information(self, "Успех", "Ваш отзыв успешно отправлен.")
        self.accept()

class PurchaseHistoryWindow(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Таблица для отображения истории покупок
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "ID покупки", "Товар", "Количество", "Цена", "Дата покупки", "Промоакция"
        ])
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSortingEnabled(True)

        # Загрузка данных о покупке
        self.load_purchases()

        # Простая кнопка для закрытия окна
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)

        # Организация компоновки
        layout.addWidget(self.history_table)
        layout.addWidget(close_button)

        self.setLayout(layout)
        self.setWindowTitle("История покупок")
        self.resize(800, 600)

    def load_purchases(self):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Запрос на получение истории покупок конкретного пользователя
        cursor.execute(""" SELECT s.id, p.title, s.sold_quantity, s.sale_price, s.sale_date, pr.name AS promotion_name FROM sales
            s LEFT JOIN products p ON s.product_id = p.id LEFT JOIN promotions pr ON s.applied_promotion_id = pr.id WHERE
            s.buyer_id = ? ORDER BY s.sale_date DESC """, (self.user_id,))

        purchases = cursor.fetchall()
        conn.close()

        # Обновляем таблицу результатами
        self.history_table.setRowCount(len(purchases))
        for row_idx, purchase in enumerate(purchases):
            date_obj = datetime.strptime(purchase[4], "%Y-%m-%d %H:%M:%S")
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")

            columns = [
                str(purchase[0]),  
                purchase[1],        
                str(purchase[2]),  
                f"{purchase[3]:.2f} ₽",  
                formatted_date,     
                purchase[5] or "Без промоакции"     
            ]

            for col_idx, value in enumerate(columns):
                item = QTableWidgetItem(str(value))
                self.history_table.setItem(row_idx, col_idx, item)

class UserProfileSettingsDialog(QDialog):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        # Поле ввода имени
        self.first_name_edit = QLineEdit()
        # Поле ввода фамилии
        self.last_name_edit = QLineEdit()
        # Поле ввода адреса электронной почты
        self.email_edit = QLineEdit()
        # Поле ввода телефонного номера
        self.phone_number_edit = QLineEdit()
        # Поле ввода нового пароля
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        # Кнопки Сохранить и Отменить
        save_button = QPushButton("Сохранить")
        cancel_button = QPushButton("Отмена")

        # Обработка нажатия кнопки Сохранить
        save_button.clicked.connect(self.saveChanges)
        # Обработка нажатия кнопки Отменить
        cancel_button.clicked.connect(self.reject)

        # Группировка кнопок
        button_box = QDialogButtonBox()
        button_box.addButton(save_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(cancel_button, QDialogButtonBox.ButtonRole.RejectRole)

        # Добавляем элементы формы
        layout.addRow("Имя:", self.first_name_edit)
        layout.addRow("Фамилия:", self.last_name_edit)
        layout.addRow("Электронная почта:", self.email_edit)
        layout.addRow("Телефон:", self.phone_number_edit)
        layout.addRow("Новый пароль:", self.new_password_edit)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setWindowTitle("Редактирование профиля покупателя")

        # Загружаем данные текущего пользователя
        self.loadUserData()

    def loadUserData(self):
        try:
            with sqlite3.connect('marketplace.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT first_name, last_name, email, phone_number FROM users WHERE id=?""",
                    (self.user_id,)
                )
                data = cursor.fetchone()

                if data:
                    self.first_name_edit.setText(data[0])
                    self.last_name_edit.setText(data[1])
                    self.email_edit.setText(data[2])
                    self.phone_number_edit.setText(data[3])
        except Exception as ex:
            QMessageBox.critical(self, "Ошибка загрузки данных", f"Произошла ошибка: {ex}")

    def saveChanges(self):
        try:
            first_name = self.first_name_edit.text().strip()
            last_name = self.last_name_edit.text().strip()
            email = self.email_edit.text().strip()
            phone = self.phone_number_edit.text().strip()
            new_password = self.new_password_edit.text().strip()

            # Проверяем наличие обязательных полей
            if not all([first_name, last_name, email, phone]):
                raise ValueError("Все поля должны быть заполнены.")

            # Проверяем формат номера телефона
            if not phone.isdigit():
                raise ValueError("Номер телефона должен состоять только из цифр.")

            # Подключаемся к базе данных
            with sqlite3.connect('marketplace.db') as conn:
                cursor = conn.cursor()

                # Проверяем уникальность email среди покупателей и продавцов
                cursor.execute("SELECT COUNT(*) FROM users WHERE email=? AND id!=?", (email, self.user_id))
                count_email_users = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM sellers WHERE business_email=?", (email,))
                count_email_sellers = cursor.fetchone()[0]

                total_count_email = count_email_users + count_email_sellers

                # Проверяем уникальность phone среди покупателей и продавцов
                cursor.execute("SELECT COUNT(*) FROM users WHERE phone_number=? AND id!=?", (phone, self.user_id))
                count_phone_users = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM sellers WHERE business_phone=?", (phone,))
                count_phone_sellers = cursor.fetchone()[0]

                total_count_phone = count_phone_users + count_phone_sellers

                # Если найден хотя бы один дубликат email или телефона
                if total_count_email > 0:
                    raise ValueError("Данный адрес электронной почты уже занят.")

                if total_count_phone > 0:
                    raise ValueError("Данный номер телефона уже занят.")

                # Хэшируем новый пароль, если он указан
                if new_password:
                    salt = bcrypt.gensalt()
                    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt)
                else:
                    hashed_password = None

                # Формируем запрос на обновление данных
                update_query = """UPDATE users SET first_name=?, last_name=?, email=?, phone_number=? """
                params = [first_name, last_name, email, phone]

                if hashed_password:
                    update_query += ", password_hash=?"
                    params.append(hashed_password)

                update_query += "WHERE id=?"
                params.append(self.user_id)

                # Выполняем обновление данных
                cursor.execute(update_query, tuple(params))
                conn.commit()

            # Сообщаем пользователю об успешности операции
            QMessageBox.information(self, "Успешно", "Ваш профиль успешно обновлен!")
            self.accept()  # Закрываем окно диалога

        except ValueError as ve:
            QMessageBox.warning(self, "Ошибка", str(ve))
        except Exception as ex:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {ex}")

class ProductDetailDialog(QDialog):
    def __init__(self, product_id, shopping_cart,parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.shopping_cart = shopping_cart
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Подробности товара")
        layout = QVBoxLayout()

        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Запрашиваем информацию о товаре
        cursor.execute(""" SELECT p.id, p.title, c.name AS category_name, p.description, p.price, p.quantity, COALESCE(AVG(r.rating), 0)
            AS avg_rating, pr.name AS promotion_name FROM products p LEFT JOIN categories c ON p.category_id = c.id LEFT JOIN promotion_items
            pi ON p.id = pi.product_id LEFT JOIN promotions pr ON pi.promotion_id = pr.id LEFT JOIN reviews r ON p.id = r.product_id WHERE p.id = ?

            GROUP BY p.id, p.title, c.name, p.description, p.price, p.quantity, pr.name """, (self.product_id,))
        product_data = cursor.fetchone()

        if not product_data:
            QMessageBox.critical(self, "Ошибка", "Данный товар не найден.")
            return

        # Раскладываем данные о товаре
        ( _, title, category_name, description, original_price, quantity, avg_rating, promotion_name) = product_data

        # Получаем итоговую цену с учетом скидок
        final_price = get_discounted_price(self.product_id)

        # Основные элементы интерфейса
        title_label = QLabel(f"<h2><b>{title}</b></h2>")
        category_label = QLabel(f"Категория: {category_name}")
        description_label = QLabel(description)
        price_label = QLabel(f"Цена: {final_price:.2f} руб.")
        quantity_label = QLabel(f"В наличии: {quantity} шт.")
        rating_label = QLabel(f"Средний рейтинг: {avg_rating:.2f}") if avg_rating > 0 else QLabel("Рейтинг отсутствует")

        # Спиннер для выбора количества товара
        spin_box = QSpinBox()
        spin_box.setRange(1, quantity)
        spin_box.valueChanged.connect(self.update_total_cost)

        # Метка для отображения итоговой суммы
        total_cost_label = QLabel("Общая сумма: 0.00 руб.")
        total_cost_label.setObjectName("totalCostLabel")

        # Кнопка добавления в корзину
        add_cart_button = QPushButton("Добавить в корзину")
        add_cart_button.clicked.connect(self.add_to_cart)
        add_cart_button.setEnabled(quantity > 0)

        # Добавляем элементы в форму
        form_layout = QFormLayout()
        form_layout.addRow("Выбор количества:", spin_box)
        form_layout.addRow(total_cost_label)
        form_layout.addRow(add_cart_button)

        # Генеральный макет окна
        layout.addWidget(title_label)
        layout.addWidget(category_label)
        layout.addWidget(description_label)
        layout.addWidget(price_label)
        layout.addWidget(quantity_label)
        layout.addWidget(rating_label)
        layout.addLayout(form_layout)

        self.setLayout(layout)
        self.resize(400, 600)
        conn.close()

        # Обновляем итоговую сумму при старте окна
        self.update_total_cost()

    def update_total_cost(self):
        try:
            # Получаем текущее значение спина
            spin_value = self.findChild(QSpinBox).value()
            # Повторно считаем итоговую цену
            final_price = get_discounted_price(self.product_id)
            total_cost = spin_value * final_price
            # Находим метку и обновляем её текст
            total_cost_label = self.findChild(QLabel, "totalCostLabel")
            total_cost_label.setText(f"Общая сумма: {total_cost:.2f} руб.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Что-то пошло не так: {e}")

    def add_to_cart(self):
        try:
            quantity = self.findChild(QSpinBox).value()
            self.shopping_cart.add_item(self.product_id, quantity)
            QMessageBox.information(self, "Успех", f"{quantity} единиц товара добавлены в корзину.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Что-то пошло не так: {e}")

def find_applicable_promotion(product_id):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()

    cursor.execute(""" SELECT pi.promotion_id, pr.discount_percent FROM promotion_items pi INNER JOIN promotions pr
        ON pi.promotion_id = pr.id WHERE pi.product_id = ? AND datetime('now') BETWEEN pr.valid_from AND pr.valid_to ORDER BY
        pr.discount_percent DESC LIMIT 1 """, (product_id,))

    applicable_promo = cursor.fetchone()
    conn.close()
    return applicable_promo

def get_discounted_price(product_id):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()

    # Получаем оригинальную цену товара
    cursor.execute("SELECT price FROM products WHERE id=?", (product_id,))
    original_price = cursor.fetchone()[0]

    # Проверяем наличие акции
    applicable_promo = find_applicable_promotion(product_id)
    if applicable_promo:
        _, discount_percent = applicable_promo
        final_price = original_price * (1 - discount_percent / 100)
    else:
        final_price = original_price

    conn.close()
    return final_price
    

class CartWindow(QDialog):
    def __init__(self, shopping_cart, parent=None):
        super().__init__(parent)
        self.shopping_cart = shopping_cart
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Таблица для отображения товаров в корзине
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Товар', 'Количество', 'Цена', 'Стоимость'])
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.fill_table()

        # Общая сумма заказа
        self.total_label = QLabel(f'Итого: {self.shopping_cart.get_total_amount():.2f} ₽')
        self.total_label.setStyleSheet('font-weight: bold; color: green;')

        # Кнопка для оформления заказа
        self.buy_button = QPushButton('Завершить покупку')
        self.buy_button.clicked.connect(self.process_order)

        # Складываем виджетами
        layout.addWidget(self.table)
        layout.addWidget(self.total_label)
        layout.addWidget(self.buy_button)

        self.setLayout(layout)
        self.setWindowTitle('Корзина')
        self.resize(600, 400)

    def fill_table(self):
        # Очищаем таблицу перед добавлением новых данных
        self.table.setRowCount(0)

        # Заполняем таблицу товарами из корзины
        for i, (product_id, quantity) in enumerate(self.shopping_cart.items):
            # Название товара
            product_name = self.get_product_name(product_id)
            # Цена товара
            unit_price = self.shopping_cart.get_product_price(product_id)
            # Стоимость всего выбранного товара
            total_price = unit_price * quantity

            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(product_name))
            self.table.setItem(i, 1, QTableWidgetItem(str(quantity)))
            self.table.setItem(i, 2, QTableWidgetItem(f'{unit_price:.2f} ₽'))
            self.table.setItem(i, 3, QTableWidgetItem(f'{total_price:.2f} ₽'))

    def process_order(self):
        # Обрабатываем покупку, удаляя купленные товары из корзины
        try:
            self.shopping_cart.checkout()
            QMessageBox.information(self, 'Готово!', 'Ваш заказ успешно оформлен.')
            self.close()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Во время оформления заказа возникла ошибка:\n{e}')
    @staticmethod
    def get_product_name(product_id):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM products WHERE id=?", (product_id,))
        name = cursor.fetchone()[0]
        conn.close()
        return name


class ShoppingCart:
    def __init__(self, user_id):
        self.user_id = user_id
        self.items = []  # Туплы вида (product_id, quantity)

    def add_item(self, product_id, quantity):
        # Добавляем товар в корзину
        self.items.append((product_id, quantity))

    def remove_item(self, product_id):
        # Удаляем конкретный товар из корзины
        self.items = [item for item in self.items if item[0] != product_id]

    def clear_cart(self):
        # Полностью очищаем корзину
        self.items.clear()

    def get_total_amount(self):
        # Суммарная стоимость товаров в корзине
        total = 0
        for product_id, quantity in self.items:
            price = self.get_product_price(product_id)
            total += price * quantity
        return total

    def get_product_price(self, product_id):
        # Получаем текущую цену товара с учетом возможных скидок
        return get_discounted_price(product_id)

    def checkout(self):
        # Оформляем покупку
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        for product_id, quantity in self.items:
            # Проверяем доступное количество товара
            cursor.execute("SELECT quantity FROM products WHERE id=?", (product_id,))
            available_stock = cursor.fetchone()[0]
            if available_stock < quantity:
                raise ValueError(f"Недостаточно товара ({available_stock}) для покупки {quantity} штук.")

            applicable_promo = find_applicable_promotion(product_id)
            if applicable_promo:
                promo_id, _ = applicable_promo
            else:
                promo_id = None

            # Получение цены товара
            discounted_price = self.get_product_price(product_id)

            # Регистрация продажи с указанием применяемой акции
            cursor.execute(
                """ INSERT INTO sales ( product_id, buyer_id, sale_price, sold_quantity, applied_promotion_id ) VALUES (?,?,?,?,?) """,
                (product_id, self.user_id, discounted_price, quantity, promo_id))

            # Уменьшаем остаток товара
            cursor.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (quantity, product_id))

        conn.commit()
        conn.close()
        self.clear_cart()
        
class SellerDashboard(QWidget):
    def __init__(self, seller_id, main_menu ):
        super().__init__()
        self.seller_id = seller_id
        self.main_menu = main_menu
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Панель продавца")
        self.setMinimumSize(800, 600)

        # Боковая панель
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        logout_btn = QPushButton("Выход")
        logout_btn.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_btn)
        
        settings_btn = QPushButton("Настройки профиля")
        settings_btn.clicked.connect(self.openProfileSettings)
        sidebar_layout.addWidget(settings_btn)

        reviews_btn = QPushButton("Обзор отзывов")
        reviews_btn.clicked.connect(self.viewReviews)
        sidebar_layout.addWidget(reviews_btn)

        history_btn = QPushButton("История продаж")
        history_btn.clicked.connect(self.show_sales_history) 
        sidebar_layout.addWidget(history_btn)

        promotions_btn = QPushButton("Управление акциями")
        promotions_btn.clicked.connect(self.managePromotions)
        sidebar_layout.addWidget(promotions_btn)

        # Поиск товаров
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Поиск по названию...")
        search_bar.textChanged.connect(self.filterProductsByName)
        sidebar_layout.addWidget(search_bar)

        # Центральная панель с таблицей товаров
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)

        # Заголовок страницы
        title_label = QLabel("<h1>Управление товарами</h1>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        central_layout.addWidget(title_label)

        # Кнопки действий сверху
        top_buttons_widget = QWidget()
        top_buttons_layout = QHBoxLayout(top_buttons_widget)
        add_product_btn = QPushButton("Добавить новый товар")
        add_product_btn.clicked.connect(self.addNewProduct)
        delete_product_btn = QPushButton("Удалить выбранный товар")
        delete_product_btn.clicked.connect(self.deleteSelectedProduct)
        assign_promo_btn = QPushButton("Назначить акцию товару")
        assign_promo_btn.clicked.connect(self.assignPromotion)
        top_buttons_layout.addWidget(add_product_btn)
        top_buttons_layout.addWidget(delete_product_btn)
        top_buttons_layout.addWidget(assign_promo_btn)
        central_layout.addWidget(top_buttons_widget)

        # Таблица товаров с дополнительным полем "Акция"
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(8)  # Один дополнительный столбец для акции
        self.products_table.setHorizontalHeaderLabels([
            "ID товара", "Название", "Категория", "Описание", "Цена", "Количество", "Средняя оценка", "Акция"
        ])
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.products_table.doubleClicked.connect(self.editProduct)
        central_layout.addWidget(self.products_table)

        # Главное окно
        main_layout = QHBoxLayout()
        main_layout.addWidget(sidebar_widget, stretch=1)
        main_layout.addWidget(central_widget, stretch=4)

        self.setLayout(main_layout)

        # Загружаем товары
        self.loadProducts()

    def managePromotions(self):
        # Открыть окно управления акциями
        self.promotions_dialog = PromotionsDialog(self.seller_id)
        self.promotions_dialog.exec()
    def viewReviews(self):
        # Открыть панель обзора отзывов
        self.reviews_panel = ReviewsPanel(self.seller_id)
        self.reviews_panel.show() 

    def filterProductsByName(self, text):
        # Очистка таблицы
        self.products_table.clearContents()
        self.products_table.setRowCount(0)

        # Если текст пуст, загрузить все товары
        if not text.strip():
            self.loadProducts()
            return
        try:
            # Фильтр товаров по названию
            conn = sqlite3.connect('marketplace.db')
            cursor = conn.cursor()
            cursor.execute(""" SELECT p.id, p.title, c.name AS category_name, p.description, p.price, p.quantity, COALESCE(AVG(r.rating), 0)
                AS avg_rating, pr.name AS promotion_name FROM products p LEFT JOIN categories c ON p.category_id = c.id LEFT JOIN promotion_items pi
                ON p.id = pi.product_id LEFT JOIN promotions pr ON pi.promotion_id = pr.id LEFT JOIN reviews r ON p.id = r.product_id
                WHERE p.seller_id = ? AND LOWER(p.title) LIKE LOWER('%'||?||'%') GROUP BY p.id, p.title, c.name, p.description, p.price,
                p.quantity, pr.name """, (self.seller_id, text))
            filtered_rows = cursor.fetchall()

            self.products_table.setRowCount(len(filtered_rows))
            row_num = 0
            for row_data in filtered_rows:
                for col_num, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value))
                    self.products_table.setItem(row_num, col_num, item)
                row_num += 1

            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Что-то пошло не так: {e}")
            

    def loadProducts(self):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        cursor.execute(""" SELECT p.id, p.title, c.name AS category_name, p.description, p.price, p.quantity, COALESCE(AVG(r.rating), 0)
            AS avg_rating, pr.name AS promotion_name FROM products p LEFT JOIN categories c ON p.category_id = c.id LEFT JOIN
            promotion_items pi ON p.id = pi.product_id LEFT JOIN promotions pr ON pi.promotion_id = pr.id LEFT JOIN reviews r ON p.id
            = r.product_id WHERE p.seller_id = ? GROUP BY p.id """, (self.seller_id,))
        rows = cursor.fetchall()

        self.products_table.setRowCount(len(rows))
        row_num = 0
        for row_data in rows:
            # Получаем оригинальную цену товара
            product_id = row_data[0]
            original_price = row_data[4]

            # Вычисляем итоговую цену с учетом скидки
            final_price = get_discounted_price(product_id)

            # Заполняем таблицу с учетом скидки
            data_with_discount = list(row_data[:4]) + [final_price] + list(row_data[5:])
            for col_num, value in enumerate(data_with_discount):
                item = QTableWidgetItem(str(value))
                self.products_table.setItem(row_num, col_num, item)
            row_num += 1

        conn.close()

    def editProduct(self):
        selected_row = self.products_table.currentRow()
        if selected_row != -1:
            product_id_item = self.products_table.item(selected_row, 0)  # Берём ID товара из первой колонки
            if product_id_item is None:
                QMessageBox.warning(self, "Ошибка", "Не удалось получить ID товара.")
                return

            product_id = int(product_id_item.text())

            self.edit_dialog = EditProductDialog(product_id, self.seller_id)
            result = self.edit_dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                self.loadProducts()  # Обновляем таблицу после изменений

    def addNewProduct(self):
        dialog = AddProductDialog(self.seller_id)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.loadProducts()  # Обновим таблицу после добавления товара

    def deleteSelectedProduct(self):
        selected_row = self.products_table.currentRow()
        if selected_row != -1:
            product_id = int(self.products_table.item(selected_row, 0).text())
            reply = QMessageBox.question(
                self, "Подтверждение удаления",
                f"Удалить товар №{product_id}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                conn = sqlite3.connect('marketplace.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM products WHERE id=? AND seller_id=?", (product_id, self.seller_id))
                conn.commit()
                conn.close()
                self.loadProducts()  # Обновление таблицы

    def assignPromotion(self):
        # Открыть диалог выбора акции для товара
        selected_row = self.products_table.currentRow()
        if selected_row != -1:
            product_id = int(self.products_table.item(selected_row, 0).text())
            assign_dialog = AssignPromotionDialog(product_id, self.seller_id)
            result = assign_dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                self.loadProducts()  # Обновляем таблицу после назначения акции

    def openProfileSettings(self):
        try:
            profile_settings_dialog = ProfileSettingsDialog(self.seller_id)
            profile_settings_dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Что-то пошло не так: {e}")

    def logout(self):
        # Возврат на главное окно (не создается новое окно)
        self.main_menu.showAgain()
        self.hide()
    def show_sales_history(self):
        # Открываем окно истории продаж
        sales_history_window = SalesHistoryWindow(self.seller_id, parent=self)
        sales_history_window.exec()


class SalesHistoryWindow(QDialog):
    def __init__(self, seller_id, parent=None):
        super().__init__(parent)
        self.seller_id = seller_id
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Таблица для отображения статистики продаж
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(6)
        self.sales_table.setHorizontalHeaderLabels([
            "ID продажи", "Товар", "Количество", "Цена", "Дата продажи", "Доход"
        ])
        self.sales_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sales_table.setAlternatingRowColors(True)
        self.sales_table.setSortingEnabled(True)

        # Загрузка данных о продажах
        self.load_sales()

        # Кнопка закрыть
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(self.sales_table)
        layout.addWidget(close_button)

        self.setLayout(layout)
        self.setWindowTitle("История продаж")
        self.resize(800, 600)

    def load_sales(self):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Получаем историю продаж текущего продавца
        cursor.execute(
            """SELECT s.id, p.title, s.sold_quantity, s.sale_price, s.sale_date, s.sale_price * s.sold_quantity AS revenue
               FROM sales s JOIN products p ON s.product_id = p.id
               WHERE p.seller_id = ?
               ORDER BY s.sale_date DESC""",
            (self.seller_id,)
        )

        sales = cursor.fetchall()
        conn.close()

        # Настраиваем количество строк в таблице
        self.sales_table.setRowCount(len(sales))

        # Перебираем каждую продажу и добавляем её данные в таблицу
        for row_idx, sale in enumerate(sales):
            sale_id, product_title, sold_qty, sale_price, sale_date_str, revenue = sale

            # Применяем комиссию
            adjusted_revenue = float(revenue) * 0.994

            # Форматируем дату продажи
            sale_date = datetime.strptime(sale_date_str, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")

            columns = [
                str(sale_id),       
                product_title,         
                str(sold_qty),          
                f"{sale_price:.2f} ₽",  
                sale_date,             
                f"{adjusted_revenue:.2f} ₽"     
            ]

            # Заполняем ячейки таблицы
            for col_idx, value in enumerate(columns):
                item = QTableWidgetItem(str(value))
                self.sales_table.setItem(row_idx, col_idx, item)

class ProfileSettingsDialog(QDialog):
    def __init__(self, seller_id):
        super().__init__()
        self.seller_id = seller_id
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        # Поля для редактирования
        self.organization_name_edit = QLineEdit()
        self.business_email_edit = QLineEdit()
        self.business_phone_edit = QLineEdit()
        self.legal_address_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        # Заполняем форму текущими данными
        self.loadSellerData()

        save_button = QPushButton("Сохранить")
        cancel_button = QPushButton("Отмена")

        # Связывание сигналов кнопок с действиями
        save_button.clicked.connect(self.saveChanges)
        cancel_button.clicked.connect(self.reject)

        # Объединение кнопок в одну группу
        button_box = QDialogButtonBox()
        button_box.addButton(save_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(cancel_button, QDialogButtonBox.ButtonRole.RejectRole)

        # Форматируем UI
        layout.addRow("Организация:", self.organization_name_edit)
        layout.addRow("Email:", self.business_email_edit)
        layout.addRow("Телефон:", self.business_phone_edit)
        layout.addRow("Юридический адрес:", self.legal_address_edit)
        layout.addRow("Новый пароль:", self.password_edit)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setWindowTitle("Редактирование профиля продавца")

    def loadSellerData(self):
        try:
            with sqlite3.connect('marketplace.db') as conn:
                cursor = conn.cursor()
                cursor.execute(""" SELECT organization_name, business_email, business_phone, legal_address FROM sellers WHERE id=? """, (self.seller_id,))
                current_data = cursor.fetchone()

                if current_data:
                    self.organization_name_edit.setText(current_data[0])
                    self.business_email_edit.setText(current_data[1])
                    self.business_phone_edit.setText(current_data[2])
                    self.legal_address_edit.setText(current_data[3])
        except Exception as ex:
            QMessageBox.critical(self, "Ошибка загрузки данных", f"Произошла ошибка: {ex}")

    def saveChanges(self):
        try:
            org_name = self.organization_name_edit.text().strip()
            email = self.business_email_edit.text().strip()
            phone = self.business_phone_edit.text().strip()
            address = self.legal_address_edit.text().strip()
            new_password = self.password_edit.text().strip()

            # Проверка заполненности ключевых полей
            if not all([org_name, email, phone]):
                raise ValueError("Необходимо заполнить обязательные поля.")

            # Проверка формата номера телефона
            if not phone.isdigit():
                raise ValueError("Номер телефона должен содержать только цифры.")

            # Соединение с базой данных
            with sqlite3.connect('marketplace.db') as conn:
                cursor = conn.cursor()

                # Проверяем уникальность email среди покупателей и продавцов
                cursor.execute("SELECT COUNT(*) FROM users WHERE email=? AND id!=?", (email, self.seller_id))
                count_email_users = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM sellers WHERE business_email=?", (email,))
                count_email_sellers = cursor.fetchone()[0]

                total_count_email = count_email_users + count_email_sellers

                # Проверяем уникальность phone среди покупателей и продавцов
                cursor.execute("SELECT COUNT(*) FROM users WHERE phone_number=? AND id!=?", (phone, self.seller_id))
                count_phone_users = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM sellers WHERE business_phone=?", (phone,))
                count_phone_sellers = cursor.fetchone()[0]

                total_count_phone = count_phone_users + count_phone_sellers

                # Если найден хотя бы один дубликат email или телефона
                if total_count_email > 1 and count_email_users !=1:
                    raise ValueError("Данный адрес электронной почты уже занят.")

                if total_count_phone > 1 and count_phone_users !=1 :
                    raise ValueError("Данный номер телефона уже занят.")

                # Если задан новый пароль, хешируем его
                if new_password:
                    salt = bcrypt.gensalt()
                    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt)
                else:
                    hashed_password = None

                # Составляем SQL-запрос для обновления записи
                update_query = """ UPDATE sellers SET organization_name=?, business_email=?, business_phone=?, legal_address=? """
                params = [org_name, email, phone, address]

                if hashed_password:
                    update_query += ", password_hash=?"
                    params.append(hashed_password)

                update_query += " WHERE id=?"
                params.append(self.seller_id)

                # Выполняем обновление данных
                cursor.execute(update_query, tuple(params))
                conn.commit()

            # Уведомляем пользователя об успешной операции
            QMessageBox.information(self, "Успех", "Профиль успешно обновлён!")
            self.accept()

        except ValueError as ve:
            QMessageBox.warning(self, "Ошибка", str(ve))
        except Exception as ex:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {ex}")

class ReviewsPanel(QWidget):
    def __init__(self, seller_id):
        super().__init__()
        self.seller_id = seller_id
        self.selected_product_name = None  # Новое состояние фильтра по названию товара
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Отзывы о товарах")
        layout = QVBoxLayout()

        # Верхний блок для поиска отзывов по товару
        search_block = QWidget()
        search_layout = QHBoxLayout(search_block)

        # Поле для ввода названия товара
        self.product_name_input = QLineEdit()
        self.product_name_input.setPlaceholderText("Введите название товара для поиска")
        search_layout.addWidget(self.product_name_input)

        # Кнопка для фильтрации отзывов
        search_btn = QPushButton("Фильтровать отзывы")
        search_btn.clicked.connect(self.filterByProductName)
        search_layout.addWidget(search_btn)

        layout.addWidget(search_block)

        # Таблица отзывов
        self.reviews_table = QTableWidget()
        self.reviews_table.setColumnCount(4)
        self.reviews_table.setHorizontalHeaderLabels(["Имя покупателя", "Товар", "Рейтинг", "Комментарий"])
        self.reviews_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.reviews_table)

        # Загружаем отзывы
        self.loadReviews()

        self.setLayout(layout)

    def loadReviews(self):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Запрос зависит от установленного фильтра
        if self.selected_product_name is None:
            # Без фильтра — грузим все отзывы
            cursor.execute(""" SELECT u.first_name || ' ' || u.last_name AS full_name, p.title, r.rating, r.comment,
                r.id FROM reviews r INNER JOIN users u ON r.buyer_id=u.id INNER JOIN products p ON r.product_id=p.id WHERE p.seller_id=? """, (self.seller_id,))
        else:
            # Грузим отзывы только по указанному товару
            cursor.execute(""" SELECT u.first_name || ' ' || u.last_name AS full_name, p.title, r.rating, r.comment,
                r.id FROM reviews r INNER JOIN users u ON r.buyer_id=u.id INNER JOIN products p ON r.product_id=p.id WHERE p.seller_id=? AND p.title LIKE ? """, (self.seller_id, '%' + self.selected_product_name + '%'))  # LIKE с частичным соответствием

        rows = cursor.fetchall()

        self.reviews_table.setRowCount(len(rows))
        row_num = 0
        for row_data in rows:
            for col_num, value in enumerate(row_data[:-1]):  # Последний столбец — id отзыва, не нужен в таблице
                item = QTableWidgetItem(str(value))
                self.reviews_table.setItem(row_num, col_num, item)
            row_num += 1

        conn.close()

    def filterByProductName(self):
        # Читаем введённое значение названия товара
        product_name = self.product_name_input.text().strip()
        if product_name:
            self.selected_product_name = product_name
        else:
            self.selected_product_name = None  # Снимаем фильтр, если поле пустое

        # Обновляем таблицу с отзывами
        self.loadReviews()

        
class AssignPromotionDialog(QDialog):
    def __init__(self, product_id, seller_id):
        super().__init__()
        self.product_id = product_id
        self.seller_id = seller_id
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Назначение акции товару")
        layout = QVBoxLayout()

        # Список доступных акций
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM promotions")
        available_promos = cursor.fetchall()
        conn.close()

        # Добавляем пункт "Без акции"
        self.promo_combo = QComboBox()
        self.promo_combo.addItem("Без акции", None)  # Специальный пункт для снятия акции
        for promo_id, promo_name in available_promos:
            self.promo_combo.addItem(promo_name, promo_id)

        layout.addWidget(QLabel("Выберите акцию:"))
        layout.addWidget(self.promo_combo)

        # Кнопка подтверждения
        confirm_btn = QPushButton("Применить акцию")
        confirm_btn.clicked.connect(self.applyPromotion)
        layout.addWidget(confirm_btn)

        self.setLayout(layout)

    def applyPromotion(self):
        selected_promo_id = self.promo_combo.currentData()

        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        if selected_promo_id is None:
            # Если выбрано "Без акции", удаляем существующую связь
            cursor.execute("DELETE FROM promotion_items WHERE product_id=?", (self.product_id,))
        else:
            # Присваиваем новую акцию или обновляем старую
            cursor.execute("INSERT OR REPLACE INTO promotion_items (promotion_id, product_id) VALUES (?, ?)", (selected_promo_id, self.product_id))

        conn.commit()
        conn.close()

        QMessageBox.information(self, "Готово", "Акция назначена товару, цены обновлены.")
        self.accept()

        
class PromotionsDialog(QDialog):
    def __init__(self, seller_id):
        super().__init__()
        self.seller_id = seller_id
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Управление акциями")
        layout = QVBoxLayout()

        # Таблица акций
        self.promotions_table = QTableWidget()
        self.promotions_table.setColumnCount(4)
        self.promotions_table.setHorizontalHeaderLabels(["Название акции", "Процент скидки", "Начало", "Конец"])
        self.promotions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.promotions_table)

        # Кнопка создания новой акции
        create_promo_btn = QPushButton("Создать акцию")
        create_promo_btn.clicked.connect(self.createPromotion)
        layout.addWidget(create_promo_btn)

        # Загружаем акции
        self.loadPromotions()

        self.setLayout(layout)

    def loadPromotions(self):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM promotions ORDER BY valid_from DESC")
        rows = cursor.fetchall()

        self.promotions_table.setRowCount(len(rows))
        row_num = 0
        for row_data in rows:
            promo_id = row_data[0]
            name = row_data[1]
            discount = row_data[2]
            start_date = row_data[3]
            end_date = row_data[4]

            self.promotions_table.setItem(row_num, 0, QTableWidgetItem(name))
            self.promotions_table.setItem(row_num, 1, QTableWidgetItem(str(discount)))
            self.promotions_table.setItem(row_num, 2, QTableWidgetItem(start_date))
            self.promotions_table.setItem(row_num, 3, QTableWidgetItem(end_date))
            row_num += 1

        conn.close()

    def createPromotion(self):
        try:
            create_dialog = CreatePromotionDialog(self.seller_id)
            result = create_dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                self.loadPromotions()  # Обновляем список акций после создания
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"При открытии окна возникла ошибка: {str(e)}")

class CreatePromotionDialog(QDialog):
    def __init__(self, seller_id):
        super().__init__()
        self.seller_id = seller_id
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Создание акции")
        layout = QVBoxLayout()

        # Название акции
        label_promo_name = QLabel("Название акции:")
        self.promo_name_input = QLineEdit()
        layout.addWidget(label_promo_name)
        layout.addWidget(self.promo_name_input)

        # Процент скидки
        label_discount = QLabel("Процент скидки (%):")
        self.discount_input = QSpinBox()
        self.discount_input.setRange(0, 99)
        layout.addWidget(label_discount)
        layout.addWidget(self.discount_input)

        # Дата начала акции
        label_start_date = QLabel("Дата начала:")
        self.start_date_input = QDateTimeEdit()
        self.start_date_input.setCalendarPopup(True)
        layout.addWidget(label_start_date)
        layout.addWidget(self.start_date_input)

        # Дата окончания акции
        label_end_date = QLabel("Дата окончания:")
        self.end_date_input = QDateTimeEdit()
        self.end_date_input.setCalendarPopup(True)
        layout.addWidget(label_end_date)
        layout.addWidget(self.end_date_input)

        # Кнопка подтверждения
        confirm_btn = QPushButton("Создать акцию")
        confirm_btn.clicked.connect(self.confirmPromotion)
        layout.addWidget(confirm_btn)

        self.setLayout(layout)

    def confirmPromotion(self):
        try:
            promo_name = self.promo_name_input.text().strip()
            discount = self.discount_input.value()
            start_date = self.start_date_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            end_date = self.end_date_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")

            # Проверка корректности данных
            if not promo_name:
                QMessageBox.warning(self, "Ошибка", "Введите название акции.")
                return

            # Проверка срока действия акции
            now = datetime.now()
            start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

            if start_dt > end_dt:
                QMessageBox.warning(self, "Ошибка", "Дата окончания должна быть позже даты начала.")
                return

            if now > end_dt:
                QMessageBox.warning(self, "Ошибка", "Срок действия акции истекает до настоящего времени.")
                return

            # Добавляем акцию в базу данных
            conn = sqlite3.connect('marketplace.db')
            cursor = conn.cursor()
            cursor.execute(""" INSERT INTO promotions (name, discount_percent, valid_from, valid_to) VALUES
                (?, ?, ?, ?) """, (promo_name, discount, start_date, end_date))
            conn.commit()
            conn.close()

            QMessageBox.information(self, "Готово", "Акция успешно создана")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Возникла ошибка при создании акции: {str(e)}")
            traceback.print_exc()  # Выведет полную информацию об ошибке в консоль
        
class EditProductDialog(QDialog):
    def __init__(self, product_id, seller_id):
        super().__init__()
        self.product_id = product_id
        self.seller_id = seller_id
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Редактирование товара")
        layout = QVBoxLayout()

        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        # Объединяем данные товаров и категорий
        cursor.execute(""" SELECT p.id, p.title, c.name AS category_name, p.description, p.price, p.quantity FROM
            products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.id=? """, (self.product_id,))
        current_product = cursor.fetchone()
        conn.close()

        # Инициализируем поля для редактирования
        self.title_input = QLineEdit(current_product[1])  # Название товара
        self.category_input = QLineEdit(current_product[2])  # Название категории
        self.description_input = QLineEdit(current_product[3])
        self.price_input = QLineEdit(str(current_product[4]))
        self.quantity_input = QLineEdit(str(current_product[5]))

        # Формируем UI
        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.saveChanges)

        layout.addWidget(QLabel("Название:"))
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel("Категория:"))
        layout.addWidget(self.category_input)
        layout.addWidget(QLabel("Описание:"))
        layout.addWidget(self.description_input)
        layout.addWidget(QLabel("Цена:"))
        layout.addWidget(self.price_input)
        layout.addWidget(QLabel("Количество:"))
        layout.addWidget(self.quantity_input)
        layout.addWidget(save_btn)

        self.setLayout(layout)
    def validateInput(self):
        # Проверка цены
        try:
            price = float(self.price_input.text())
            if price <= 0:
                raise ValueError("Цена должна быть положительным числом.")
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение цены.")
            return False

        # Проверка количества
        try:
            quantity = int(self.quantity_input.text())
            if quantity <= 0:
                raise ValueError("Количество должно быть положительным числом.")
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение количества.")
            return False

        return True
    
    def saveChanges(self):
        if not self.validateInput():  # Проверка правильности введённых данных
            return
        new_title = self.title_input.text().strip()
        new_category_name = self.category_input.text().strip()
        new_description = self.description_input.text()
        new_price = float(self.price_input.text())
        new_quantity = int(self.quantity_input.text())

        # Проверяем категорию и получаем её ID
        category_id = self.get_or_create_category(new_category_name)

        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        cursor.execute("""UPDATE products SET title=?, category_id=?, description=?, price=?, quantity=? WHERE id=?""",
                      (new_title, category_id, new_description, new_price, new_quantity, self.product_id))
        conn.commit()
        conn.close()
        self.accept()

    def get_or_create_category(self, category_name):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Сначала ищем категорию по имени
        cursor.execute("SELECT id FROM categories WHERE name=?", (category_name,))
        result = cursor.fetchone()

        if result:
            category_id = result[0]
        else:
            # Если категории нет, создаём новую
            cursor.execute("INSERT INTO categories(name) VALUES (?)", (category_name,))
            category_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return category_id

# Окно для добавления нового товара
class AddProductDialog(QDialog):
    def __init__(self, seller_id):
        super().__init__()
        self.seller_id = seller_id
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Новый товар")
        layout = QVBoxLayout()

        self.title_input = QLineEdit()  # Поле для названия товара
        self.category_input = QLineEdit()  # Поле для названия категории
        self.description_input = QLineEdit()
        self.price_input = QLineEdit()
        self.quantity_input = QLineEdit()

        save_btn = QPushButton("Добавить товар")
        save_btn.clicked.connect(self.addProduct)

        layout.addWidget(QLabel("Название:"))
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel("Категория:"))
        layout.addWidget(self.category_input)
        layout.addWidget(QLabel("Описание:"))
        layout.addWidget(self.description_input)
        layout.addWidget(QLabel("Цена:"))
        layout.addWidget(self.price_input)
        layout.addWidget(QLabel("Количество:"))
        layout.addWidget(self.quantity_input)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def validateInput(self):
        # Проверка цены
        try:
            price = float(self.price_input.text())
            if price <= 0:
                raise ValueError("Цена должна быть положительным числом.")
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение цены.")
            return False

        # Проверка количества
        try:
            quantity = int(self.quantity_input.text())
            if quantity <= 0:
                raise ValueError("Количество должно быть положительным числом.")
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение количества.")
            return False

        return True

    def addProduct(self):
        if not self.validateInput():  # Проверка правильности введённых данных
            return
        title = self.title_input.text().strip()
        category_name = self.category_input.text().strip()
        description = self.description_input.text()
        price = float(self.price_input.text())
        quantity = int(self.quantity_input.text())

        # Проверяем категорию и получаем её ID
        category_id = self.get_or_create_category(category_name)

        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO products(category_id, title, description, price, quantity, seller_id) VALUES (?, ?, ?, ?, ?, ?)""",
                      (category_id, title, description, price, quantity, self.seller_id))
        conn.commit()
        conn.close()
        self.accept()

    def get_or_create_category(self, category_name):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Сначала ищем категорию по имени
        cursor.execute("SELECT id FROM categories WHERE name=?", (category_name,))
        result = cursor.fetchone()

        if result:
            category_id = result[0]
        else:
            # Если категории нет, создаём новую
            cursor.execute("INSERT INTO categories(name) VALUES (?)", (category_name,))
            category_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return category_id
    

# Основной класс регистрации
class RegistrationWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent  # Сохраняем ссылку на главное окно
        self.is_seller_mode = False  # Переменная режима регистрации
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Регистрация на маркетплейс")
        self.setMinimumSize(300, 500)
        layout = QVBoxLayout()

        # Элементы ввода зависят от выбранного режима
        self.lbl_first_field = QLabel("Имя:")
        self.txt_first_field = QLineEdit()
        self.lbl_second_field = QLabel("Фамилия:")
        self.txt_second_field = QLineEdit()
        self.lbl_email = QLabel("Email:")
        self.txt_email = QLineEdit()
        self.lbl_phone = QLabel("Телефон:")
        self.txt_phone = QLineEdit()
        self.lbl_password = QLabel("Пароль:")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)

        # Переключатель типа регистрации
        self.radio_seller = QPushButton("Регистрация как продавец")
        self.radio_seller.setCheckable(True)
        self.radio_seller.toggled.connect(self.changeFormFields)  # Связываем изменение формы с изменением состояния кнопки

        # Кнопка регистрации
        self.btn_register = QPushButton("Зарегистрироваться")
        self.btn_register.clicked.connect(self.onRegisterClick)

        # Добавляем элементы в макет
        layout.addWidget(self.lbl_first_field)
        layout.addWidget(self.txt_first_field)
        layout.addWidget(self.lbl_second_field)
        layout.addWidget(self.txt_second_field)
        layout.addWidget(self.lbl_email)
        layout.addWidget(self.txt_email)
        layout.addWidget(self.lbl_phone)
        layout.addWidget(self.txt_phone)
        layout.addWidget(self.lbl_password)
        layout.addWidget(self.txt_password)
        layout.addWidget(self.radio_seller)
        layout.addWidget(self.btn_register)

        self.setLayout(layout)

    def changeFormFields(self, checked):
        if checked:
            # Режим продавца активирован
            self.lbl_first_field.setText("Название организации:")
            self.lbl_second_field.setText("Юридический адрес:")
            self.is_seller_mode = True
            self.radio_seller.setText("Регистрация как покупатель")  # Меняем надпись на кнопке
        else:
            # Обычный режим регистрации
            self.lbl_first_field.setText("Имя:")
            self.lbl_second_field.setText("Фамилия:")
            self.is_seller_mode = False
            self.radio_seller.setText("Регистрация как продавец")  # Возвращаем первоначальную надпись

    def onRegisterClick(self):
        # Получение данных из интерфейса
        first_value = self.txt_first_field.text().strip()
        second_value = self.txt_second_field.text().strip()
        email = self.txt_email.text().strip()
        phone = self.txt_phone.text().strip()
        password = self.txt_password.text().strip()

        # Базовая проверка заполненности
        if not all([first_value, second_value, email, phone, password]):
            QMessageBox.warning(self, "Ошибка", "Все поля должны быть заполнены.")
            return

        # Проверка телефона на допустимый формат (например, числовой)
        if not phone.isdigit():
            QMessageBox.warning(self, "Ошибка", "Номер телефона должен содержать только цифры.")
            return

        # Проверка уникальности email и телефона в базе данных
        try:
            conn = sqlite3.connect('marketplace.db')
            cursor = conn.cursor()
            
            # Проверяем email на уникальность в обеих таблицах
            cursor.execute("SELECT COUNT(*) FROM users WHERE email=?", (email,))
            count_users_email = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sellers WHERE business_email=?", (email,))
            count_sellers_email = cursor.fetchone()[0]

            # Проверяем телефон на уникальность в обеих таблицах
            cursor.execute("SELECT COUNT(*) FROM users WHERE phone_number=?", (phone,))
            count_users_phone = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sellers WHERE business_phone=?", (phone,))
            count_sellers_phone = cursor.fetchone()[0]

            # Если email или телефон уже используются
            if count_users_email > 0 or count_sellers_email > 0:
                QMessageBox.warning(self, "Ошибка", "Электронная почта уже используется другим пользователем.")
                conn.close()
                return

            if count_users_phone > 0 or count_sellers_phone > 0:
                QMessageBox.warning(self, "Ошибка", "Номер телефона уже используется другим пользователем.")
                conn.close()
                return

            # Продолжаем регистрацию
            self.register(first_value, second_value, email, phone, password)
            conn.close()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def register(self, first_value, second_value, email, phone, password):
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()

        # Выбор таблицы для вставки данных
        table_name = 'sellers' if self.is_seller_mode else 'users'

        # Проверка уникальности email
        unique_column = 'business_email' if self.is_seller_mode else 'email'
        cursor.execute(f"SELECT * FROM {table_name} WHERE {unique_column}=?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            QMessageBox.warning(self, "Ошибка", "Пользователь с таким Email уже существует.")
            return

        # Хэширование пароля
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

        # Добавляем нового пользователя или продавца
        if self.is_seller_mode:
            cursor.execute("INSERT INTO sellers (organization_name, business_email, business_phone, legal_address, password_hash) VALUES (?,?,?,?,?)",
                            (first_value, email, phone, second_value, hashed_password ))
        else:
            cursor.execute("INSERT INTO users (first_name, last_name, email, phone_number, password_hash) VALUES (?,?,?,?,?)",
                            (first_value, second_value, email, phone, hashed_password))

        conn.commit()
        conn.close()

        QMessageBox.information(self, "Успешно", "Вы успешно зарегистрированы.")

        # ОЧИСТКА ПОЛЕЙ
        self.txt_first_field.clear()
        self.txt_second_field.clear()
        self.txt_email.clear()
        self.txt_phone.clear()
        self.txt_password.clear()

        # Возвращаемся на главное окно
        self.parent.showAgain()
        self.hide()

        
# Главная функция для запуска приложения
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(style_sheet)
    # Создаем базу данных (если она ещё не была создана ранее)
    create_db()

    main_menu = MainMenu()
    main_menu.show()

    sys.exit(app.exec())
