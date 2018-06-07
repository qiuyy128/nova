# -*- coding:utf-8 -*-
__author__ = 'qiuyyb'

from django import forms
from models import Asset, AssetGroup, Task, AppConfig


class UserForm(forms.Form):
    username = forms.CharField(label='Username', max_length=100)
    password = forms.CharField(label='Password', max_length=100)


class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "ip", "other_ip", "hostname", "port", "asset_groups", "username", "password", "configs", "use_default_auth",
            "mac", "remote_ip", "brand", "cpu", "memory", "disk", "system_type", "system_version",
            "cabinet", "position", "number", "status", "asset_type", "env", "sn", "is_active", "comment",
            "system_arch"
        ]


class AssetGroupForm(forms.ModelForm):
    class Meta:
        model = AssetGroup
        fields = [
            "name", "comment"
        ]


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "task_id", "name", "status", "start_time", "end_time", "result"
        ]


class AppConfigForm(forms.Form):
    name = forms.CharField(label='name', max_length=30)
    svn_url = forms.CharField(label='svn_url', max_length=200)
    files = forms.FileField()
    env = forms.CharField(label='env', max_length=25)
    # class Meta:
    #     model = AppConfig
    #     fields = [
    #         "name", "svn_url", "files", "env"
    #     ]
