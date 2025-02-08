from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
import mysql.connector
import webbrowser
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'
CORS(app)

# MySQL database configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="technicalWorld@1234",
    database="dbms_project"
)

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/signup")

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        name, password, role = data['name'], data['password'], data['role']

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Authentication WHERE login_id=%s AND password=%s AND role=%s", (name, password, role))
        user = cursor.fetchone()
        cursor.close()

        if user:
            session['user'], session['role'] = name, role
            redirect_url = url_for('reader_portal') if role == 'reader' else url_for('staff_portal')
            return jsonify({"message": "Login successful", "role": role, "redirect": redirect_url}), 200
        else:
            return jsonify({"message": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({"message": "An error occurred during login."}), 500

@app.route('/reader_portal', methods=['GET'])
def reader_portal():
    if 'user' in session and session['role'] == 'reader':
        user = session['user']

        # Initialize all variables to avoid reference issues
        profile, borrowed_books, transactions, orders, fine_details, available_books, book_inventory, payments = (
            {}, [], [], [], [], [], [], []
        )

        try:
            # Fetch profile details
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM Readers WHERE name=%s", (user,))
                profile = cursor.fetchone() or {'email': '', 'phone_no': '', 'address': '', 'name': ''}
                #print(f"Fetched profile details: {profile}")

            # Fetch borrowed books
            with db.cursor(dictionary=True) as cursor:
                cursor.execute(""" 
                    SELECT books.Title as title, transaction_history.return_collect_date as due_date
                    FROM transaction_history
                    JOIN orders ON transaction_history.order_id = orders.order_id
                    JOIN books ON orders.book_no = books.Book_No
                    WHERE orders.user_id = (SELECT user_id FROM Readers WHERE name=%s)
                """, (user,))
                borrowed_books = cursor.fetchall() or []
                #print(f"Fetched borrowed books: {borrowed_books}")

            # Fetch transaction history
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT books.Title as book_title, transaction_history.issue_date, transaction_history.return_collect_date, transaction_history.status
                    FROM transaction_history
                    JOIN orders ON transaction_history.order_id = orders.order_id
                    JOIN books ON orders.book_no = books.Book_No
                    WHERE orders.user_id = (SELECT user_id FROM Readers WHERE name=%s)
                """, (user,))
                transactions = cursor.fetchall() or []
                #if (transactions["status"]==None):
                #    transactions["status"]="No"
                #print(f"Fetched transaction history: {transactions}")

            # Fetch order history
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT books.Title as book_title, orders.type
                    FROM orders
                    JOIN books ON orders.book_no = books.Book_No
                    WHERE orders.user_id = (SELECT user_id FROM Readers WHERE name=%s)
                """, (user,))
                orders = cursor.fetchall() or []
                #print(f"Fetched order history: {orders}")

            # Fetch all fine details (use fetchall() to get multiple fines)
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT Amount as total_fine, status as fine_status
                    FROM fine
                    WHERE User_id = (SELECT user_id FROM Readers WHERE name=%s)
                """, (user,))
                fine_details = cursor.fetchall() or []
                #print(f"Fetched fine details: {fine_details}")

            # Fetch available books
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT Book_No, Title, Author, ISBN, Price, Edition, Category, YOP, publisher.Name FROM books Join publisher ON books.publisher_id=publisher.publisher_id")
                available_books = cursor.fetchall() or []
                #print(f"Fetched available books: {available_books}")

            # Fetch book inventory
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM book_inventory")
                book_inventory = cursor.fetchall() or []
                #print(f"Fetched book inventory: {book_inventory}")

            # Fetch payment details
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT payment.Transaction_id, payment.Payment_Date, payment.Payment_Success, payment.Refund,
                           COALESCE(fine.Amount, 0) AS fine_amount, fine.status AS fine_status
                    FROM payment
                    LEFT JOIN fine ON payment.Transaction_id = fine.User_id
                    WHERE fine.User_id = (SELECT user_id FROM Readers WHERE name=%s)
                """, (user,))
                payments = cursor.fetchall() or []
                #print(f"Fetched payment details: {payments}")

            
        except mysql.connector.Error as e:
            print(f"Error during fetching data: {e}")
            return jsonify({"message": f"An error occurred while fetching data: {e}"}), 500

        # Render the template with all fetched data
        return render_template('reader_portal.html', user=user, profile=profile, borrowed_books=borrowed_books,
                               transactions=transactions, orders=orders, fine_details=fine_details,
                               available_books=available_books, book_inventory=book_inventory, payments=payments)
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('signup_page'))

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        name, password, role = data['name'], data['password'], data['role']

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Authentication WHERE login_id=%s", (name,))
        if cursor.fetchone():
            return jsonify({"message": "Account with this login ID already exists."}), 400

        cursor.execute("INSERT INTO Authentication (login_id, password, role) VALUES (%s, %s, %s)", (name, password, role))
        if role == 'reader':
            cursor.execute("INSERT INTO Readers (name, email, phone_no, address) VALUES (%s, %s, %s, %s)", 
                           (name, data['email'], data['phone_no'], data['address']))
        elif role == 'staff':
            cursor.execute("INSERT INTO Staff (name, post) VALUES (%s, %s)", (name, data['post']))
        db.commit()

        return jsonify({"message": f"{role.capitalize()} signup successful"}), 201
    except mysql.connector.Error as e:
        db.rollback()
        print(f"MySQL error during signup: {e}")
        return jsonify({"message": "MySQL error during signup."}), 500
    finally:
        cursor.close()


