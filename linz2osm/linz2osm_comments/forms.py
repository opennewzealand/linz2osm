from django import forms
from django.conf import settings
from django.contrib.comments.forms import CommentForm
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.encoding import force_unicode
from linz2osm.linz2osm_comments.models import AuthenticatedComment, WorksliceComment
import datetime
import re

class AuthenticatedCommentForm(CommentForm):
    def get_comment_model(self):
        return AuthenticatedComment
    
    def get_comment_create_data(self):
        return dict(
            content_type = ContentType.objects.get_for_model(self.target_object),
            object_pk    = force_unicode(self.target_object._get_pk_val()),
            comment      = self.cleaned_data["comment"],
            submit_date  = timezone.now(),
            site_id      = settings.SITE_ID,
            is_public    = True,
            is_removed   = False,
        )

AuthenticatedCommentForm.base_fields.pop('url')
AuthenticatedCommentForm.base_fields.pop('email')
AuthenticatedCommentForm.base_fields.pop('name')

CHANGESET_RE = re.compile("^(.*/)?(?P<changeset_id>[0-9]*)$")

class WorksliceCommentForm(AuthenticatedCommentForm):
    changeset = forms.CharField(label=('Changeset'), required=False)

    def clean_changeset(self):
        changeset = self.cleaned_data['changeset']
        if changeset:
            m = CHANGESET_RE.match(changeset)
            if m:
                changeset = m.group('changeset_id')
            else:
                raise forms.ValidationError("Changeset must be a number or URL of OpenStreetMap page")
        return changeset
    
    def get_comment_model(self):
        return WorksliceComment

    def get_comment_create_data(self):
        data = super(WorksliceCommentForm, self).get_comment_create_data()
        data['changeset'] = self.cleaned_data['changeset']
        return data
