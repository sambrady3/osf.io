import datetime
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from model import Subscription
from model import DigestNotification
from website import mails
from website.models import Node
from mako.lookup import Template


def notify(uid, event, **context):
    key = str(uid + '_' + event)

    for notification_type in notifications.keys():
        try:
            subscription = Subscription.find_one(Q('_id', 'eq', key))
        except NoResultsFound:
            return
        subscribed_users = []
        try:
            subscribed_users = getattr(subscription, notification_type)
        # TODO: handle this error
        except AttributeError:
            pass
        send(subscribed_users, notification_type, uid, event, **context)


def send(subscribed_users, notification_type, uid, event, **context):
    notifications.get(notification_type)(subscribed_users, uid, event, **context)


def email_transactional(subscribed_users, uid, event, **context):
    """
    :param subscribed_users:mod-odm User objects
    :param context: context variables for email template
    :return:
    """
    subject = Template(email_templates[event]['subject']).render(**context)
    message = Template(email_templates[event]['message']).render(**context)

    for user in subscribed_users:
        email = user.username
        if context.get('commenter') != user.fullname:
            mails.send_mail(
                to_addr=email,
                mail=mails.TRANSACTIONAL,
                name=user.fullname,
                subject=subject,
                message=message)


def email_digest(subscribed_users, uid, event, **context):
    message = Template(email_templates[event]['message']).render(**context)

    try:
        node = Node.find_one(Q('_id', 'eq', uid))
        nodes = get_node_lineage(node)
    except NoResultsFound:
        nodes = []

    for user in subscribed_users:
        if context.get('commenter') != user.fullname:
            digest = DigestNotification(timestamp=datetime.datetime.utcnow(),
                                        event=event,
                                        user_id=user._id,
                                        message=message,
                                        node_lineage=nodes.reverse())
            digest.save()


node_lineage = []
def get_node_lineage(node):
    if node is not None:
        node_lineage.append(node._id)
    if node.node__parent is not None:
        for n in node.node__parent:
            get_node_lineage(n)

    return node_lineage


notifications = {
    'email_transactional': email_transactional,
    'email_digest': email_digest
}

email_templates = {
    'comments': {
        'subject': '${commenter} commented on "${title}".',
        'message': '${commenter} commented on your project "${title}": "${content}"'
    },
    'comment_replies': {
        'subject': '${commenter} replied to your comment on "${title}".',
        'message': '${commenter} replied to your comment "${parent_comment}" on your project "${title}": "${content}"'
    }
}

