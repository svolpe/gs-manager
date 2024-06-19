import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from ..extensions import db
from ..models.users import User

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    """
    This view is used to register a new user
    """
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.session.query(User.id).filter_by(user_name=username).first() is not None:
            error = 'User {} is already registered.'.format(username)
        if error is None:
            user = User(user_name=username, password=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    """
    This view does the following:
        1.) Lets the user log in
        2.) Stores user's ID in a new session
        3.) Stores data in a cookie and sends it to the client browser and
        then the browser then sends it back with subsequent requests
        Flask securely signs the data so that it can't be tampered with
    """

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        error = None
        user = User.query.filter_by(user_name=username).first()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user.password, password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user.id
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    """
    This function is called before any URL request to this site. It then
    checks if the user ID is stored in the session and gets the user data
    from the database storing it on g.user
    """

    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = db.session.query(User.id).filter_by(id=user_id).first()


@bp.route('/logout')
def logout():
    """
    This view logs out the user
    """

    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    """
    This decorator returns a new view function that wraps the original view it’s applied to.
    The new function checks if a user is loaded and redirects to the login page otherwise.
    If a user is loaded the original view is called and continues normally.
    You’ll use this decorator when writing the blog views.
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

