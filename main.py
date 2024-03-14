from flask_login import LoginManager, UserMixin, login_user, logout_user, user_logged_in, login_required, current_user
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from werkzeug import security as pswd_controller
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, asc
from functools import wraps
import datetime
import calendar
import smtplib
import shutil
import os

MY_EMAIL = "demelgayle4@gmail.com"
APP_PASSWORD = "lrwakfivpymjwbas"
RECEIVERS_EMAIL = "gayledemel@yahoo.com"
GMAIL_SEVER = "smtp.gmail.com"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
TYPE_OF_HASH = 'pbkdf2:sha256'
SALT = 5
ZERO = 0

new_product = True
adding_new_address = False

db = SQLAlchemy()
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///product_info.db"
app.secret_key = b'_5#y2L"F4Q8z$n^xec]/'

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(Users, user_id)


with app.app_context():
    db.create_all()


class Users(db.Model, UserMixin):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    date_of_birth = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    favorited_items = db.relationship('Favorite', backref="client")
    carted_items = db.relationship('Cart', backref="client")
    delivery_address = db.relationship('Address', backref="client")


class ProductInfo(db.Model):
    __tablename__ = "Product Info"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    product_name = db.Column(db.String, unique=True, nullable=False)
    type = db.Column(db.String, nullable=False)
    cost = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String, nullable=False)
    reviewer = db.relationship('Reviews', backref="poster")


class Reviews(db.Model):
    __tablename__ = "Reviews"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('Product Info.id'), nullable=False)
    review = db.Column(db.String, nullable=False)


class Favorite(db.Model):
    __tablename__ = "Favorites"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)


class Cart(db.Model):
    __tablename__ = "Carted Items"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    product_amount = db.Column(db.Integer, nullable=False)


class Address(db.Model):
    __tablename__ = "Addresses"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    address = db.Column(db.Integer, nullable=False)
    checked = db.Column(db.Boolean, nullable=False)


def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return redirect(abort(403))
        return func(*args, **kwargs)

    return decorated_function


@app.route('/', methods=['GET', 'POST'])
def homepage():
    products = db.session.execute(db.select(ProductInfo).order_by(ProductInfo.id)).scalars()
    product_image_path = "/static/Images/Product Images"
    if request.method == 'POST':
        if 'delete-button' in request.form:
            product_image_path = (f"C:/Users/Demel/Documents/Python_Projects/"
                                  f"Rachelle_Website/Beautiful Peaches/static/Images/Product Images")
            refactor_database(product_image_path)
            return redirect(url_for('homepage'))
        elif 'by-id' in request.form:
            products = db.session.execute(db.select(ProductInfo).order_by(desc(ProductInfo.id))).scalars()
            return redirect(url_for('homepage'))
        elif 'low-to-high' in request.form:
            products = db.session.execute(db.select(ProductInfo).order_by(asc(ProductInfo.cost))).scalars()
            return render_template('yoni_products.html', products=products, product_image_path=product_image_path)
        elif 'high-to-low' in request.form:
            products = db.session.execute(db.select(ProductInfo).order_by(desc(ProductInfo.cost))).scalars()
            return render_template('yoni_products.html', products=products, product_image_path=product_image_path)
    elif request.method == "GET":
        return render_template('yoni_products.html', products=products, product_image_path=product_image_path)


@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    current_year = int(datetime.datetime.now().year)
    if request.method == 'POST':
        query = Users.query.filter_by(email=request.form.get('email')).first()
        if query is None:
            new_user = Users(name=request.form['name'], email=request.form['email'],
                             date_of_birth=f"{calendar.month_name[int(request.form['month'])]}-{request.form['day']}-{request.form['year']}",
                             password=pswd_controller.generate_password_hash(
                                 password=request.form['password'], method=TYPE_OF_HASH, salt_length=SALT))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            if user_logged_in:
                return redirect(url_for('profile'))
            else:
                return render_template('sign_up.html', current_year=current_year)
        else:
            flash('The email you entered already exist. Please try another or Sign In.')
            return render_template('sign_up.html', current_year=current_year)
    if request.method == 'GET':
        return render_template('sign_up.html', current_year=current_year)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('email')
        if username_or_email.find('@') > 0:
            query = Users.query.filter_by(email=request.form.get('email')).first()
            if query is None:
                flash('The email you entered does not exist. Please SignUp or Try again.')
                return render_template('login.html')
            elif query.id > 0:
                found_user = query
                right_password_entered = pswd_controller.check_password_hash(query.password,
                                                                             request.form.get('password'))
                if right_password_entered:
                    login_user(found_user)
                    return redirect(url_for('profile'))
                else:
                    flash('Invalid password.')
                    return render_template('login.html')
        else:
            flash('Please enter the "@" symbol.')
            return render_template('login.html')
    if request.method == 'GET':
        return render_template('login.html')


