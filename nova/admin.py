from django.contrib import admin

# Register your models here.
from .models import Asset, AssetGroup, App, AppHost, AppGroup, AppConfig, Database, Sql, AccessKey, OssBucketApp, \
    HttpStep, ServiceStep
admin.site.register(Asset)
admin.site.register(AssetGroup)
admin.site.register(App)
admin.site.register(AppHost)
admin.site.register(AppGroup)
admin.site.register(AppConfig)
admin.site.register(Database)
admin.site.register(Sql)
admin.site.register(AccessKey)
admin.site.register(OssBucketApp)
admin.site.register(HttpStep)
admin.site.register(ServiceStep)
