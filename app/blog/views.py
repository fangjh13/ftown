# -*- coding: utf-8 -*-

import os
from datetime import date
from flask import render_template, request, flash, redirect, url_for, abort, session, g, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import cast, Date
from app import db
from app.blog.captcha import generate_captcha_image
from . import blog
from .forms import WriteForm, CommentForm, CommentOpenForm, SearchForm
from ..email import send_mail
from ..models import User, Post, Comment, Tag
from .qiniu_ftown import upload_picture


# Blog background management authentication
# from flask_httpauth import HTTPBasicAuth
# auth = HTTPBasicAuth()
#
# @auth.verify_password
# def verify_pswd(username, password):
#     # blog administrator is `BlogAdmin`
#     if username == 'BlogAdmin':
#         blogadmin = User.query.filter_by(username='BlogAdmin').first_or_404()
#         if blogadmin.verify_password(password):
#             return True
#     return False


@blog.before_app_request
def before_request():
    g.search_form = SearchForm()



@blog.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    # flask-SQLAlchemy Pagination
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, 4, error_out=False)
    posts = pagination.items
    return render_template('/blog/home.html', posts=posts,
                           pagination=pagination, endpoint='blog.home')


@blog.route('/about')
def about():
    return render_template('/blog/about.html')


@blog.route('/post/<username>')
def user_post(username):
    page = request.args.get('page', 1, type=int)
    u = User.query.filter_by(username=username).first_or_404()
    pagination = Post.query.filter_by(author=u
                                      ).order_by(Post.timestamp.desc()).paginate(
        page, 4, error_out=False)
    posts = pagination.items
    return render_template('/blog/home.html', posts=posts,
                           pagination=pagination, endpoint='blog.user_post',
                           username=username)


@blog.route('/post', methods=['GET', 'POST'])
def post():
    post = Post.query.order_by(Post.timestamp.desc()).first_or_404()
    form = CommentForm()
    if form.validate_on_submit():
        content = form.content.data
        c = Comment(body=content, author=current_user, post=post)
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('blog.post')+'#comment')
    comments = post.comments.all()
    count = post.comments.count()
    post.views += 1
    db.session.add(post)
    db.session.commit()
    open_form = CommentOpenForm()
    if current_app.config['TESTING']:
        # for unit test
        code, captcha_b64 = generate_captcha_image('abcd')
    else:
        code, captcha_b64 = generate_captcha_image()
    return render_template('/blog/post.html', post=post, form=form,
                           captcha_b64=captcha_b64, comments=comments,
                           count=count, open_form=open_form)


@blog.route('/post/open-comment/<int:post_id>', methods=['POST'])
def open_comment(post_id):
    post = Post.query.get_or_404(post_id)
    y, m, d = post.timestamp.year, post.timestamp.month, post.timestamp.day
    brief_title = post.brief_title
    open_form = CommentOpenForm()
    if open_form.validate_on_submit():
        if (not session.get('code')) or (session['code'] != open_form.open_captcha.data.upper()):
            flash('验证码错误，请重新填写')
            return redirect(url_for('.post_brief', y=y, m=m, d=d,
                                    brief_title=brief_title) + '#alert-message')
        content = open_form.open_content.data
        open_name = open_form.open_name.data
        open_email = open_form.open_email.data
        anonymous_user = User(name=open_name, incog_email=open_email,
                              anonymous=True)
        c = Comment(body=content, author=anonymous_user, post=post)
        db.session.add_all([anonymous_user, c])
        db.session.commit()
        # send remind email when comment
        subject = '[SOMEONE COMMENT] someone comment your posts.[OPEN COMMENT]'
        addr = url_for('.onepost', post_id=post.id, _external=True)
        send_mail(subject,
                  "Blog Admin <{0}>".format(os.environ.get('MAIL_USERNAME')),
                  recipients=[post.author.email],
                  prefix_template='/mail/comment_remind',
                  addr=addr, content=content)
        return redirect(url_for('.post_brief', y=y, m=m, d=d,
                                brief_title=brief_title)+'#comment')
    flash('信息填写错误，请重新填写！')
    return redirect(url_for('.post_brief', y=y, m=m, d=d,
                            brief_title=brief_title)+'#alert-message')