@app.route('/skincare', methods=['GET', 'POST'])
def skincare():
    products = db.session.execute(db.select(ProductInfo).order_by(ProductInfo.id)).scalars()
    product_image_path = (f"C:/Users/Demel/Documents/Python_Projects/"
                          f"Rachelle_Website/Beautiful Peaches/static/Images/Product Images")
    if request.method == 'POST':
        if 'delete-button' in request.form:
            refactor_database(product_image_path)
        return redirect(url_for('skincare'))
    elif request.method == "GET":
        product_image_path = "/static/Images/Product Images"
        return render_template('skincare_products.html', products=products, product_image_path=product_image_path)


@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product(product_id):
    product_info = db.get_or_404(ProductInfo, product_id)
    product_image_path = f'/static/Images/Product Images/{product_info.id}'
    if request.method == "GET":
        return render_template('product_page.html', product_info=product_info, product_image_path=product_image_path)
    elif request.method == "POST":
        if 'add_to_cart' in request.form:
            new_item = Cart(client_id=current_user.id, item_id=product_id, product_amount=1)
            db.session.add(new_item)
            db.session.commit()
        elif 'buy_now' in request.form:
            final_cost = int_to_currency(product_info.cost)
            email_to_send = generate_email([{'product_info': product_info, 'amount': 1}], final_cost)
            with smtplib.SMTP(GMAIL_SEVER) as connection:
                connection.starttls()
                connection.login(user=MY_EMAIL, password=APP_PASSWORD)
                connection.sendmail(
                    from_addr=MY_EMAIL,
                    to_addrs=RECEIVERS_EMAIL,
                    msg=f"{email_to_send}"
                )
        elif 'add-to-favorites' in request.form:
            new_item = Favorite(client_id=current_user.id, item_id=product_id)
            db.session.add(new_item)
            db.session.commit()
        return render_template('product_page.html', product_info=product_info, product_image_path=product_image_path)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    global adding_new_address
    if request.method == 'POST':
        if 'logout' in request.form:
            logout_user()
            return redirect(url_for('homepage'))
        elif 'address-button' in request.form:
            adding_new_address = True
            redirect(url_for('profile'))
        elif 'checkable-address' in request.form:
            addresses = Address.query.filter_by(client_id=current_user.id)
            keys = list(request.form.keys())
            checked_address_id = int(keys[1])
            for address in addresses:
                if address.id != checked_address_id:
                    address.checked = False
                    db.session.add(address)
                    db.session.commit()
                else:
                    address.checked = True
                    db.session.add(address)
                    db.session.commit()
        elif 'save' in request.form:
            user_address = (f'{request.form.get("street-address")}, {request.form.get("city")},'
                            f' {request.form.get("parish")}')
            addresses = Address.query.filter_by(client_id=current_user.id).first()
            if addresses is None:
                new_address = Address(client_id=current_user.id, address=user_address, checked=True)
            else:
                new_address = Address(client_id=current_user.id, address=user_address, checked=False)
            db.session.add(new_address)
            db.session.commit()
            adding_new_address = False
            redirect(url_for('profile'))
        elif 'delete-button' in request.form:
            keys = list(request.form.keys())
            product_id = int(keys[1])
            delete_this_product = db.get_or_404(Address, product_id)
            db.session.delete(delete_this_product)
            db.session.commit()

    list_of_address = Address.query.filter_by(client_id=current_user.id)
    list_of_address = [address for address in list_of_address]
    return render_template('profile.html', addresses=list_of_address, new_address=adding_new_address)


