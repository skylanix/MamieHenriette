from flask import render_template, request, redirect, url_for
from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import TwitchLinkFilter, TwitchAllowedDomain, TwitchAllowedUser


def _get_or_create_config():
    config = TwitchLinkFilter.query.first()
    if not config:
        config = TwitchLinkFilter(enabled=False)
        db.session.add(config)
        db.session.commit()
    return config


@webapp.route("/link-filter")
@require_page("link_filter")
def link_filter():
    config = _get_or_create_config()
    domains = TwitchAllowedDomain.query.order_by(TwitchAllowedDomain.domain).all()
    users = TwitchAllowedUser.query.order_by(TwitchAllowedUser.username).all()
    return render_template("link-filter.html", config=config, domains=domains, users=users)


@webapp.route("/link-filter/toggle")
@require_page("link_filter")
def toggle_link_filter():
    if not can_write_page("link_filter"):
        return render_template("403.html"), 403
    config = _get_or_create_config()
    config.enabled = not config.enabled
    db.session.commit()
    return redirect(url_for('link_filter'))


@webapp.route("/link-filter/update", methods=['POST'])
@require_page("link_filter")
def update_link_filter():
    if not can_write_page("link_filter"):
        return render_template("403.html"), 403
    config = _get_or_create_config()
    config.allow_subscribers = request.form.get('allow_subscribers') is not None
    config.allow_vips = request.form.get('allow_vips') is not None
    config.allow_moderators = request.form.get('allow_moderators') is not None
    config.timeout_duration = int(request.form.get('timeout_duration', 60))
    config.warning_message = request.form.get('warning_message', '')
    db.session.commit()
    return redirect(url_for('link_filter'))


@webapp.route("/link-filter/domain/add", methods=['POST'])
@require_page("link_filter")
def add_allowed_domain():
    if not can_write_page("link_filter"):
        return render_template("403.html"), 403
    domain = request.form.get('domain', '').strip().lower()
    if domain:
        domain = domain.replace('https://', '').replace('http://', '').replace('www.', '')
        domain = domain.split('/')[0]
        existing = TwitchAllowedDomain.query.filter_by(domain=domain).first()
        if not existing:
            new_domain = TwitchAllowedDomain(domain=domain)
            db.session.add(new_domain)
            db.session.commit()
    return redirect(url_for('link_filter'))


@webapp.route("/link-filter/domain/delete/<int:domain_id>")
@require_page("link_filter")
def delete_allowed_domain(domain_id):
    if not can_write_page("link_filter"):
        return render_template("403.html"), 403
    domain = TwitchAllowedDomain.query.get_or_404(domain_id)
    db.session.delete(domain)
    db.session.commit()
    return redirect(url_for('link_filter'))


@webapp.route("/link-filter/user/add", methods=['POST'])
@require_page("link_filter")
def add_allowed_user():
    if not can_write_page("link_filter"):
        return render_template("403.html"), 403
    username = request.form.get('username', '').strip().lower().lstrip('@')
    if username:
        existing = TwitchAllowedUser.query.filter_by(username=username).first()
        if not existing:
            new_user = TwitchAllowedUser(username=username)
            db.session.add(new_user)
            db.session.commit()
    return redirect(url_for('link_filter'))


@webapp.route("/link-filter/user/delete/<int:user_id>")
@require_page("link_filter")
def delete_allowed_user(user_id):
    if not can_write_page("link_filter"):
        return render_template("403.html"), 403
    user = TwitchAllowedUser.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('link_filter'))
