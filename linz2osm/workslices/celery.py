from __future__ import absolute_import

from celery import Celery

celery = Celery(broker = 'amqp://',
                backend = 'amqp://',
                include = ['linz2osm.workslices.tasks'])
celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES = 86400,
    )
