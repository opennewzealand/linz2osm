from django.db import models
from django.contrib.comments.models import Comment, BaseCommentAbstractModel, COMMENT_MAX_LENGTH

class AuthenticatedComment(Comment):
    pass

class WorksliceComment(AuthenticatedComment):
    changeset = models.TextField(blank=True)