@app.route('/favorites', methods=['GET', 'POST'])
@login_required
def favorites():
    cart_database = Favorite.query.filter_by(client_id=current_user.id)
    product_image_path = f'/static/Images/Product Images/'
    items_in_favorites = []
    for thing in cart_database:
        items_in_favorites.append(
            {'product_info': db.get_or_404(ProductInfo, thing.item_id)})

    if request.method == 'POST':
        if 'remove' in request.form:
            for item in items_in_favorites:
                item_to_remove = Favorite.query.filter_by(item_id=item['product_info'].id)
                for thing in item_to_remove:
                    if thing.client_id == current_user.id:
                        db.session.delete(thing)
                        db.session.commit()
        db.session.commit()
        return redirect(url_for('favorites'))
    return render_template('favorites.html', products_in_cart=items_in_favorites,
                           product_image_path=product_image_path)


@app.route('/cart/<int:product_id>', methods=['GET', 'POST'])
def cart(product_id):
    cart_database = Cart.query.filter_by(client_id=current_user.id)
    items_in_cart = []
    for thing in cart_database:
        items_in_cart.append(
            {'product_info': db.get_or_404(ProductInfo, thing.item_id), 'amount': thing.product_amount})
    product_image_path = f'/static/Images/Product Images/'
    cost_of_products = 0

    for item in items_in_cart:
        cost_of_products += item['product_info'].cost * item['amount']
    final_cost = int_to_currency(cost_of_products)

    if request.method == 'POST':
        if product_id > ZERO:
            if 'remove' in request.form:
                for item in items_in_cart:
                    item_to_remove = Cart.query.filter_by(item_id=item['product_info'].id)
                    for thing in item_to_remove:
                        if thing.client_id == current_user.id:
                            db.session.delete(thing)
                            db.session.commit()
            else:
                for item in items_in_cart:
                    item_amount_to_change = Cart.query.filter_by(item_id=item['product_info'].id)
                    for thing in item_amount_to_change:
                        if thing.client_id == current_user.id:
                            if 'increase' in request.form:
                                thing.product_amount += 1
                                db.session.add(thing)
                            elif 'decrease' in request.form:
                                thing.product_amount -= 1
                                db.session.add(thing)
                                if thing.product_amount == 0:
                                    db.session.delete(thing)
                db.session.commit()
            return redirect(url_for('cart', product_id=ZERO))
        elif product_id == ZERO:
            check_for_user_address = Address.query.filter_by(client_id=current_user.id).first()
            if check_for_user_address is None:
                flash('Please add and email to your profile before submitting order.')
            else:
                email_to_send = generate_email(items_in_cart, final_cost)
                with smtplib.SMTP(GMAIL_SEVER) as connection:
                    connection.starttls()
                    connection.login(user=MY_EMAIL, password=APP_PASSWORD)
                    connection.sendmail(
                        from_addr=MY_EMAIL,
                        to_addrs=RECEIVERS_EMAIL,
                        msg=f"{email_to_send}"
                    )
                    final_cost = "$00.00"
                    item_to_remove = db.session.execute(db.select(Cart)).scalars()
                    for thing in item_to_remove:
                        db.session.delete(thing)
                        db.session.commit()
            return redirect(url_for('cart', product_id=ZERO))
    if request.method == 'GET':
        return render_template('cart.html', product_id=ZERO,
                               products_in_cart=items_in_cart,
                               product_image_path=product_image_path, final_cost=final_cost)


def int_to_currency(final_cost):
    seperator_of_thousand = "."
    seperator_of_fraction = ","
    final_cost = "${:,.2f}".format(final_cost)
    if seperator_of_thousand == ".":
        main_currency, fractional_currency = final_cost.split(".")[0], final_cost.split(".")[1]
        new_main_currency = main_currency.replace(",", ".")
        currency = new_main_currency + seperator_of_fraction + fractional_currency
    return final_cost


