from flask import request, jsonify, current_app as app, url_for
from . import api
from ..models import Post, User


# to get users
@api.route('/users/<int:id>')
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())

@api.route('/users/<int:id>/posts/')
def get_user_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page',1,type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page=page,per_page=int(app.config['NKBLOG_POSTS_PER_PAGE']), error_out=False
    )
    posts = pagination.items
    prev = None
    
    if pagination.has_prev:
        prev = url_for('api.get_user_posts',id=id,page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_posts',id=id,page=page+1)

    return jsonify({
        'posts':[post.to_json() for post in posts],
        'prev_url':prev,
        'next_url':next,
        'count':pagination.total})

@api.route('/users/<int:id>/timeline/')
def get_user_followed_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page',1,type=int)
    pagination = user.followed_posts.order_by(Post.timestamp.desc()).paginate(
        page=page,per_page=int(app.config['NKBLOG_POSTS_PER_PAGE']), error_out=False
    )
    posts = pagination.items
    prev = None
    
    if pagination.has_prev:
        prev = url_for('api.get_user_followed_posts',id=id,page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_followed_posts',id=id,page=page+1)

    return jsonify({
        'posts':[post.to_json() for post in posts],
        'prev_url':prev,
        'next_url':next,
        'count':pagination.total})