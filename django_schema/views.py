# Create your views here.
import datetime
from collections import namedtuple

import namedtupled
from django.apps import apps
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.forms import SimpleArrayField
from django.core.exceptions import FieldDoesNotExist
from django.forms import ModelForm, DateTimeField
from django.http import JsonResponse
from django.views.generic import TemplateView

INTERNAL_TYPES = [
    "BigIntegerField",
    "BinaryField",
    "BooleanField",
    "CharField",
    "DateField",
    "DateTimeField",
    "DecimalField",
    "DurationField",
    "CharField",
    "FileField",
    "FloatField",
    "FileField",
    "IntegerField",
    "GenericIPAddressField",
    "NullBooleanField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "SlugField",
    "SmallIntegerField",
    "TextField",
    "TimeField",
    "CharField",
    "UUIDField"
]
HTML_INPUT_ELEMENT_TYPE = [
    'text',
    'number',
    'email',
    'url',
    'password',
    'date',
    'time',
    'file',
    'checkbox',
    'datetime-local'
]


def get_model_form_fields(meta_model):
    class DynamicModelForm(ModelForm):
        class Meta:
            model = meta_model
            fields = "__all__"

    form = DynamicModelForm()
    form_fields = set(form.fields)

    return form_fields


class PlainDictionaryToObject(object):
    @staticmethod
    def map(data, nested=False):
        return namedtuple('PainDictionaryToObject', data.keys())(*data.values())


def get_formatted_app_name(app_name):
    # ToDo @bikesh "Just in case if you are are versioning your apps like apps/v1/ need to make this dynamic and optimise  "
    app_name = app_name.split("apps.v1.")[-1]
    return app_name


def get_models(app_name):
    """
    app_name must match the  name of the AppConfig Class located in apps.py as below.
    from django.apps import AppConfig
    class CoreConfig(AppConfig):
        name = 'core'
    :param app_name: 'core'
    :return: "List of models linked with this app
    """
    try:
        _models = list(apps.get_app_config(app_name).get_models())
        return _models
    except:
        raise LookupError(f"this is no such app {app_name}")


def get_local_apps():
    """
    :return: List of all the installed Local Apps assign to Variable LOCAL_APPS in settings file
    """

    local_apps = settings.SCHEMA_APPS
    local_apps = [get_formatted_app_name(x) for x in local_apps]
    return local_apps


def get_apps_and_models():
    """
    :return:  All the local apps and it's associate models.
    """
    local_apps = get_local_apps()
    apps_and_models = {
        name:list(get_models(name)) for name in local_apps
    }

    return apps_and_models


class LocalInstallApps(TemplateView):
    """
    This View provide list of all the local apps and its models.
    """
    template_name = 'django_schema/local-installed-apps-list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        apps_and_models = get_apps_and_models()
        ctx['local_apps'] = apps_and_models
        return ctx


