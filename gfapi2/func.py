import yaml
import dicttoxml
import logging
from xml.dom.minidom import parseString
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest


def accceptable_formats(obj_name):
    if obj_name == "foodbanks":
        return ["json","xml","yaml","geojson"]
    return ["json","xml","yaml"]


def make_geojson(data):

    features = []
    for foodbank in data:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(foodbank.get("lat_lng").split(",")[1]), float(foodbank.get("lat_lng").split(",")[0])]
                },
                "properties": {
                    "name": foodbank.get("name"),
                    "address": foodbank.get("address"),
                    "country": foodbank.get("country"),
                    "url": foodbank.get("urls").get("homepage"),
                    "json": foodbank.get("urls").get("self"),
                    "network": foodbank.get("network"),
                    "email": foodbank.get("email"),
                    "telephone": foodbank.get("phone"),
                    "parliamentary_constituency": foodbank.get("politics").get("parliamentary_constituency")
                }
            }
        )

    geojson = {
        "type": "FeatureCollection",
        "features": features
     }

    return geojson


def ApiResponse(data, obj_name, format):

    valid_formats = accceptable_formats(obj_name)

    if format not in valid_formats:
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
    elif format == "geojson":
        geojson_str = make_geojson(data)
        return JsonResponse(geojson_str, safe=False, json_dumps_params={'indent': 2})


xml_item_name = lambda x: x[:-1]