from django.db import models
from django.contrib.comments.models import Comment, BaseCommentAbstractModel, COMMENT_MAX_LENGTH

class AuthenticatedComment(Comment):
    def content_object_link_text(self):
        return ("#%s" % self.object_pk)

class WorksliceComment(AuthenticatedComment):
    changeset = models.TextField(blank=True)

    def changeset_link(self):
        if self.changeset:
            return "http://www.openstreetmap.org/browse/changeset/%s" % self.changeset
        return ""


