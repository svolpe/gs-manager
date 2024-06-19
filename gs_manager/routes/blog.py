from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.users import User
from ..models.blog import Post


bp = Blueprint('blog', __name__)


@bp.route('/blog')
def index():
    query = db.session.query(
        User.id, Post.title, Post.body, Post.created, Post.author_id, Post.id, User.user_name
    ).join(User, Post.author_id == User.id).order_by(Post.created.desc())

    return render_template('blog/index.html', posts=query)


@bp.route('/blog/create', methods=('GET', 'POST'))
# @login_required
def create():
    """Create a new blog entry"""

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            post = Post(title=title, body=body, author_id=g.user.id)
            db.session.add(post)
            db.session.commit()

            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')


def get_post(id, check_author=True):

    post = db.session.query(
        User.id, Post.title, Post.body, Post.created, Post.author_id, Post.id, User.user_name
    ).join(User, Post.author_id == User.id).filter(Post.id == id).first()


    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

#    if check_author and (post.id != g.user['id']):
#        abort(403)

    return post


@bp.route('/blog/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            post = update(Post).where(Post.author_id == g.user['id']).values(title=title, body=body)
            post.verified = True
            db.session.commit()

            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    Post.query.filter(Post.id == id).delete()
    db.session.commit()
    return redirect(url_for('blog.index'))