@blog.route('/post/<int:post_id>', methods=['GET', 'POST'])
def onepost(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        content = form.content.data
        c = Comment(body=content, author=current_user, post=post)
        db.session.add(c)
        db.session.commit()
        # send remind email when comment
        subject = '[SOMEONE COMMENT] someone comment your posts.'
        addr = url_for('.onepost', post_id=post_id, _external=True)
        send_mail(subject,
                  "Blog Admin <{0}>".format(os.environ.get('MAIL_USERNAME')),
                  recipients=[post.author.email],
                  prefix_template='/mail/comment_remind',
                  addr=addr, content=content)
        return redirect(url_for('.onepost', post_id=post.id)+'#comment')
    comments = post.comments.all()
    count = post.comments.count()
    post.views += 1
    db.session.add(post)
    db.session.commit()
    open_form = CommentOpenForm()
    if current_app.config['TESTING']:
        # for unit test
        code, captcha_b64 = generate_captcha_image('abcd')
    else:
        code, captcha_b64 = generate_captcha_image()
    return render_template('/blog/post.html', post=post, form=form,
                           comments=comments, count=count, open_form=open_form,
                           captcha_b64=captcha_b64, code=''.join(code))


@blog.route('/contact', methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        form = request.form
        if session['code'] != form['captcha'].upper():
            flash("验证码错误请重新输入")
            return redirect(url_for('.contact'))
        subject = '[IMPORTANT REPLY] someone contact to you'
        send_mail(subject,
                  "Blog Admin <{0}>".format(os.environ.get('MAIL_USERNAME')),
                  recipients=['616960344@qq.com'],
                  prefix_template='/mail/mail_contact',
                  form=form)
        flash('提交成功，我会很快联系你的')
        return redirect(url_for('.contact'))
    if current_app.config['TESTING']:
        # for unit test
        code, captcha_b64 = generate_captcha_image('abcd')
    else:
        code, captcha_b64 = generate_captcha_image()
    session['code'] = ''.join(code)
    return render_template('/blog/contact.html', captcha_b64=captcha_b64)


@blog.route('/dashboard')
@login_required
def dashboard():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, 10, error_out=False)
    posts = pagination.items
    return render_template('/blog/dashboard.html', posts=posts, pagination=pagination,
                                                                endpoint='blog.dashboard')


@blog.route('/write', methods=['GET', 'POST'])
@login_required
def write():
    form = WriteForm()
    if form.validate_on_submit():
        if form.picture.data:
            # save uploaded picture to qiniu
            p = form.picture.data
            filename = secure_filename(p.filename)
              # unique filename
            split = os.path.splitext(filename)
            pre_post = Post.query.order_by(Post.id.desc()).first()
            if pre_post:
                id = pre_post.id + 1
            else:
                id = 1
            filename = split[0] + '-' + str(id) + split[1]
            data = p.read()
            upload_picture('blog', filename, data)
        else:
            filename = None

        title = form.title.data
        subtitle = form.subtitle.data
        brief_title = form.brief_title.data
        tag_string = form.tags.data
        body = form.body.data

        u = User.query.filter_by(username=current_user.username).first_or_404()
        p = Post(picture=filename, title=title, subtitle=subtitle,
                 brief_title=brief_title, body=body, author=u)
        # add post tags
        tags = set(map(lambda x: x.strip(), tag_string.split(';')))
        # remove '' tag
        try:
            tags.remove('')
        except KeyError:
            pass
        for i in tags:
            t = Tag.query.filter_by(name=i).first()
            if not t:
                t = Tag(name=i)
            p.tags.append(t)
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('blog.post'))
    return render_template('/blog/write.html', form=form)


