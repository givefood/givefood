from django import forms
from django.db import models
from django.contrib import admin
from .models import UniqueAction, ActionLog, encode_model

def _show_model(m):

    if m._meta.app_label == "uniquetool":
        return False

    if any([ x.unique for x in m._meta.fields ]):
        return True

    if x._meta.unique_together:
        return True

    return False

class ActionLogInline(admin.TabularInline):
    model = ActionLog
    verbose_name_plural = 'List of action messages'

    can_delete = False
    extra = 0
    editable_fields = []
    readonly_fields = ('log_type', 'instance_key', 'marker_key', )

    def has_add_permission(self, request):
        return False


class UniqueActionAdmin(admin.ModelAdmin):
    actions = None
    list_display = ('action_type', 'model_name', 'status')
    change_form_template = "admin/unique_action_change_form.html"
    inlines = [ActionLogInline]

    @classmethod
    def model_choices(cls):
        if not hasattr(cls, '_model_choices'):
            all_models = sorted([
                (encode_model(m), m.__name__)
                for m in models.get_models()
                if _show_model(m)
            ], key=lambda x: x[1])
            cls._model_choices = all_models
        return cls._model_choices

    def model_name(self, instance):
        return dict(self.model_choices())[instance.model]

    def get_form(self, request, obj=None, **kwargs):
        if obj is not None and obj.pk:
            kwargs['fields'] = []
            return super(UniqueActionAdmin, self).get_form(request, obj=obj, **kwargs)

        form = super(UniqueActionAdmin, self).get_form(request, obj=obj, **kwargs)
        # FIXME: this field should be optional when a "clean" action is selected
        form.base_fields['model'] = forms.ChoiceField(choices=self.model_choices())
        return form

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == 'running':
            return False
        return super(UniqueActionAdmin, self).has_delete_permission(request, obj=obj)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if obj:
            context["title"] = u"Errors from %s on %s (%s)" % (obj.action_type, self.model_name(obj), obj.get_status_display())
            context["readonly"] = True
        return super(UniqueActionAdmin, self).render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)


admin.site.register(UniqueAction, UniqueActionAdmin)