class ModelsOfLocalApp(TemplateView):
    """
    This view List of all the models of Specific App.
    """
    template_name = 'django_schema/models-of-local-app.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        app_name = kwargs.get('app_name')
        _models = get_models(app_name)

        forms = {}
        for _model in _models:
            fields = _model._meta.get_fields()

            class DynamicModelForm(ModelForm):
                class Meta:
                    model = _model
                    fields = '__all__'

            model_form_fields = DynamicModelForm().fields
            for f in fields:
                setattr(f, 'is_in_default_model_form_fields', True if f.name in model_form_fields else False)
            forms.update({
                _model.__name__:fields
            })
        ctx['forms'] = forms

        if hasattr(settings, 'MODEL_SCHEMA_TEST'):
            test_app_name = settings.MODEL_SCHEMA_TEST['app_name']
            test_model_name = settings.MODEL_SCHEMA_TEST['model']
            test_model = apps.get_model(app_label=test_app_name, model_name=test_model_name)

            class GenericModelForm(ModelForm):
                class Meta:
                    model = test_model
                    fields = '__all__'

            test_model_form = GenericModelForm()
            ctx['test_model_form'] = test_model_form
            ctx['fields'] = test_model._meta.get_fields()

        ctx['app_name'] = app_name

        return ctx

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        app_name = kwargs.get('app_name', None)
        schema_style = kwargs.get('style', None)
        app_config = apps.get_app_config(app_name)
        model_name = request.POST['model-name']
        model = app_config.get_model(model_name)
        fields = request.POST.keys()
        default_schema = self.get_default_schema_for_model(app_config, model, fields, schema_style)
        return default_schema

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_default_schema_for_model(self, app, model, fields, format_style=None):
        """
        This method will called when user submit the form. From the form we will get, model, selected fields and data_format style
        :param app: App name
        :param model: Model object
        :param fields: selected fields from the model
        :param format_style: Format style of json response
        :return: schema
        """

        app_name = get_formatted_app_name(app.name)
        model_name = model.__name__
        meta_model = model

        form_fields = get_model_form_fields(meta_model)
        selected_fields = set(fields)
        final_fields = selected_fields.intersection(form_fields)
        schema = {
            app_name:{
                'app_name':app_name,
                'full_name':app.name,
                'models':{
                    model_name:{
                        'model_name':model_name,
                        "properties":{
                        }
                    }
                }
            }

        }

        for _field in fields:
            schema[app_name]['models'][model_name]["properties"].update(self.get_field_data(model, _field))

        if format_style in ['one']:
            formatted_schema = self.get_schema_format_style_one(schema)
            return JsonResponse(formatted_schema)

        return JsonResponse(schema)

    def get_schema_format_style_one(self, schema):
        app_name = list(schema.keys())[0]
        model = list(schema[app_name]['models'])[0]
        form_name = model
        form_fields = schema[app_name]['models'][form_name]['properties']
        raw_schema = {
            form_name:{
                "attrs":{
                    "visible":False,
                    "action":"",
                    "method":"",
                    "size":"mini",
                    "label-width":"150px",
                    "label-position":"right",
                    "inline":False,
                    "id":form_name,
                    "ref":form_name,
                    "rules":{}
                },
                "FormFields":{}
            }
        }

        field_rules = {}

        for field, values in form_fields.items():
            element_type = values['html_form_element']['element_type']
            form_field_type = values['html_form_element']['form_field_type']
            # textarea does not have type
            widget_type = values['html_form_element']['widget'].get('type')
            field_and_values = {}
            if element_type == 'input' and widget_type == 'text' and form_field_type == 'SimpleArrayField':
                field_and_values = self.get_form_input_simple_array_field_style_one(field, values)
            if element_type == 'input' and widget_type == 'file' and form_field_type == 'ImageField':
                field_and_values = self.get_form_input_image_field_style_one(field, values)
            elif element_type == 'input' and widget_type == 'text':
                field_and_values = self.get_form_input_text_style_one(field, values)
            elif element_type == 'textarea':
                field_and_values = self.get_form_element_textarea_style_one(field, values)
            elif element_type == 'input' and widget_type == 'checkbox':
                field_and_values = self.get_form_input_checkbox_style_one(field, values)
            elif element_type == 'input' and widget_type == 'url':
                field_and_values = self.get_form_input_url_style_one(field, values)
            elif element_type == 'input' and widget_type == 'email':
                field_and_values = self.get_form_input_email_style_one(field, values)
            elif element_type == 'input' and widget_type == 'number':
                field_and_values = self.get_form_input_number_style_one(field, values)
            elif element_type == 'input' and widget_type == 'date':
                field_and_values = self.get_form_input_date_style_one(field, values)
            elif element_type == 'input' and widget_type == 'time':
                field_and_values = self.get_form_input_time_style_one(field, values)
            elif element_type == 'input' and widget_type == 'datetime-local':
                field_and_values = self.get_form_input_date_time_local_style_one(field, values)
            elif element_type == 'select' and form_field_type == 'TypedChoiceField':
                field_and_values = self.get_form_element_select_typed_choice_field_style_one(field, values)
            elif element_type == 'select' and form_field_type == 'ModelChoiceField':
                field_and_values = self.get_form_element_select_model_choice_field_style_one(field, values)
            elif element_type == 'select' and form_field_type == 'TreeNodeMultipleChoiceField':
                field_and_values = self.get_form_element_select_model_tree_node_multiple_choice_field_style_one(field,
                                                                                                                values)

            else:
                field_and_values = self.get_unknown_form_element_values_style_one(field, values)
            field_rules.update({
                field:[]
            })
            field_and_values[field].update({
                'form_field_type_for_reference':form_field_type,
                'help_text':values['help_text']
            })
            raw_schema[form_name]['FormFields'].update(field_and_values)
        raw_schema[form_name]['attrs']['rules'] = field_rules
        return raw_schema

    def get_form_input_text_style_one(self, field_name, field_attrs):
        '''
        "field_name":{
                    "label":"field_name",
                    "formFieldType":{
                       "type":"input",
                       "attrs":{
                          "visible":true,
                          "type":"text",
                          "placeholder":"Please input",
                          "autofocus":true,
                          "maxlength":150,
                          "minlength":30,
                          "readonly":false,
                          "name":"field_name",
                          "clearable":false,
                          "disabled":false,
                          "size":"medium",
                          "suffix-icon":"",
                          "prefix-icon":"",
                          "id":"field_name"
                       }
                    }
                 },
        :param schema:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"text",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "maxlength":field.max_length,
                        "minlength":field.min_length,
                        "readonly":False,
                        "name":field.name,
                        "clearable":False,
                        "disabled":False,
                        "size":"medium",
                        "suffix-icon":"",
                        "prefix-icon":"",
                        "id":field.id
                    }
                }
            },
        }

        return final_schema

    def get_form_input_image_field_style_one(self, field_name, field_attrs):
        '''
       data= {
        "thumbnail":{
           "label":"Thumbnail",
           "formFieldType":{
              "type":"input",
              "attrs":{
                 "visible":true,
                 "type":"text",
                 "placeholder":null,
                 "autofocus":true,
                 "maxlength":100,
                 "minlength":"",
                 "readonly":false,
                 "name":"thumbnail",
                 "clearable":false,
                 "disabled":false,
                 "size":"medium",
                 "suffix-icon":"",
                 "prefix-icon":"",
                 "id":"thumbnail"
              }
           },
           "form_field_type_for_reference":"ImageField"
            }
        }
        :param schema:
        :return: data
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"file",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "maxlength":field.max_length,
                        "minlength":field.min_length,
                        "readonly":False,
                        "name":field.name,
                        "clearable":False,
                        "disabled":False,
                        "size":"medium",
                        "suffix-icon":"",
                        "prefix-icon":"",
                        "id":field.id
                    }
                }
            },
        }

        return final_schema

    def get_form_input_simple_array_field_style_one(self, field_name, field_attrs):
        '''
        "field_name":{
                    "label":"field_name",
                    "formFieldType":{
                       "type":"input",
                       "attrs":{
                          "visible":true,
                          "type":"text",
                          "placeholder":"Please input",
                          "autofocus":true,
                          "maxlength":150,
                          "minlength":30,
                          "readonly":false,
                          "name":"field_name",
                          "clearable":false,
                          "disabled":false,
                          "size":"medium",
                          "suffix-icon":"",
                          "prefix-icon":"",
                          "id":"field_name"
                       }
                    }
                 },
        :param schema:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        ## Extract only values of the field name
        base_field_reduced_attrs = namedtupled.reduce(field.base_field)[field_name]
        base_element_type = base_field_reduced_attrs['html_form_element']['element_type']
        base_element_widget_type = base_field_reduced_attrs['html_form_element']['widget']['type']
        base_field_attr = {}

        # ToDo @bikesh "At the moment only handle email and text"
        if base_element_type == 'input' and base_element_widget_type == 'email':
            base_field_attr = self.get_form_input_email_style_one(field_name, base_field_reduced_attrs)
        if base_element_type == 'input' and base_element_widget_type == 'text':
            base_field_attr = self.get_form_input_text_style_one(field_name, base_field_reduced_attrs)
        # if field.base_field.
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"text",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "maxlength":field.max_length,
                        "minlength":field.min_length,
                        "readonly":False,
                        "name":field.name,
                        "clearable":False,
                        "disabled":False,
                        "size":"medium",
                        "suffix-icon":"",
                        "prefix-icon":"",
                        "id":field.id,
                    },
                    "baseFormField":base_field_attr

                }
            },
        }

        return final_schema

    def get_form_input_url_style_one(self, field_name, field_attrs):
        '''
        "field_name":{
                    "label":"field_name",
                    "formFieldType":{
                       "type":"input",
                       "attrs":{
                          "visible":true,
                          "type":"text",
                          "placeholder":"Please input",
                          "autofocus":true,
                          "maxlength":150,
                          "minlength":30,
                          "readonly":false,
                          "name":"field_name",
                          "clearable":false,
                          "disabled":false,
                          "size":"medium",
                          "suffix-icon":"",
                          "prefix-icon":"",
                          "id":"field_name"
                       }
                    }
                 },
        :param schema:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"url",
                    "attrs":{
                        "visible":True,
                        "type":"text",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "maxlength":field.max_length,
                        "minlength":field.min_length,
                        "readonly":False,
                        "name":field.name,
                        "clearable":False,
                        "disabled":False,
                        "size":"medium",
                        "suffix-icon":"",
                        "prefix-icon":"",
                        "id":field.id
                    }
                }
            },
        }

        return final_schema

    def get_form_input_email_style_one(self, field_name, field_attrs):
        '''
        :param schema:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"email",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "maxlength":field.max_length,
                        "minlength":field.min_length,
                        "readonly":False,
                        "name":field.name,
                        "clearable":False,
                        "disabled":False,
                        "size":"medium",
                        "suffix-icon":"",
                        "prefix-icon":"",
                        "id":field.id
                    }
                }
            },
        }
        return final_schema

    def get_form_input_date_style_one(self, field_name, field_attrs):
        '''
        :param schema:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field_name,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"date",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "default-value":"",
                        "readonly":False,
                        "name":field.name,
                        "format":"yyyy/MM/dd",
                        "value-format":"yyyy-MM-dd",
                        "other-value-formats":'',
                        "align":"right",
                        "disabled":False,
                        "clearable":True,
                        "editable":True,
                        "size":"medium",
                        "clear-icon":"el-icon-circle-close",
                        "prefix-icon":"el-icon-date",
                        "picker-options":"",
                        "id":field.id
                    }
                }
            },
        }
        return final_schema

    def get_form_input_time_style_one(self, field_name, field_attrs):
        '''
        :param schema:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field_name,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"time",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "default-value":"",
                        "readonly":False,
                        "name":field.name,
                        "format":"HH:mm:ss",
                        "value-format":"HH:mm:ss",
                        "other-value-formats":'',
                        "align":"right",
                        "disabled":False,
                        "clearable":True,
                        "editable":True,
                        "size":"medium",
                        "clear-icon":"el-icon-circle-close",
                        "prefix-icon":"el-icon-date",
                        "picker-options":"",
                        "id":field.id
                    }
                }
            },
        }
        return final_schema

    def get_form_input_date_time_local_style_one(self, field_name, field_attrs):
        '''
        :param schema:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"datetime",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "default-value":"",
                        "readonly":False,
                        "name":"field_name3",
                        "format":"WW",
                        "value-format":"yyyy-MM-dd HH:mm:ss",
                        "align":"right",
                        "disabled":False,
                        "clearable":True,
                        "editable":True,
                        "size":"medium",
                        "clear-icon":"el-icon-circle-close",
                        "prefix-icon":"el-icon-date",
                        "id":field.id
                    }
                }
            }
        }
        return final_schema

    def get_form_input_number_style_one(self, field_name, field_attrs):
        '''
        :param schema:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"number",
                        "placeholder":field.placeholder,
                        "autofocus":True,
                        "maxlength":field.max_length,
                        "minlength":field.min_length,
                        "readonly":False,
                        "name":field.name,
                        "clearable":False,
                        "disabled":False,
                        "size":"medium",
                        "suffix-icon":"",
                        "prefix-icon":"",
                        "id":field.id
                    }
                }
            },
        }
        return final_schema

    def get_form_input_checkbox_style_one(self, field_name, field_attrs):
        '''
        data = {
        field_name":{
                    "label":"field_name",
                    "formFieldType":{
                       "type":"input",
                       "attrs":{
                          "visible":true,
                          "type":"checkbox",
                          "checked":true,
                          "name":"field_name",
                          "disabled":false,
                          "size":"medium",
                          "id":"field_name"
                       }
                    }
                 }

        }
        :param field_name:
        :param field_attrs:
        :return:
        '''
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"input",
                    "attrs":{
                        "visible":True,
                        "type":"checkbox",
                        "checked":field.default,
                        "name":field.name,
                        "disabled":False,
                        "size":"medium",
                        "id":field.id
                    }
                }
            }
        }
        return final_schema

    def get_form_element_select_typed_choice_field_style_one(self, field_name, field_attrs):
        """
        data = {
         "field_name":{
            "label":"field_name",
            "formFieldType":{
               "type":"select",
               "attrs":{
                  "visible":true,
                  "id":"field_name",
                  "disabled":false,
                  "clearable":true,
                  "multiple":false,
                  "placeholder":"select",
                  "collapse-tags":true
               },
               "choices":[
                  {
                     "value":"Option1",
                     "label":"Option1"
                  },
                  {
                     "value":"Option2",
                     "label":"Option2"
                  },
                  {
                     "value":"Option3",
                     "label":"Option3"
                  }
               ]
            }
         },
        }
        :param field_name:
        :param field_attrs:
        :return:
        """
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"select",
                    "attrs":{
                        "visible":True,
                        "id":field.id,
                        "disabled":False,
                        "clearable":True,
                        "multiple":field.html_form_element.widget.allow_multiple_selected,
                        "placeholder":field.placeholder,
                        "collapse-tags":True,
                        "is_model_choice_field":False
                    },
                    "choices":self.get_choices(field.html_form_element.widget.choices)
                }
            },
        }

        return final_schema

    def get_form_element_select_model_choice_field_style_one(self, field_name, field_attrs):
        """
        data = {
         "field_name":{
            "label":"field_name",
            "formFieldType":{
               "type":"select",
               "attrs":{
                  "visible":true,
                  "id":"field_name",
                  "disabled":false,
                  "clearable":true,
                  "multiple":false,
                  "placeholder":"select",
                  "collapse-tags":true
               },
               "choices":[
                  {
                     "value":"Option1",
                     "label":"Option1"
                  },
                  {
                     "value":"Option2",
                     "label":"Option2"
                  },
                  {
                     "value":"Option3",
                     "label":"Option3"
                  }
               ]
            }
         },
        }
        :param field_name:
        :param field_attrs:
        :return:
        """
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"select",
                    "attrs":{
                        "visible":True,
                        "id":field.id,
                        "disabled":False,
                        "clearable":True,
                        "multiple":field.html_form_element.widget.allow_multiple_selected,
                        "placeholder":field.placeholder,
                        "can_be_autocomplete":field.html_form_element.widget.can_be_autocomplete,
                        "set_id_on_form_save":field.html_form_element.widget.set_id_on_form_save,
                        "collapse-tags":True,
                        "is_model_choice_field":True
                    },
                    "choices":"ModelChoiceIterator",
                }
            },
        }

        return final_schema

    def get_form_element_select_model_tree_node_multiple_choice_field_style_one(self, field_name, field_attrs):
        """
        data = {
        "tree_categories": {
                        "label": "Tree Categories",
                        "formFieldType": {
                            "type": "select",
                            "attrs": {
                                "visible": true,
                                "id": "tree_categories",
                                "disabled": false,
                                "clearable": true,
                                "multiple": true,
                                "placeholder": null,
                                "can_be_autocomplete": true,
                                "set_id_on_form_save": true,
                                "collapse-tags": true,
                                "is_model_choice_field": true
                            },
                            "choices": "TreeNodeMultipleChoiceField"
                        },
                        "form_field_type_for_reference": "TreeNodeMultipleChoiceField"
            }
        }
        :param field_name:
        :param field_attrs:
        :return:
        """
        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"select",
                    "attrs":{
                        "visible":True,
                        "id":field.id,
                        "disabled":False,
                        "clearable":True,
                        "multiple":field.html_form_element.widget.allow_multiple_selected,
                        "placeholder":field.placeholder,
                        "can_be_autocomplete":field.html_form_element.widget.can_be_autocomplete,
                        "set_id_on_form_save":field.html_form_element.widget.set_id_on_form_save,
                        "collapse-tags":True,
                        "is_model_choice_field":True
                    },
                    "choices":"TreeNodeMultipleChoiceIterator",
                }
            },
        }

        return final_schema

    def get_form_element_textarea_style_one(self, field_name, field_attrs):
        """
        field_name":{
                    "label":"field_name",
                    "formFieldType":{
                       "type":"textarea",
                       "attrs":{
                          "visible":true,
                          "rows":"2",
                          "autofocus":true,
                          "maxlength":150,
                          "minlength":30,
                          "readonly":false,
                          "name":"field_name",
                          "clearable":false,
                          "disabled":false,
                          "size":"medium",
                          "placeholder":"Please input",
                          "id":"field_name",
                          "autosize":{
                             "minRows":2,
                             "maxRows":4
                          }
                       }
                    }
        :param field:
        :return:
        """

        field = self.get_field_values(field_attrs)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"textarea",
                    "attrs":{
                        "visible":True,
                        "rows":"2",
                        "autofocus":True,
                        "maxlength":field.max_length,
                        "minlength":field.min_length,
                        "readonly":False,
                        "name":field.name,
                        "clearable":False,
                        "disabled":False,
                        "size":"medium",
                        "placeholder":field.placeholder,
                        "id":field.id,
                        "autosize":{
                            "minRows":field.html_form_element.widget.attrs.rows,
                            "maxRows":field.html_form_element.widget.attrs.rows
                        }
                    }
                }
            }
        }

        return final_schema

    def get_field_values(self, values):
        key = values['key']
        label = values.get('label', key).title()
        data = {
            'key':key,
            'label':label,
            'is_required':values.get('required'),
            'placeholder':values.get('default', f'Please provide {label}'),
            'max_length':values.get('max_length', 0),
            'min_length':values.get('min_length', 0),
            'id':key,
            'name':key,
        }
        values.update(data)
        data = namedtupled.map(values)
        return data

    def get_unknown_form_element_values_style_one(self, field_name, values):
        field = self.get_field_values(values)
        final_schema = {
            field_name:{
                "label":field.label,
                "formFieldType":{
                    "type":"unknown",
                    "attrs":{
                        "visible":True,
                        "rows":"2",
                        "autofocus":True,
                        "maxlength":field.max_length,
                        "minlength":field.min_length,
                        "readonly":False,
                        "name":field.name,
                        "clearable":False,
                        "disabled":False,
                        "size":"medium",
                        "placeholder":field.placeholder,
                        "id":field.id,
                    }
                }
            }
        }

        return final_schema

    def get_choices(self, choices):
        options = []
        for k, v in choices:
            options.append({
                "label":v,
                "value":k,
            })

        return options

    def get_html_element_data(self, field):
        try:
            widget = field.formfield().widget
        except:
            widget = ''
        form_field_type = field.formfield().__class__.__name__
        widget_class = widget.__class__.__name__
        if widget:
            data = {
                'element_type':'',
                'form_field_type':form_field_type,
                'widget':{
                    'attrs':widget.attrs if hasattr(widget, 'attrs') else '',
                    'widget_class':widget_class,
                }

            }
            if hasattr(widget, 'allow_multiple_selected'):
                data['widget']['allow_multiple_selected'] = widget.allow_multiple_selected
            if hasattr(widget, 'format'):
                data['widget']['format'] = widget.format

            if hasattr(widget, 'choices'):
                if form_field_type in ['ModelMultipleChoiceField', 'ModelChoiceField', "TreeNodeMultipleChoiceField"]:
                    data['widget']['can_be_autocomplete'] = True
                    data['widget']['set_id_on_form_save'] = True
                    data['widget']['form_field_type_for_reference'] = form_field_type
                else:
                    data['widget']['choices'] = self.get_choices(widget.choices)

            if hasattr(widget, 'input_type'):
                input_type = widget.input_type
                if widget_class == 'DateTimeInput':
                    input_type = 'datetime-local'
                if widget_class == 'DateInput':
                    input_type = 'date'
                if widget_class == 'TimeInput':
                    input_type = 'time'
                element_type = ''
                if input_type in HTML_INPUT_ELEMENT_TYPE:
                    element_type = 'input'
                if input_type == 'select':
                    element_type = 'select'

                data['element_type'] = element_type
                data['widget'].update({
                    'type':input_type,

                })

            if widget_class == 'Textarea':
                data['element_type'] = 'textarea'

            return data
        else:
            return ''

    def get_field_label(self, field):
        label = ''
        try:
            label = field.formfield().label
        except:
            pass
        return label

    def get_field_is_required(self, field):
        required = ''
        try:
            required = field.formfield().required
        except:
            pass
        return required

    def get_field_default(self, field):
        initial = ''
        try:
            initial = field.formfield().initial
            if callable(initial):
                if isinstance(field.formfield(), DateTimeField):
                    if isinstance(initial(), datetime.datetime):
                        initial = initial().strftime("%Y-%m-%d %H:%I:%S %Z")
                else:
                    # need to handle other initials
                    initial = ''
        except:
            pass
        return initial

    def get_field_help_text(self, field):
        help_text = ''
        try:
            help_text = field.formfield().help_text
        except:
            pass
        return help_text

    def get_field_data(self, model, field_name):
        data = {}
        try:
            model_form_fields = get_model_form_fields(model)
            field_obj = model._meta.get_field(field_name)
            internal_type = field_obj.get_internal_type()
            data = self._get_field_data(model, field_obj)
            if hasattr(field_obj, 'base_field') and isinstance(field_obj, ArrayField) and isinstance(
                    field_obj.formfield(),
                    SimpleArrayField):
                data[field_name].update({
                    'base_field':self._get_field_data(model, field_obj.base_field)
                })
        except FieldDoesNotExist:
            pass

        return data

    def _get_field_data(self, model, field_obj):
        model_form_fields = get_model_form_fields(model)
        # field = model._meta.get_field(field)
        internal_type = field_obj.get_internal_type()
        data = {
            field_obj.name:{
                "related_model":"",
                "is_related":field_obj.is_relation,
                "key":field_obj.name,
                "data_type":internal_type,
                "model_field_type":internal_type,
                "min_length":field_obj.min_length if hasattr(field_obj, 'min_length') else '',
                "max_length":field_obj.max_length,
                "choices":self.get_choices(field_obj.choices),
                "label":self.get_field_label(field_obj),
                "required":self.get_field_is_required(field_obj),
                "default":self.get_field_default(field_obj),
                "help_text":self.get_field_help_text(field_obj),
                "form_field_type":field_obj.formfield().__class__.__name__,
                "html_form_element":self.get_html_element_data(field_obj),
                "is_in_default_model_form_fields":True if field_obj.name in model_form_fields else False
                ## Is in ModelForm field which return __all__
            }
        }
        return data


class LocalInstallAppsStyleOne(LocalInstallApps):

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['style'] = 'one'
        return ctx


class SchemaIndexView(TemplateView):
    template_name = "django_schema/schema_index.html"
