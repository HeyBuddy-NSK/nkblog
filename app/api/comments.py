from app.models import User, Post, Comment, Permission
from . import api
from .decorators import permission_required
from flask import jsonify, request, g, url_for, current_app as app
from app import db


# function to get single comment
@api.route('/comments/<int:id>')
def get_comment(id):
    comment = Comment.query.get_or_404(id)
    return jsonify(comment.to_json())

# function to write new comment through api
@api.route('/posts/<int:id>/comments',methods=['POST'])
@permission_required(Permission.COMMENT)
def new_comment(id):
    post = Post.query.get_or_404(id)
    comment = Comment.from_json(request.json)
    comment.author = g.current_user
    comment.post = post
    db.session.add(comment)
    db.session.commit()

    return jsonify(comment.to_json()), 201, {'Location':url_for('api.get_comment',id=comment.id)}


# method to get comments for posts
@api.route('/posts/<int:id>/comments')
def get_post_comments(id):
    post = Post.query.get_or_404(id)

    # pagination
    page = request.args.get('page',1,type=int) 
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page=page,per_page=int(app.config['NKBLOG_COMMENTS_PER_PAGE']), error_out=False
    )
    
    # getting all comments
    comments = pagination.items
    
    # pagination for previous and next page
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_post_comments',id=id,page=page-1)
    
    next = None
    if pagination.has_next:
        next = url_for('api.get_post_comments',id=id,page=page+1)

    return jsonify({
        'comments':[comment.to_json() for comment in comments],
        'prev':prev,
        'next':next,
        'count':pagination.total
    })


# method to get all comments
@api.route('/comments/')
def get_comments():
    page = request.args.get('page',1,type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page=page,per_page=int(app.config['NKBLOG_COMMENTS_PER_PAGE']),error_out=False
    )

    comments = pagination.items

    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_comments',page=page-1)
    
    next = None
    if pagination.has_next:
        next = url_for('api.get_comments',page=page+1)

    return jsonify({
        'comments':[comment.to_json() for comment in comments],
        'prev':prev,
        'next':next,
        'count':pagination.total
    })