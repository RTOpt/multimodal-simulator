import requests
from pyproj import Proj, transform


def get_path(origin, destination):
    in_proj = Proj(init='epsg:2154')
    out_proj = Proj(init='epsg:4326')
    converted_origin_x, converted_origin_y = transform(in_proj, out_proj, origin[0], origin[1])
    converted_destination_x, converted_destination_y = transform(in_proj, out_proj, destination[0], destination[1])

    loc = "{},{};{},{}".format(converted_origin_x, converted_origin_y, converted_destination_x, converted_destination_y)
    # http://router.project-osrm.org/route/v1/driving/
    url = "http://206.12.92.28/pdll/table/v1/driving/"
    option = "?generate_hints=false&annotations=duration,distance"
    r = requests.get(url + loc + option)
    if r.status_code != 200:
        return {}

    res = r.json()

    distance = res['distances']
    duration = res['durations']
    out = {
        'origin_x': converted_origin_x,
        'origin_y': converted_origin_y,
        'destination_x': converted_destination_x,
        'destination_y': converted_destination_y,
        'distance': distance,
        'duration': duration
        }

    return out


