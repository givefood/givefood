import yaml
import dicttoxml
import logging
from xml.dom.minidom import parseString
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest


ACCEPTABLE_FORMATS = ["json","xml","yaml"]


def ApiResponse(data, obj_name, format):

    if format not in ACCEPTABLE_FORMATS:
        return HttpResponseBadRequest()

    if format == "json":
        return JsonResponse(data, safe=False, json_dumps_params={'indent': 2})
    elif format == "xml":
        dicttoxml.LOG.setLevel(logging.ERROR)
        xml_str = dicttoxml.dicttoxml(data, attr_type=False, custom_root=obj_name, item_func=xml_item_name)
        xml_dom = parseString(xml_str)
        xml_str = xml_dom.toprettyxml()
        return HttpResponse(xml_str, content_type="text/xml")
    elif format == "yaml":
        yaml_str = yaml.safe_dump(data, encoding='utf-8', allow_unicode=True, default_flow_style=False)
        return HttpResponse(yaml_str, content_type="text/yaml")


xml_item_name = lambda x: x[:-1]