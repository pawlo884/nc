from django.apps import AppConfig


class Matterhorn1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matterhorn1'

    def ready(self):
        # CSS fix layoutu changelist (Django 6 + admin_interface sticky filter)
        from django.contrib.admin import ModelAdmin
        from django.forms import Media

        if getattr(ModelAdmin, '_nc_django6_changelist_css_patched', False):
            return

        fix_css = Media(css={
            'all': ('matterhorn1/css/admin-changelist-django6-fix.css',),
        })
        original_media = ModelAdmin.media.fget

        def media(self):
            return original_media(self) + fix_css

        ModelAdmin.media = property(media)
        ModelAdmin._nc_django6_changelist_css_patched = True
