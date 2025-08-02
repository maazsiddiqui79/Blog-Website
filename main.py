# Import necessary modules
from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash , request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user , login_required
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm
import smtplib
from datetime import datetime

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app=app)

# Set up Flask-Login manager
login_manger = LoginManager()
login_manger.init_app(app=app)
login_manger.login_view = 'login'

# Define BlogPost model for blog posts table
class BlogPost(db.Model,UserMixin):
    __tablename__ = "blog_post"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    users_email = db.Column(db.String(250), nullable=False)

# Define User_Comment model for comments table
class User_Comment(db.Model,UserMixin):
    __tablename__ = "user_comment"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    POST_ID = db.Column(db.Integer, nullable=False)

# Define Users_DATABASE model for registered users table
class Users_DATABASE(db.Model,UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    hashed_password = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    created_on = db.Column(db.String(250), nullable=False)

# User loader callback for Flask-Login 
@login_manger.user_loader
def load_user(user_id):
    return Users_DATABASE.query.get(int(user_id))


# Create all tables in the database
with app.app_context():
    db.create_all()

# Route to handle user registration
@app.route('/register', methods=['GET','POST'])
def register():
    
    created_ = datetime.now()
    created_.strftime("%B %d, %Y at %I:%M %p") 
    
    if request.method == 'POST':
        u_name = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password=password,method='pbkdf2:sha256',salt_length=8)
        exist_user = Users_DATABASE.query.filter_by(email=email).first()
        if exist_user:
            flash('A user with this email already exists. Please log in instead.', 'danger')
        else:
            new_user = Users_DATABASE(username=u_name,
                                      email=email,
                                      hashed_password=hashed_password,
                                      password=password,
                                      created_on=created_)
            try:
                db.session.add(new_user)
                db.session.commit()
                login_user(user=new_user)
                posts = BlogPost.query.all()
                return redirect(url_for('get_all_posts',logged_in = current_user.is_authenticated,all_posts=posts))
            except Exception:
                db.session.rollback()
                flash('An unexpected error occurred during registration. Please try again later.', 'danger')
    return render_template("register.html",logged_in = current_user.is_authenticated)

# Route to handle user login
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = Users_DATABASE.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.hashed_password,password):
                login_user(user=user)
                posts = BlogPost.query.all()
                return redirect(url_for('get_all_posts',logged_in = current_user.is_authenticated,all_posts=posts))
            else:
                flash('Incorrect password. Please try again.', 'warning')
        else:
            flash('No account found with that email. Please register first.', 'danger')
    return render_template("login.html",logged_in = current_user.is_authenticated)

# Route to handle user logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

# Route to display all blog posts
@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts,logged_in = current_user.is_authenticated)

# Route to display individual blog post and handle comments
@app.route("/post/<int:post_id>",methods=['GET','POST'])
def show_post(post_id):
    all_cmt = User_Comment.query.all()
    requested_post = db.get_or_404(BlogPost, post_id)
    if request.method == 'POST':
        cmt = request.form.get('comment')
        author_name = current_user.username
        dates = date.today().strftime("%B %d, %Y")
        p_id = post_id
        new_cmt = User_Comment(body=cmt,author=author_name,date=dates,POST_ID=p_id)
        try:
            db.session.add(new_cmt)
            db.session.commit()
        except Exception:
            flash("Unable to post your comment at this time. Please try again later.", 'danger')
        all_cmt = User_Comment.query.all()
        return redirect(url_for('show_post', post=requested_post,logged_in = current_user.is_authenticated , post_id=post_id,all_cmt=all_cmt))
    return render_template("post.html", post=requested_post,logged_in = current_user.is_authenticated , post_id=post_id,all_cmt=all_cmt)

# Route to create a new blog post (admin only)
@app.route("/new-post", methods=["GET", "POST"])
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        existing_post = BlogPost.query.filter_by(title=form.title.data).first()
        if existing_post:
            flash("A post with this title already exists. Please use a different title.", "warning")
            return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.username,
            date=date.today().strftime("%B %d, %Y"),
            users_email=current_user.email
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts", logged_in=current_user.is_authenticated))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)

# Route to edit a blog post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id,logged_in = current_user.is_authenticated))
    return render_template("make-post.html", form=edit_form, is_edit=True,logged_in = current_user.is_authenticated)


@app.route("/account/", methods=["GET", "POST"])
@login_required
def account():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("account.html",current_user=current_user,logged_in = current_user.is_authenticated,all_post=posts)

# Route to delete a blog post (admin only)
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts',logged_in = current_user.is_authenticated))


# Route to render the about page
@app.route("/about")
def about():
    return render_template("about.html",logged_in = current_user.is_authenticated)

# Route to render the contact page and send contact form details via email
@app.route("/contact",methods=['GET','POST'])
def contact():
    if request.method =='POST':
        print("ON CONTACT PAGE")
        name = request.form['name']
        email_id = request.form['email']
        phone_no = request.form['phone']
        message = request.form['message']
        sender_mail = "maaz.irshad.siddiqui@gmail.com"
        password ="tvud sggg rdle ywll"
        message = f"""Subject: Assalamualaikum

    You’ve received a new message from your website contact form.

    New User Registered
    Name: {name}
    Email: {email_id}
    Phone No: {phone_no}

    Message:
    {message}

    ---

    This message was sent via the contact form on your portfolio/blog site.
    Please respond at your earliest convenience.
    """
        with smtplib.SMTP_SSL("smtp.gmail.com",port=465) as connection:
                connection.login(user=sender_mail,password=password)
                connection.sendmail(
                    from_addr=sender_mail,
                    to_addrs='siddiqui.maaz79@gmail.com',
                    msg=message.encode("utf-8")
                )
        print("Mail Sent")
        return render_template('successful_form_delivered.html',logged_in = current_user.is_authenticated)
    return render_template("contact.html",logged_in = current_user.is_authenticated)


@app.route('/all-user-in-db')
def all_users():
    data  = Users_DATABASE.query.all()
    return render_template('all_users.html',data=data)

# Run the Flask application
if __name__ == "__main__":
    app.run(debug=True, port=5002)
