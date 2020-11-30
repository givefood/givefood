import yaml
import dicttoxml
import logging
from xml.dom.minidom import parseString
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest


def accceptable_formats(obj_name):

    have_geojson = ["foodbanks","constituency"]
    valid_formats = ["json","xml","yaml"]

    if obj_name in have_geojson:
        valid_formats.append("geojson")

    return valid_formats


def constituency_geojson(data):

    return {}



def ApiResponse(data, obj_name, format):

    valid_formats = accceptable_formats(obj_name)

    if format not in valid_formats:
        return HttpResponseBadRequest()

    if format == "json" or format == "geojson":
        response = JsonResponse(data, safe=False, json_dumps_params={'indent': 2})
    elif format == "xml":
        dicttoxml.LOG.setLevel(logging.ERROR)
        xml_str = dicttoxml.dicttoxml(data, attr_type=False, custom_root=obj_name, item_func=xml_item_name)
        xml_dom = parseString(xml_str)
        xml_str = xml_dom.toprettyxml()
        response = HttpResponse(xml_str, content_type="text/xml")
    elif format == "yaml":
        yaml_str = yaml.safe_dump(data, encoding='utf-8', allow_unicode=True, default_flow_style=False)
        response = HttpResponse(yaml_str, content_type="text/yaml")
    
    response["Access-Control-Allow-Origin"] = "*"
    return response


xml_item_name = lambda x: x[:-1]