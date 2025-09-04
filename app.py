from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wags_global.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    wallet_balance = db.Column(db.Float, default=0.0)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)


# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(100), default='default-product.jpg')
    category = db.Column(db.String(50), default='general')
    cart_items = db.relationship('CartItem', backref='product', lazy=True)


# Cart Item Model
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


# Helper function to get current user
def get_current_user():
    """Get the current user from session or return None if not logged in or user doesn't exist"""
    if 'user_id' not in session:
        return None

    user = db.session.get(User, session['user_id'])
    if user is None:
        # User doesn't exist anymore - clear session
        session.clear()

    return user


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(user, *args, **kwargs)

    return decorated_function


# Get cart item count for navbar
def get_cart_count():
    user = get_current_user()
    if user:
        cart_count = db.session.query(db.func.sum(CartItem.quantity)).filter_by(user_id=user.id).scalar()
        return cart_count or 0
    return 0


# Get cart total for context processor
def get_cart_total():
    user = get_current_user()
    if user:
        cart_items = db.session.query(CartItem, Product).join(Product).filter(CartItem.user_id == user.id).all()
        cart_total = sum(item.Product.price * item.CartItem.quantity for item in cart_items)
        return cart_total
    return 0


# Make cart_count and cart_total available to all templates
@app.context_processor
def inject_cart_data():
    return dict(cart_count=get_cart_count(), cart_total=get_cart_total())


# Create tables
with app.app_context():
    db.create_all()

    # Add sample products if none exist
    if not db.session.query(Product).first():
        sample_products = [
            # Health & Wellness Products
            Product(
                name="CONFO BALM",
                description="Refined fragrant herbal extract balm with 20 years of experience. Soothing relief for muscle aches and pains.",
                price=12.99,
                image="CUNFU5.jpg",
                category="health"
            ),
            Product(
                name="CANFOR Essential Oil",
                description="Pure essential oil from SINO CONFO GROUP LIMITED. Perfect for aromatherapy and relaxation.",
                price=18.50,
                image="CUNFU6.jpg",
                category="health"
            ),
            Product(
                name="SylFlora Botanical Serum",
                description="Natural botanical serum for skin rejuvenation. Tech-infused formula for maximum effectiveness.",
                price=24.99,
                image="SYLFLORA1.jpg",
                category="beauty"
            ),
            Product(
                name="Mornings TechO Supplement",
                description="Daily wellness supplement to boost your morning routine. Enhanced with natural ingredients.",
                price=29.99,
                image="SYLFLORA3.jpg",
                category="health"
            ),

            # Additional products to fill out the shop
            Product(
                name="Premium Service Package",
                description="Our premium service package includes everything you need for business success. With 24/7 support and advanced features.",
                price=199.99,
                image="https://via.placeholder.com/300x200?text=Product+1",
                category="service"
            ),
            Product(
                name="Business Solution Suite",
                description="Comprehensive business solutions for enterprises of all sizes. Includes analytics, reporting, and integration capabilities.",
                price=349.99,
                image="https://via.placeholder.com/300x200?text=Product+2",
                category="service"
            ),
            Product(
                name="Global Connectivity Plan",
                description="Stay connected globally with our connectivity plan. Includes high-speed access and secure connections worldwide.",
                price=149.99,
                image="https://via.placeholder.com/300x200?text=Product+3",
                category="service"
            ),
            Product(
                name="Executive Support Package",
                description="Priority support and consultation services for executives. Personalized solutions for your business needs.",
                price=499.99,
                image="https://via.placeholder.com/300x200?text=Product+4",
                category="service"
            )
        ]

        for product in sample_products:
            db.session.add(product)

        db.session.commit()


# Routes
@app.route('/')
def index():
    featured_products = db.session.query(Product).filter(Product.category.in_(['health', 'beauty'])).limit(3).all()
    return render_template('index.html', featured_products=featured_products)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/shop')
def shop():
    category = request.args.get('category', 'all')

    if category == 'all':
        products = db.session.query(Product).all()
    else:
        products = db.session.query(Product).filter_by(category=category).all()

    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0] is not None]

    return render_template('shop.html', products=products, categories=categories, current_category=category)


@app.route('/wallet')
@login_required
def wallet(user):
    return render_template('wallet.html', user=user)


@app.route('/cart')
@login_required
def cart(user):
    cart_items = db.session.query(CartItem, Product).join(Product).filter(CartItem.user_id == user.id).all()
    total = sum(item.Product.price * item.CartItem.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total, user=user)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(user, product_id):
    product = db.session.get(Product, product_id)
    if not product:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Product not found'})
        flash('Product not found', 'error')
        return redirect(url_for('shop'))

    # Check if product is already in cart
    cart_item = db.session.query(CartItem).filter_by(user_id=user.id, product_id=product_id).first()

    if cart_item:
        # Update quantity
        cart_item.quantity += 1
    else:
        # Add new item to cart
        cart_item = CartItem(user_id=user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()

    # Calculate updated cart totals
    cart_count = db.session.query(db.func.sum(CartItem.quantity)).filter_by(user_id=user.id).scalar() or 0
    cart_items = db.session.query(CartItem, Product).join(Product).filter(CartItem.user_id == user.id).all()
    cart_total = sum(item.Product.price * item.CartItem.quantity for item in cart_items)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'{product.name} added to cart!',
            'cart_count': cart_count,
            'cart_total': cart_total
        })

    flash(f'{product.name} added to cart!', 'success')
    return redirect(request.referrer or url_for('shop'))


@app.route('/update_cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(user, item_id):
    cart_item = db.session.get(CartItem, item_id)

    if not cart_item or cart_item.user_id != user.id:
        flash('Item not found in your cart', 'error')
        return redirect(url_for('cart'))

    action = request.form.get('action')

    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1
    elif action == 'remove':
        db.session.delete(cart_item)

    db.session.commit()
    flash('Cart updated successfully', 'success')
    return redirect(url_for('cart'))


@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart(user):
    db.session.query(CartItem).filter_by(user_id=user.id).delete()
    db.session.commit()
    flash('Cart cleared successfully', 'success')
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['POST'])
@login_required
def checkout(user):
    cart_items = db.session.query(CartItem, Product).join(Product).filter(CartItem.user_id == user.id).all()

    if not cart_items:
        flash('Your cart is empty', 'error')
        return redirect(url_for('cart'))

    total = sum(item.Product.price * item.CartItem.quantity for item in cart_items)

    if user.wallet_balance < total:
        flash('Insufficient funds in your wallet', 'error')
        return redirect(url_for('cart'))

    # Process payment
    user.wallet_balance -= total

    # Clear cart
    db.session.query(CartItem).filter_by(user_id=user.id).delete()

    db.session.commit()

    flash(f'Order placed successfully! ${total:.2f} deducted from your wallet.', 'success')
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = db.session.query(User).filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')

        if db.session.query(User).filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')

        if db.session.query(User).filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.route('/add_funds', methods=['POST'])
@login_required
def add_funds(user):
    amount = float(request.form['amount'])

    user.wallet_balance += amount
    db.session.commit()

    flash(f'${amount} has been added to your wallet', 'success')
    return redirect(url_for('wallet'))


if __name__ == '__main__':
    app.run(debug=True)