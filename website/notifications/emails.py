import pytz

from mako.lookup import Template
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from website import mails
from website import models as website_models
from website.notifications import constants
from website.notifications import utils
from website.notifications.model import NotificationDigest
from website.notifications.model import NotificationSubscription
from website.util import web_url_for

LOCALTIME_FORMAT = '%H:%M on %A, %B %w'

def notify(uid, event, **context):
    # TODO: docstring

    node_subscribers = []

    try:
        subscription = NotificationSubscription.find_one(
            Q('_id', 'eq', utils.to_subscription_key(uid, event))
        )
    except NoResultsFound:
        subscription = None

    for notification_type in constants.NOTIFICATION_TYPES.keys():
        subscribed_users = getattr(subscription, notification_type, [])

        node_subscribers.extend(subscribed_users)

        if subscribed_users and notification_type != 'none':
            event = 'comment_replies' if context.get('target_user') else event
            send([u._id for u in subscribed_users], notification_type, uid, event, **context)

    return check_parent(uid, event, node_subscribers, **context)


def check_parent(uid, event, node_subscribers, **context):
    """ Check subscription object for the event on the parent project
        and send transactional email to indirect subscribers.
    """
    node = website_models.Node.load(uid)
    target_user = context.get('target_user', None)

    if node and node.node__parent:
        for p in node.node__parent:
            key = utils.to_subscription_key(p._id, event)
            try:
                subscription = NotificationSubscription.find_one(Q('_id', 'eq', key))
            except NoResultsFound:
                return check_parent(p._id, event, node_subscribers, **context)

            for notification_type in constants.NOTIFICATION_TYPES.keys():
                try:
                    subscribed_users = getattr(subscription, notification_type)
                except AttributeError:
                    subscribed_users = []

                for u in subscribed_users:
                    if u not in node_subscribers and node.has_permission(u, 'read'):
                        node_subscribers.append(u)
                        if notification_type != 'none':
                            event = 'comment_replies' if target_user else event
                            send([u._id], notification_type, uid, event, **context)

            return check_parent(p._id, event, node_subscribers, **context)

    return node_subscribers


def send(subscribed_user_ids, notification_type, uid, event, **kwargs):
    """Dispatch to the handler for the provided notification_type"""

    if notification_type == 'none':
        return

    try:
        {
            'email_transactional': email_transactional,
            'email_digest': email_digest,
        }[notification_type](
            subscribed_user_ids=subscribed_user_ids,
            uid=uid,
            event=event,
            **kwargs
        )
    except KeyError:
        raise ValueError('Unrecognized notification_type')


def email_transactional(subscribed_user_ids, uid, event, **context):
    """
    :param subscribed_user_ids: mod-odm User object ids
    :param uid: id of the event owner (Node or User)
    :param event: name of notification event (e.g. 'comments')
    :param context: context variables for email template
    :return:
    """
    template = event + '.html.mako'
    subject = Template(email_templates[event]['subject']).render(**context)

    for user_id in subscribed_user_ids:
        user = website_models.User.load(user_id)
        email = user.username
        context['localized_timestamp'] = localize_timestamp(context.get('timestamp'), user)
        message = mails.render_message(template, **context)

        if context.get('commenter')._id != user._id:
            mails.send_mail(
                to_addr=email,
                mail=mails.TRANSACTIONAL,
                mimetype='html',
                name=user.fullname,
                node_id=context.get('node_id'),
                node_title=context.get('title'),
                subject=subject,
                message=message,
                url=get_settings_url(uid, user)
            )


def email_digest(subscribed_user_ids, uid, event, **context):
    """ Render the email message from context vars and store in the
        NotificationDigest objects created for each subscribed user.
    """
    template = event + '.html.mako'

    try:
        node = website_models.Node.find_one(Q('_id', 'eq', uid))
        node_lineage_ids = get_node_lineage(node)
    except NoResultsFound:
        node_lineage_ids = []

    for user_id in subscribed_user_ids:
        user = website_models.User.load(user_id)
        context['localized_timestamp'] = localize_timestamp(context.get('timestamp'), user)
        message = mails.render_message(template, **context)

        if context.get('commenter')._id != user._id:
            digest = NotificationDigest(
                timestamp=context.get('timestamp'),
                event=event,
                user_id=user._id,
                message=message,
                node_lineage=node_lineage_ids
            )
            digest.save()


def get_node_lineage(node):
    """ Get a list of node ids in order from the node to top most project
        e.g. [parent._id, node._id]
    """
    lineage = [node._id]

    while node.parent_id:
        node = website_models.Node.load(node.parent_id)
        lineage = [node._id] + lineage

    return lineage


def get_settings_url(uid, user):
    if uid == user._id:
        return web_url_for('user_notifications', _absolute=True)

    node = website_models.Node.load(uid)
    assert node, 'get_settings_url recieved an invalid Node id'
    return node.web_url_for('node_setting', _guid=True, _absolute=True)


def localize_timestamp(timestamp, user):
    try:
        user_timezone = pytz.timezone(user.timezone)
    except pytz.UnknownTimeZoneError:
        user_timezone = pytz.timezone('Etc/UTC')
    return timestamp.astimezone(user_timezone).strftime(LOCALTIME_FORMAT)


email_templates = {
    'comments': {
        'subject': '${commenter.fullname} commented on "${title}".'
    },
    'comment_replies': {
        'subject': '${commenter.fullname} replied to your comment on "${title}".'
    }
}
