from datetime import datetime
from flask import render_template, session, redirect, url_for, flash, request, make_response
from . import main
from .. import db
from .forms import NameForm, EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from ..models import User, Role, Permission, Post, Comment
from ..email import send_mail
from flask import current_app as app, abort
from flask_login import login_required, current_user
from ..decorators import admin_required, permission_required

@main.route('/',methods=['GET','POST'])
def index():
    # form = NameForm()
    # if form.validate_on_submit():
    #     user = User.query.filter_by(username=form.name.data).first()
    #     if user is None:
    #         user = User(username=form.name.data)
    #         db.session.add(user)
    #         db.session.commit()
    #         session['known'] = False
    #         if app.config['NKBLOG_ADMIN']:
    #             send_mail(app.config['NKBLOG_ADMIN'],'New User', 'Mail/new_user',user=user)
    #             print("mail sent successfully.")
    #         else:
    #             print("--no admin mail--")

    #     else:
    #         session['known'] = True
    #     session['name'] = form.name.data
    #     form.name.data = ''
    
    form = PostForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        post = Post(body=form.body.data, author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()

        return redirect(url_for('.index'))
    
    # posts = Post.query.order_by(Post.timestamp.desc()).all()
    # paginating
    page = request.args.get('page',1,type=int)

    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed',''))

    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query

    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=int(app.config['NKBLOG_POSTS_PER_PAGE']),error_out=False
    )
    posts = pagination.items

    return render_template('index.html',form=form, posts=posts,Permission=Permission,
                           show_followed=show_followed, pagination=pagination)

# function to perform logic for user profile and its posts.
@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user is None:
        abort(404)
    
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html',user=user,posts=posts,Permission=Permission)


# function to edit profile of user
@main.route('/edit-profile',methods=['GET','POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user',username=current_user.username, Permission=Permission))
    
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html',form=form,Permission=Permission)

# function to edit profile if user is admin.
@main.route('/edit-profile/<int:id>',methods=['GET','POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('Profile has be updated')
        return redirect(url_for('.user',username=user.username, Permission=Permission))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html',form=form,user=user,Permission=Permission)


# function to generate permanent link for posts.
@main.route('/post/<int:id>', methods=['GET','POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        
        db.session.add(comment)
        db.session.commit()
        flash('You comment has been published.')
        return redirect(url_for('.post',id=post.id,page=-1))
    page = request.args.get('page',1,type=int)
    if page==-1:
        page = (post.comments.count() - 1 )// int(app.config['NKBLOG_COMMENTS_PER_PAGE']) + 1
    
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page=page,per_page=int(app.config['NKBLOG_COMMENTS_PER_PAGE']),
        error_out=False
    )
    comments = pagination.items
    return render_template('post.html',posts=[post],form=form,comments=comments,pagination=pagination, Permission=Permission)


# function to edit posts in db and render the template to edit the post.
@main.route('/edit/<int:id>',methods=['GET','POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        abort(403)

    form = PostForm()

    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()

        flash('The post has been updated')
        return redirect(url_for('.post',id=post.id))
    
    form.body.data = post.body
    return render_template('edit_post.html',form=form,Permission=Permission)


# Functio to perform follow logic.
@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user',username=username))
    current_user.follow(user)
    db.session.commit()
    flash(f'You are now following {username}.')
    return redirect(url_for('.user',username=username))

# function to perform unfollow logic
@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    
    if current_user.is_following(user):
        current_user.unfollow(user)
        db.session.commit()
        flash(f'You have unfollowed {username}.')
        return redirect(url_for('.user',username=username))
    
    flash("You are not following this user.")
    return redirect(url_for('.user',username=username))

# function to get all followers list.
@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    
    page = request.args.get('page',1,type=int)
    pagination = user.followers.paginate(
        page=page, per_page= int(app.config['NKBLOG_POSTS_PER_PAGE']),
        error_out=False
    )

    follows = [{'user':item.follower, 'timestamp':item.timestamp}
               for item in pagination.items]
    
    return render_template('followers.html',user=user,title="Followers of",endpoint='.followers',
                           pagination=pagination,follows=follows,Permission=Permission)


# function to get all following list
@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    
    page = request.args.get('page',1,type=int)
    pagination = user.followed.paginate(
        page=page, per_page= int(app.config['NKBLOG_POSTS_PER_PAGE']),
        error_out = False
    )
    follows = [{'user':item.followed,'timestamp':item.timestamp}
               for item in pagination.items]
    return render_template('followers.html',user=user,title="Following of",endpoint='.followed_by',
                           pagination=pagination,follows=follows,Permission=Permission)

# function to set cookie value for all posts.
@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60) # for 30 days.
    return resp

# function set cookie value for followed posts.
@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed','1',max_age=30*24*60*60) # for 30 days
    return resp

# function to moderate comments
@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page',1,type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page=page,per_page=int(app.config['NKBLOG_COMMENTS_PER_PAGE']),
        error_out=False
    )
    comments = pagination.items
    return render_template('moderate.html',comments=comments, pagination=pagination, page=page, Permission=Permission)

# function to set enable comment
@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled=False
    db.session.add(comment)
    return redirect(url_for('.moderate',page=request.args.get('page',1,type=int)))

# function to set disable comment
@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled=True
    db.session.add(comment)
    return redirect(url_for('.moderate',page=request.args.get('page',1,type=int)))