## staff portal

@app.route('/staff_portal', methods=['GET'])
def staff_portal():
    if 'user' in session and session['role'] == 'staff':
        user = session['user']
        profile, reader, staff, orders, books, book_inventory = {}, [], [], [], [], []

        try:
            cursor = db.cursor(dictionary=True)

            # Profile details
            cursor.execute("SELECT * FROM staff WHERE name=%s", (user,))
            profile = cursor.fetchone() or {'name': '', 'post': ''}

            # Readers details
            cursor.execute("""
                SELECT readers.user_id AS id, readers.name, readers.email, readers.phone_no, readers.address, authentication.password
                FROM readers JOIN authentication ON readers.name=authentication.login_id
            """)
            reader = cursor.fetchall()

            # Staff details
            cursor.execute("""
                SELECT staff.staff_id AS id, staff.name, staff.post, authentication.password
                FROM staff JOIN authentication ON staff.name=authentication.login_id
            """)
            staff = cursor.fetchall()

            # Orders details
            cursor.execute("SELECT * FROM orders")
            orders = cursor.fetchall()

            # Books details
            cursor.execute("SELECT * FROM books")
            books = cursor.fetchall()
            #print(books)

            cursor.execute("SELECT * FROM book_inventory")
            book_inventory = cursor.fetchall()
            print(book_inventory)

           
            cursor.close()

        except mysql.connector.Error as e:
            return jsonify({"message": f"An error occurred: {e}"}), 500

        return render_template('staff_portal.html', user=user, profile=profile, reader=reader, staff=staff, orders=orders, books=books, book_inventory=book_inventory)
    return redirect(url_for('login'))

#### Functions to Add and Update Orders


@app.route('/add_order', methods=['POST'])
def add_order():
    try:
        user_id = request.form['user_id']
        book_no = request.form['book_no']
        order_type = request.form['type']
        
        query = "INSERT INTO orders (user_id, book_no, type) VALUES (%s, %s, %s)"
        values = (user_id, book_no, order_type)
        
        cursor = db.cursor()
        cursor.execute(query, values)
        db.commit()
        
        cursor.close()
        return redirect(url_for('staff_portal'))
    except mysql.connector.Error as e:
        return {"message": f"An error occurred: {e}"}

@app.route('/update_order', methods=['POST'])
def update_order():
    try:
        order_id = request.form['order_id']
        user_id = request.form.get('user_id')
        book_no = request.form.get('book_no')
        order_type = request.form.get('type')
        
        query = "UPDATE orders SET user_id = %s, book_no = %s, type = %s WHERE order_id = %s"
        values = (user_id, book_no, order_type, order_id)
        
        cursor = db.cursor()
        cursor.execute(query, values)
        db.commit()
        
        cursor.close()
        return redirect(url_for('staff_portal'))
    except mysql.connector.Error as e:
        return {"message": f"An error occurred: {e}"}


@app.route('/add_book', methods=['POST'])
def add_book():
    try:
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        price = request.form['price']
        edition = request.form['edition']
        category = request.form['category']
        publisher_id = request.form['publisher_id']
        yop = request.form['yop']
        
        query = """
            INSERT INTO books (title, author, isbn, price, edition, category, publisher_id, yop)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (title, author, isbn, price, edition, category, publisher_id, yop)
        
        cursor = db.cursor()
        cursor.execute(query, values)
        db.commit()
        
        cursor.close()
        return redirect(url_for('staff_portal'))
    except mysql.connector.Error as e:
        return {"message": f"An error occurred: {e}"}

@app.route('/update_book', methods=['POST'])
def update_book():
    try:
        book_no = request.form['book_no']
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        price = request.form.get('price')
        edition = request.form.get('edition')
        category = request.form.get('category')
        publisher_id = request.form.get('publisher_id')
        yop = request.form.get('yop')
        
        query = """
            UPDATE books 
            SET title = %s, author = %s, isbn = %s, price = %s, edition = %s, category = %s, 
                publisher_id = %s, yop = %s
            WHERE book_no = %s
        """
        values = (title, author, isbn, price, edition, category, publisher_id, yop, book_no)
        
        cursor = db.cursor()
        cursor.execute(query, values)
        db.commit()
        
        cursor.close()
        return redirect(url_for('staff_portal'))
    except mysql.connector.Error as e:
        return {"message": f"An error occurred: {e}"}

@app.route('/add_book_inventory', methods=['POST'])
def add_book_inventory():
    try:
        book_no = request.form['Book_No']
        quantity = request.form['Quantity']
        
        query = "INSERT INTO book_inventory (Book_No, Quantity) VALUES (%s, %s)"
        values = (book_no, quantity)
        
        cursor = db.cursor()
        cursor.execute(query, values)
        db.commit()
        
        cursor.close()
        return redirect(url_for('staff_portal'))
    except mysql.connector.Error as e:
        return {"message": f"An error occurred: {e}"}

@app.route('/update_book_inventory', methods=['POST'])
def update_book_inventory():
    try:
        book_no = request.form['Book_No']
        quantity = request.form.get('Quantity')
        
        query = "UPDATE book_inventory SET Quantity = %s WHERE Book_No = %s"
        values = (quantity, book_no)
        
        cursor = db.cursor()
        cursor.execute(query, values)
        db.commit()
        
        cursor.close()
        return redirect(url_for('staff_portal'))
    except mysql.connector.Error as e:
        return {"message": f"An error occurred: {e}"}


if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)
