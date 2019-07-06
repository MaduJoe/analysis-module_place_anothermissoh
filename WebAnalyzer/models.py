# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
from rest_framework import exceptions
from AnalysisModule.config import DEBUG, PROFILE
from WebAnalyzer.tasks import analyzer_by_path
from WebAnalyzer.utils import filename
from Profile.timer import start_time, end_time
import ast


class ImageModel(models.Model):
    image = models.ImageField(upload_to=filename.default)
    token = models.AutoField(primary_key=True)
    uploaded_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    model_inference_time = models.FloatField(null=True, unique=False)
    result_save_time = models.FloatField(null=True, unique=False)

    def save(self, *args, **kwargs):
        super(ImageModel, self).save(*args, **kwargs)

        if PROFILE:
            start = start_time()
            task_get = self.get_task(self.image.path)
            self.model_inference_time = end_time(start)

            start = start_time()
            self.create_result(task_get, self.result)
            self.result_save_time = end_time(start)

        else :
            task_get = self.get_task(self.image.path)
            self.create_result(task_get, self.result)

        super(ImageModel, self).save()

    def get_task(self, image_path):
        if DEBUG:
            task_get = ast.literal_eval(str(analyzer_by_path(image_path)))
        else:
            task_get = ast.literal_eval(str(analyzer_by_path.delay(image_path).get()))
        return task_get

    def create_result(self, task_get, results):
        for result in task_get:
            results.create(values=result)


class ResultModel(models.Model):
    result_model = models.ForeignKey(ImageModel, related_name='result', on_delete=models.CASCADE)
    values = models.TextField()

    def save(self, *args, **kwargs):
        if not (isinstance(self.values[0], list) or isinstance(self.values[0], tuple)):
            raise exceptions.ValidationError("Module return values(0) Error. Please contact the administrator")
        if not (isinstance(self.values[1], dict)):
            raise exceptions.ValidationError("Module return values(1) Error. Please contact the administrator")

        super(ResultModel, self).save(*args, **kwargs)
        x, y, w, h = self.values[0]
        ResultPositionModel.objects.create(result_detail_model=self, x=x, y=y, w=w, h=h)
        for item in self.values[1].items():
            self.label.create(description=item[0], score=float(item[1]))
        # super(ResultModel, self).save()


class ResultPositionModel(models.Model):
    result_detail_model = models.OneToOneField(ResultModel, related_name='position', on_delete=models.CASCADE)
    x = models.FloatField(null=True, unique=False)
    y = models.FloatField(null=True, unique=False)
    w = models.FloatField(null=True, unique=False)
    h = models.FloatField(null=True, unique=False)

    class Meta:
        ordering = ['x', 'y', 'w', 'h']


class ResultLabelModel(models.Model):
    result_detail_model = models.ForeignKey(ResultModel, related_name='label', on_delete=models.CASCADE)
    description = models.TextField(null=True, unique=False)
    score = models.FloatField(null=True, unique=False)

    class Meta:
        ordering = ['-score']
