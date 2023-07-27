from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import requests
import os
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reciplanner.db'
db = SQLAlchemy(app)


migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

spoon_api_key= os.environ.get('SPOON_API')

class DietaryRestrictions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    diet = db.Column(db.String(200), nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    dietary_restrictions = db.relationship('DietaryRestrictions', backref='user', lazy=True)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        user_id = current_user.id
        dietary_restrictions = DietaryRestrictions.query.filter_by(user_id=user_id).all()
        user_diets = [dr.diet for dr in dietary_restrictions]
        return render_template('home.html', name=current_user.username, user_diets=user_diets)
    else:
        return render_template('home.html', name="Guest")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken. Please choose a different one.', 'error')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('User Created Successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger'), 401
            return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/update-dietary-restrictions', methods=['POST'])
@login_required
def update_dietary_restrictions():
    data = request.form.getlist('diet')
    user_id = current_user.id
    
    # delete current dietary restrictions
    DietaryRestrictions.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    
    # add new dietary restrictions
    for diet in data:
        dr = DietaryRestrictions(user_id=user_id, diet=diet)
        db.session.add(dr)
    db.session.commit()
    
    flash('Dietary restrictions updated successfully!', 'success')
    return redirect(url_for('search_by_ingredients'))

@app.route('/favorite-recipe', methods=['POST'])
@login_required
def favorite_recipe():
    recipe_id = request.form.get('id')
    recipe_title = request.form.get('title')
    recipe_image = request.form.get('image')
    user_id = current_user.id

    existing_recipe = Recipe.query.filter_by(id=recipe_id, user_id=user_id).first()

    if existing_recipe is None:
        recipe = Recipe(id=recipe_id, title=recipe_title, image=recipe_image, user_id=user_id)
        db.session.add(recipe)
        db.session.commit()
        flash('Recipe saved successfully!')
    else:
        flash('This recipe is already in your favorites')

    return redirect(url_for('get_favorites'))

@app.route('/search-recipes')
@login_required
def search_recipes():
    return render_template('search_recipes.html')

@app.route('/search-by-ingredients', methods=['GET', 'POST'])
@login_required
def search_by_ingredients():
    user_id = current_user.id
    dietary_restrictions = DietaryRestrictions.query.filter_by(user_id=user_id).all()
    user_diets = [dr.diet for dr in dietary_restrictions]
    if request.method == 'POST':
        ingredients = request.form.get('ingredients')
        url = f"https://api.spoonacular.com/recipes/findByIngredients?ingredients={ingredients}&number=50&ranking=1&ignorePantry=true&diet={','.join(user_diets)}&apiKey={spoon_api_key}"
        response = requests.get(url)
        recipes = response.json()
        return render_template('search_by_ingredients.html', recipes=recipes, user_diets=user_diets)
    
    return render_template('search_by_ingredients.html', user_diets=user_diets)

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form['search']
    user_id = current_user.id
    dietary_restrictions = DietaryRestrictions.query.filter_by(user_id=user_id).all()
    user_diets = [dr.diet for dr in dietary_restrictions]

    api_url = f"https://api.spoonacular.com/recipes/complexSearch?query={search_query}&number=50&diet={','.join(user_diets)}&apiKey={spoon_api_key}"
    response = requests.get(api_url)

    # Handle the case where the API request fails
    if response.status_code != 200:
        flash('There was an error processing your request. Please try again.', 'error')
        return redirect(url_for('home'))

    data = response.json()
    recipes = data.get('results', [])
    
    return render_template('recipe_results.html', recipes=recipes, user_diets=user_diets)

@app.route('/search-by-category', methods=['GET', 'POST'])
@login_required
def search_by_category():
    user_id = current_user.id
    dietary_restrictions = DietaryRestrictions.query.filter_by(user_id=user_id).all()
    user_diets = [dr.diet for dr in dietary_restrictions]
    recipes = []

    if request.method == 'POST':
        category = request.form.get('category')
        url = f"https://api.spoonacular.com/recipes/complexSearch?query={category}&number=50&diet={','.join(user_diets)}&apiKey={spoon_api_key}"
        response = requests.get(url)
        recipes = response.json().get('results', [])
        print(response.status_code)
        print(recipes)
    return render_template('search_by_category.html', recipes=recipes, user_diets=user_diets)

@app.route('/recipe-detail/<int:recipe_id>')
@login_required
def recipe_detail(recipe_id):
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information?includeNutrition=true&apiKey={spoon_api_key}"
    response = requests.get(url)
    recipe = response.json()
    
    return render_template('recipe_detail.html', recipe=recipe)

@app.route('/remove-favorite', methods=['POST'])
@login_required
def remove_favorite():
    recipe_id = request.form.get('id')
    recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    
    if recipe:
        db.session.delete(recipe)
        db.session.commit()
        flash('Recipe removed from your favorites.')
    else:
        flash('Recipe not found in your favorites.')

    return redirect(url_for('get_favorites'))

@app.route('/get-favorites')
@login_required
def get_favorites():
    user_id = current_user.id
    recipes = Recipe.query.filter_by(user_id=user_id).all()
    user_diets = [dr.diet for dr in current_user.dietary_restrictions]
    return render_template('favorites.html', recipes=recipes, user_diets=user_diets)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
