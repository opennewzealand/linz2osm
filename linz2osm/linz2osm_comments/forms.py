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
    changesets = forms.CharField(label='Changeset(s)', widget=forms.Textarea, required=False)

    def clean_changesets(self):
        changeset_ary = self.cleaned_data['changesets'].split()
        changeset_out = []
        for changeset in changeset_ary:
            if changeset:
                m = CHANGESET_RE.match(changeset)
                if m:
                    changeset_out.append(m.group('changeset_id'))
                else:
                    raise forms.ValidationError("Changesets must be a number or URL of OpenStreetMap page")
        return "\n".join(changeset_out)
    
    def get_comment_model(self):
        return WorksliceComment

    def get_comment_create_data(self):
        data = super(WorksliceCommentForm, self).get_comment_create_data()
        data['changesets'] = self.cleaned_data['changesets']
        return data
