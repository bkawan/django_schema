=====

django_schema

=====

Django Schema is a simple Django app to generate schema of Models .

`Demo Link`_

.. image:: django-schema-demo.gif

Installation

.. code:: shell

   $ pipenv install django_schema

Detailed documentation is in the “docs” directory.

Quick start
-----------

1. Add “schema” to your INSTALLED_APPS setting like this::

.. code:: python

     INSTALLED_APPS = [
         ...
         'django_schema',
     ]

2. Add list of local apps to SCHEMA_APPS setting like this

.. code:: python


   SCHEMA_APPS = [
           'blog',
           'users',
           'product',
   ]

3. Include the schema URLconf in your project urls.py like this::

.. code:: python

   from django.urls import include
   urlpatterns = [
       ...
       path('schema/', include('django_schema.urls'))
   ]

4. Visit http://127.0.0.1:8000/schema/ to check all the schema styles

5. For testing

.. code:: python

   MODEL_SCHEMA_TEST = {
       'app_name':'blog',
       'model':'post'
   }

To Do
-----

-  Permission
-  Handling App versioning for ex ‘apps/v1/blog’, ‘apps/v1/users’
-  Add Serializers For all the Django Model Field INTERNAL_TYPES
-  Handle more html elements types
-  Add docs
-  Add Testing

.. _Demo Link: http://django-schema.herokuapp.com