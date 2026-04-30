from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'

    def ready(self):
        """
        Work around django-countries 7.5.1 + Django 5.2/Python 3.12 issue:
        Country widgets store lazy choices that may resolve to a
        BlankChoiceIterator without __len__, and django-countries attempts to
        list() it (triggering a length-hint call).
        """
        try:
            from django.utils.functional import Promise
            from django_countries import widgets as country_widgets
        except Exception:
            return

        def safe_get_choices(self):  # type: ignore[no-redef]
            if isinstance(self._choices, Promise):
                materialized = []
                for choice in self._choices:
                    materialized.append(choice)
                self._choices = materialized
            return self._choices

        # NOTE: django-countries defines `choices` as a property whose fget is
        # bound to the original get_choices function object, so patch the
        # property itself (not only the method).
        try:
            country_widgets.LazyChoicesMixin.choices = property(  # type: ignore[attr-defined]
                safe_get_choices,
                country_widgets.LazyChoicesMixin.set_choices,  # type: ignore[attr-defined]
            )
        except Exception:
            return