def generate_email(items, final_cost):
    message_head = f"Subject: New Order!!!\n\n"
    message_client = f"Rachelle just requested a delivery for:\n\n"
    message_products = ""
    message_deliver_to = "\n\n\n Deliver To:  "
    for item in items:
        message_products += f"{item['product_info'].product_name}                   ${item['product_info'].cost}.00\n"

    addresses = Address.query.filter_by(client_id=current_user.id)
    for address in addresses:
        if address.checked:
            message_deliver_to += address.address
        else:
            continue

    message_total = f"\nTotal: {final_cost}"
    email_to_send = f"{message_head}{message_client}{message_products}{message_total}{message_deliver_to}"
    return email_to_send


@app.route('/modifier/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_only
def modifier(product_id):
    global new_product
    new_product = False
    product_image_path = (f"C:/Users/Demel/Documents/Python_Projects/"
                          f"Rachelle_Website/Beautiful Peaches/static/Images/Product Images")
    current_product = db.get_or_404(ProductInfo, product_id)

    if request.method == 'POST':
        if 'description' in request.form:
            if request.form.get('price').isalpha():
                flash('Please Enter Characters 0 - 9 only.')
            else:
                current_product.product_name = request.form.get('name')
                current_product.type = request.form.get('type')
                current_product.cost = request.form.get('price')
                current_product.description = request.form.get('description')
                db.session.add(current_product)
                db.session.commit()

            if os.path.isdir(f"{product_image_path}/{product_id}"):
                shutil.rmtree(f"{product_image_path}/{product_id}")
                images = [request.files['image1'], request.files['image2'],
                          request.files['image3'], request.files['image4']]
                store_product_image(current_product, images)

    return render_template('modifier.html', current_product=current_product)


@app.route('/new-product', methods=['GET', 'POST'])
@login_required
@admin_only
def create_new_product():
    global new_product
    new_product = True
    if request.method == 'POST':
        if request.form.get('price').find('$') != -1 or request.form.get('price').find('.') != -1:
            flash('Please Enter Characters 0 - 9 only.')
            return redirect(url_for('create_new_product'))
        else:
            product_info = ProductInfo(product_name=request.form.get('name'), type=request.form.get('type'),
                                       cost=request.form.get('price'), description=request.form.get('description'))
            db.session.add(product_info)
            db.session.commit()

            result = ProductInfo.query.filter_by(product_name=request.form.get('name')).first()
            images = [request.files['image1'], request.files['image2'], request.files['image3'],
                      request.files['image4']]
            store_product_image(result, images)
            return render_template('modifier.html', new_product=new_product)
    else:
        return render_template('modifier.html', new_product=new_product)


def store_product_image(current_product, images):
    os.mkdir(f'static/Images/Product Images/{current_product.id}')
    index = 1
    for image in images:
        filename = secure_filename(image.filename)
        image.save(os.path.join(f'static/Images/Product Images/{current_product.id}', filename))
        os.rename(src=f'static/Images/Product Images/{current_product.id}/{filename}',
                  dst=f'static/Images/Product Images/{current_product.id}/{index}.jpg')
        index += 1


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def refactor_database(product_image_path):
    keys = list(request.form.keys())
    product_id = int(keys[1])
    if os.path.isdir(f"{product_image_path}/{product_id}"):
        shutil.rmtree(f"{product_image_path}/{product_id}")
        delete_this_product = db.get_or_404(ProductInfo, product_id)
        db.session.delete(delete_this_product)
        db.session.commit()

        item_to_remove = Cart.query.filter_by(item_id=product_id)
        for thing in item_to_remove:
            if thing.item_id == product_id:
                db.session.delete(thing)
                db.session.commit()

        products = db.session.execute(db.select(ProductInfo).order_by(ProductInfo.id)).scalars()
        amount_of_image_folders_left = check_amount_of_folders(product_image_path)
        folders = [entry for entry in os.listdir(product_image_path)
                   if os.path.isdir(os.path.join(product_image_path, entry))]
        i = 1

        for index in range(amount_of_image_folders_left):
            if amount_of_image_folders_left > 0:
                os.rename(f"{product_image_path}/{folders[index]}", f"{product_image_path}/{index + 1}")
                for item in products:
                    item.id = i
                    db.session.add(item)
                    db.session.commit()
                    i += 1


def check_amount_of_folders(product_image_path):
    return len([entry for entry in os.listdir(product_image_path)
                if os.path.isdir(os.path.join(product_image_path, entry))])


if __name__ == '__main__':
    app.run(debug=True)
