import yaml
import dicttoxml
import logging
from xml.dom.minidom import parseString
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest


# Sets of formats that can be returned per object name
STD_FORMATS = [
    "json",
    "xml",
    "yaml",
]
STD_FORMATS_GEOJSON = [
    "json",
    "xml",
    "yaml",
    "geojson",
]

# The formats allowed per object name
ALLOWED_FORMATS = {
    "foodbank": STD_FORMATS_GEOJSON,
    "foodbanks": STD_FORMATS_GEOJSON,
    "location": STD_FORMATS,
    "locations": STD_FORMATS_GEOJSON,
    "donationpoints": STD_FORMATS_GEOJSON,
    "need": STD_FORMATS,
    "needs": STD_FORMATS,
    "constituency": STD_FORMATS_GEOJSON,
    "constituencies": STD_FORMATS,
}


def ApiResponse(data, obj_name, format):

    if format not in ALLOWED_FORMATS.get(obj_name):
        return HttpResponseBadRequest()

    json_formats = [
        "json",
        "geojson"
    ]
    xml_formats = [
        "xml",
        "opml",
        "rss",
    ]

    if format in json_formats:
        response = JsonResponse(data, safe=False, json_dumps_params={'indent': 2})
    elif format in xml_formats:
        dicttoxml.LOG.setLevel(logging.ERROR)
        xml_str = dicttoxml.dicttoxml(data, attr_type=False, custom_root=obj_name, item_func=xml_item_name)
        xml_dom = parseString(xml_str)
        xml_str = xml_dom.toprettyxml()
        response = HttpResponse(xml_str, content_type="text/xml")
    elif format == "yaml":
        yaml_str = yaml.dump(data, encoding='utf-8', allow_unicode=True, default_flow_style=False)
        response = HttpResponse(yaml_str, content_type="text/yaml")
    
    response["Access-Control-Allow-Origin"] = "*"
    return response


def xml_item_name(plural):

    singular = {
        "foodbanks":"foodbank",
        "nearby_foodbanks":"foodbank",
        "locations":"location",
        "needs":"need",
        "constituencies":"constituency",
    }

    return singular.get(plural)