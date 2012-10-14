from django.db import models
from django.contrib.comments.models import Comment, BaseCommentAbstractModel, COMMENT_MAX_LENGTH

class AuthenticatedComment(Comment):
    def content_object_link_text(self):
        return ("#%s" % self.object_pk)

    def display_name(self):
        u = self.user
        if u:
            fn = u.get_full_name()
            if fn:
                return "%s (%s)" % (u.username, fn)
            else:
                return u.username

class WorksliceComment(AuthenticatedComment):
    changesets = models.TextField(blank=True)

    def changeset_list(self):
        return self.changesets.split()

