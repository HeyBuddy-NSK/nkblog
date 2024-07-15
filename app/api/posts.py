from . import api
from app import db
from ..models import Post, Permission
from flask import jsonify, request, g, url_for, current_app as app
from .decorators import permission_required
from .errors import forbidden

# method to get all posts
@api.route('/posts/')
def get_posts():
    page = request.args.get('page',1,type=int)
    pagination = Post.query.paginate(
        page=page,per_page=int(app.config['NKBLOG_POSTS_PER_PAGE']), error_out=False
    )
    posts = pagination.items
    prev = None
    
    if pagination.has_prev:
        prev = url_for('api.get_posts',page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_posts',page=page+1)

    return jsonify({
        'posts':[post.to_json() for post in posts],
        'prev_url':prev,
        'next_url':next,
        'count':pagination.total})

# method to get single blog post.
@api.route('/posts/<int:id>')
def get_post(id):
    post = Post.query.get_or_404(id)
    return jsonify(post.to_json())


# method to create new post. (resource handler)
@api.route('/posts/',methods=['POST'])
@permission_required(Permission.WRITE)
def new_post():
    post = Post.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    db.session.commit()

    return jsonify(post.to_json()), 201, {'Location':url_for('api.get_post',id=post.id)}

# method to handle editing posts.
@api.route('/posts/<int:id>',methods=['PUT'])
@permission_required(Permission.WRITE)
def edit_post():
    post = Post.query.get_or_404(id)
    if g.current_user != post.author and not g.current_user.can(Permission.ADMIN):
        return forbidden('Insuffiecient Permissions')
    
    post.body = request.json.get('body',post.body)
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())