@blog.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    p = Post.query.filter_by(id=id).first_or_404()
    if p.author.id != current_user.id:
        abort(403)
    form = WriteForm()
    if form.validate_on_submit():
        pic = form.picture.data
        if pic:
            filename = secure_filename(pic.filename)
            split = os.path.splitext(filename)
            suffix = p.id
            filename = split[0] + '-' + str(suffix) + split[1]
            data = pic.read()
            upload_picture('blog', filename, data)
        else:
            filename = p.picture

        p.picture = filename
        p.title = form.title.data
        p.brief_title = form.brief_title.data
        p.subtitle = form.subtitle.data
        p.body = form.body.data
        tag_string = form.tags.data
        tags = set(map(lambda x: x.strip(), tag_string.split(';')))
        try:
            tags.remove('')
        except KeyError:
            pass
        # get old tags via session
        old_tags = session.get('old_tags')
        # remove all old tags
        if old_tags:
            for i in old_tags:
                t = Tag.query.filter_by(name=i).first()
                p.tags.remove(t)
        # add new tags
        for i in tags:
            t = Tag.query.filter_by(name=i).first()
            if not t:
                t = Tag(name=i)
            p.tags.append(t)
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('blog.onepost', post_id=id))
    form.picture.data = p.picture
    form.title.data = p.title
    form.subtitle.data = p.subtitle
    form.brief_title.data = p.brief_title
    # set previous tag via flask session
    tags = list(map(lambda x: x.name, p.tags.all()))
    session['old_tags'] = tags
    form.tags.data = ';'.join(tags)
    form.body.data = p.body
    return render_template('/blog/write.html', form=form)


@blog.route('/delete/<int:id>')
@login_required
def delete(id):
    p = Post.query.filter_by(id=id).first_or_404()
    if p.author.id != current_user.id:
        abort(403)
    db.session.delete(p)
    db.session.commit()
    flash('DELETE SUCCESS')
    return redirect(url_for('blog.dashboard'))


@blog.route('/like/<int:id>')
def like(id):
    p = Post.query.filter_by(id=id).first_or_404()
    p.likes += 1
    db.session.add(p)
    db.session.commit()
    return redirect(url_for('blog.onepost', post_id=p.id))


@blog.route('/tags/<tag_name>')
def tag_sort(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first()
    if not tag:
        abort(404)
    page = request.args.get('page', 1, type=int)
    pagination = tag.posts.order_by(Post.timestamp.desc()).paginate(
        page, 4, error_out=False)
    posts = pagination.items
    return render_template('/blog/home.html', posts=posts,
                           pagination=pagination,
                           tag_name=tag_name,
                           endpoint='blog.tag_sort')


@blog.route('/<int:y>/<int:m>/<int:d>/<brief_title>', methods=['GET', 'POST'])
def post_brief(y, m, d, brief_title):
    post = Post.query.filter(
            cast(Post.timestamp, Date) == date(y,m,d)).\
                filter_by(brief_title=brief_title).first_or_404()
    form = CommentForm()
    if form.validate_on_submit():
        content = form.content.data
        c = Comment(body=content, author=current_user, post=post)
        db.session.add(c)
        db.session.commit()
        # send remind email when comment
        subject = '[SOMEONE COMMENT] someone comment your posts.'
        addr = url_for('.onepost', post_id=post.id, _external=True)
        send_mail(subject,
                  "Blog Admin <{0}>".format(os.environ.get('MAIL_USERNAME')),
                  recipients=[post.author.email],
                  prefix_template='/mail/comment_remind',
                  addr=addr, content=content)
        return redirect(url_for('.post_brief', y=y, m=m, d=d,
                                brief_title=brief_title)+'#comment')
    comments = post.comments.all()
    count = post.comments.count()
    post.views += 1
    db.session.add(post)
    db.session.commit()
    open_form = CommentOpenForm()
    if current_app.config['TESTING']:
        # for unit test
        code, captcha_b64 = generate_captcha_image('abcd')
    else:
        code, captcha_b64 = generate_captcha_image()
    session['code'] = ''.join(code)
    return render_template('/blog/post.html', post=post, form=form,
                           comments=comments, count=count,
                           open_form=open_form,
                           captcha_b64=captcha_b64, code=''.join(code))


@blog.route('/search')
def search():
    if not g.search_form.validate():
        return redirect(url_for('blog.home'))
    page = request.args.get('page', 1, type=int)

    posts, total = Post.search(g.search_form.q.data, page, 4)
    next_url = url_for('blog.search', q=g.search_form.q.data, page=page+1) \
            if total > page * 4 else None
    prev_url = url_for('blog.search', q=g.search_form.q.data, page=page-1) \
            if page > 1 else None
    # fake pagination
    pagination = None
    if next_url or prev_url:
        class Foo: pass
        pagination = Foo()
        if next_url:
            pagination.has_next = True
            pagination.next_num = page+1
        if prev_url:
            pagination.has_prev = True
            pagination.prev_num = page-1
    return render_template('/blog/home.html', posts=posts,
                           pagination=pagination,
                           search_data=g.search_form.q.data,
                           endpoint="blog.search")
