import django
from django.db import DEFAULT_DB_ALIAS, router
from django.apps import apps
from django.utils.encoding import smart_text
from django.utils import six
from django.utils.six.moves import input


def update_contenttypes(sender, verbosity=2, db=DEFAULT_DB_ALIAS, **kwargs):
    """
        Django's default update_contenttypes relies on many inconsistent queries which causes problems
        with syncdb. This monkeypatch replaces it with a version that does look ups on unique constraints
        which are slightly better protected from eventual consistency issues by the context cache.
    """
    from django.contrib.contenttypes.models import ContentType
    
    if verbosity >= 2:
        print("Running Djangae version of update_contenttypes on {}".format(sender))

    try:
        apps.get_model('contenttypes', 'ContentType')
    except LookupError:
        return

    if hasattr(router, "allow_migrate_model"):
        if not router.allow_migrate_model(db, ContentType):
            return

    ContentType.objects.clear_cache()
    app_models = sender.get_models()
    if not app_models:
        return
    # They all have the same app_label, get the first one.
    app_label = sender.label
    app_models = dict(
        (model._meta.model_name, model)
        for model in app_models
    )

    created_or_existing_pks = []
    created_or_existing_by_unique = {}

    for (model_name, model) in six.iteritems(app_models):
        # Go through get_or_create any models that we want to keep
        defaults = {}
        if django.VERSION < (1, 9):
            defaults['name'] = smart_text(model._meta.verbose_name_raw)

        ct, created = ContentType.objects.get_or_create(
            app_label=app_label,
            model=model_name,
            defaults=defaults,
        )

        if verbosity >= 2 and created:
            print("Adding content type '%s | %s'" % (ct.app_label, ct.model))

        created_or_existing_pks.append(ct.pk)
        created_or_existing_by_unique[(app_label, model_name)] = ct.pk

    # Now lets see if we should remove any

    to_remove = [x for x in ContentType.objects.filter(app_label=app_label) if x.pk not in created_or_existing_pks]

    # Now it's possible that our get_or_create failed because of consistency issues and we create a duplicate.
    # Then the original appears in the to_remove and we remove the original. This is bad. So here we go through the
    # to_remove list, and if we created the content type just now, we delete that one, and restore the original in the
    # cache
    for ct in to_remove:
        unique = (ct.app_label, ct.model)
        if unique in created_or_existing_by_unique:
            # We accidentally created a duplicate above due to HRD issues, delete the one we created
            ContentType.objects.get(pk=created_or_existing_by_unique[unique]).delete()
            created_or_existing_by_unique[unique] = ct.pk
            ct.save()  # Recache this one in the context cache

    to_remove = [ x for x in to_remove if (x.app_label, x.model) not in created_or_existing_by_unique ]

    # Now, anything left should actually be a stale thing. It's still possible we missed some but they'll get picked up
    # next time. Confirm that the content type is stale before deletion.
    if to_remove:
        if kwargs.get('interactive', False):
            content_type_display = '\n'.join([
                '    %s | %s' % (x.app_label, x.model)
                for x in to_remove
            ])
            ok_to_delete = input("""The following content types are stale and need to be deleted:

%s

Any objects related to these content types by a foreign key will also
be deleted. Are you sure you want to delete these content types?
If you're unsure, answer 'no'.

    Type 'yes' to continue, or 'no' to cancel: """ % content_type_display)
        else:
            ok_to_delete = False

        if ok_to_delete == 'yes':
            for ct in to_remove:
                if verbosity >= 2:
                    print("Deleting stale content type '%s | %s'" % (ct.app_label, ct.model))
                ct.delete()
        else:
            if verbosity >= 2:
                print("Stale content types remain.")
