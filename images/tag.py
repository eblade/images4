
import random, logging

from bottle import Bottle, auth_basic, request
from sqlalchemy.orm.exc import NoResultFound

from . import api, Tag
from .database import get_db
from .types import PropertySet, Property
from .user import authenticate, no_guests


BASE = '/tag'
app = Bottle()
api.register(BASE, app)


@app.get('/')
@auth_basic(authenticate)
def rest_get_tags():
    json = get_tags().to_json()
    logging.debug("Tag feed\n%s", json)
    return json


@app.get('/<id>')
@auth_basic(authenticate)
def rest_get_tag_by_id(id):
    json = get_tag_by_id().to_json()
    logging.debug("Tag\n%s", json)
    return json


@app.post('/')
@auth_basic(authenticate)
@no_guests()
def rest_add_tag():
    tag = TagDescriptor(request.json)
    logging.debug("Incoming Tag\n%s", tag.to_json())
    json = add_tag(tag).to_json()
    logging.debug("Outgoing Tag\n%s", json)
    return json


@app.delete('/<id>')
@auth_basic(authenticate)
@no_guests()
def rest_delete_tag_by_id(id):
    logging.debug("Deleting Tag %s", id)
    delete_tag_by_id(id)


colors = [
    # Background Foreground Name
    ('#000000', '#ffffff', 'Black'),
    ('#000080', '#ffffff', 'Navy'),
    ('#00008B', '#ffffff', 'DarkBlue'),
    ('#0000CD', '#ffffff', 'MediumBlue'),
    ('#0000FF', '#ffffff', 'Blue'),
    ('#006400', '#ffffff', 'DarkGreen'),
    ('#008000', '#ffffff', 'Green'),
    ('#008080', '#ffffff', 'Teal'),
    ('#008B8B', '#ffffff', 'DarkCyan'),
    ('#00BFFF', '#ffffff', 'DeepSkyBlue'),
    ('#00CED1', '#ffffff', 'DarkTurquoise'),
    ('#00FA9A', '#ffffff', 'MediumSpringGreen'),
    ('#00FF00', '#ffffff', 'Lime'),
    ('#00FF7F', '#191970', 'SpringGreen'),
    ('#00FFFF', '#191970', 'Aqua'),
    ('#00FFFF', '#ffffff', 'Cyan'),
    ('#191970', '#ffffff', 'MidnightBlue'),
    ('#1E90FF', '#ffffff', 'DodgerBlue'),
    ('#20B2AA', '#2F4F4F', 'LightSeaGreen'),
    ('#228B22', '#ffffff', 'ForestGreen'),
    ('#2E8B57', '#ffffff', 'SeaGreen'),
    ('#2F4F4F', '#ffffff', 'DarkSlateGray'),
    ('#32CD32', '#ffffff', 'LimeGreen'),
    ('#3CB371', '#ffffff', 'MediumSeaGreen'),
    ('#40E0D0', '#2F4F4F', 'Turquoise'),
    ('#4169E1', '#ffffff', 'RoyalBlue'),
    ('#4682B4', '#ffffff', 'SteelBlue'),
    ('#483D8B', '#ffffff', 'DarkSlateBlue'),
    ('#48D1CC', '#2F4F4F', 'MediumTurquoise'),
    ('#4B0082', '#ffffff', 'Indigo'),
    ('#556B2F', '#ffffff', 'DarkOliveGreen'),
    ('#5F9EA0', '#ffffff', 'CadetBlue'),
    ('#6495ED', '#ffffff', 'CornflowerBlue'),
    ('#663399', '#ffffff', 'RebeccaPurple'),
    ('#66CDAA', '#2F4F4F', 'MediumAquaMarine'),
    ('#696969', '#ffffff', 'DimGray'),
    ('#6A5ACD', '#ffffff', 'SlateBlue'),
    ('#6B8E23', '#ffffff', 'OliveDrab'),
    ('#708090', '#ffffff', 'SlateGray'),
    ('#778899', '#333333', 'LightSlateGray'),
    ('#7B68EE', '#ffffff', 'MediumSlateBlue'),
    ('#7CFC00', '#6B8E23', 'LawnGreen'),
    ('#7FFF00', '#6B8E23', 'Chartreuse'),
    ('#7FFFD4', '#483D8B', 'Aquamarine'),
    ('#800000', '#ffffff', 'Maroon'),
    ('#800080', '#ffffff', 'Purple'),
    ('#808000', '#ffffff', 'Olive'),
    ('#808080', '#ffffff', 'Gray'),
    ('#87CEEB', '#191970', 'SkyBlue'),
    ('#87CEFA', '#191970', 'LightSkyBlue'),
    ('#8A2BE2', '#ffffff', 'BlueViolet'),
    ('#8B0000', '#ffffff', 'DarkRed'),
    ('#8B008B', '#ffffff', 'DarkMagenta'),
    ('#8B4513', '#ffffff', 'SaddleBrown'),
    ('#8FBC8F', '#191970', 'DarkSeaGreen'),
    ('#90EE90', '#191970', 'LightGreen'),
    ('#9370DB', '#9400D3', 'MediumPurple'),
    ('#9400D3', '#ffffff', 'DarkViolet'),
    ('#98FB98', '#ffffff', 'PaleGreen'),
    ('#9932CC', '#ffffff', 'DarkOrchid'),
    ('#9ACD32', '#ffffff', 'YellowGreen'),
    ('#A0522D', '#ffffff', 'Sienna'),
    ('#A52A2A', '#ffffff', 'Brown'),
    ('#A9A9A9', '#ffffff', 'DarkGray'),
    ('#ADD8E6', '#191970', 'LightBlue'),
    ('#ADFF2F', '#191970', 'GreenYellow'),
    ('#AFEEEE', '#191970', 'PaleTurquoise'),
    ('#B0C4DE', '#191970', 'LightSteelBlue'),
    ('#B0E0E6', '#191970', 'PowderBlue'),
    ('#B22222', '#ffffff', 'FireBrick'),
    ('#B8860B', '#ffffff', 'DarkGoldenRod'),
    ('#BA55D3', '#ffffff', 'MediumOrchid'),
    ('#BC8F8F', '#ffffff', 'RosyBrown'),
    ('#BDB76B', '#ffffff', 'DarkKhaki'),
    ('#C0C0C0', '#B22222', 'Silver'),
    ('#C71585', '#ffffff', 'MediumVioletRed'),
    ('#CD5C5C', '#ffffff', 'IndianRed'),
    ('#CD853F', '#ffffff', 'Peru'),
    ('#D2691E', '#ffffff', 'Chocolate'),
    ('#D2B48C', '#ffffff', 'Tan'),
    ('#D3D3D3', '#C71585', 'LightGray'),
    ('#D8BFD8', '#DC143C', 'Thistle'),
    ('#DA70D6', '#ffffff', 'Orchid'),
    ('#DAA520', '#ffffff', 'GoldenRod'),
    ('#DB7093', '#ffffff', 'PaleVioletRed'),
    ('#DC143C', '#ffffff', 'Crimson'),
    ('#DCDCDC', '#C71585', 'Gainsboro'),
    ('#DDA0DD', '#ffffff', 'Plum'),
    ('#DEB887', '#000000', 'BurlyWood'),
    ('#E0FFFF', '#000000', 'LightCyan'),
    ('#E6E6FA', '#000000', 'Lavender'),
    ('#E9967A', '#000000', 'DarkSalmon'),
    ('#EE82EE', '#000000', 'Violet'),
    ('#EEE8AA', '#000000', 'PaleGoldenRod'),
    ('#F08080', '#DC143C', 'LightCoral'),
    ('#F0E68C', '#ffffff', 'Khaki'),
    ('#F0F8FF', '#4169E1', 'AliceBlue'),
    ('#F0FFF0', '#F08080', 'HoneyDew'),
    ('#F0FFFF', '#DA70D6', 'Azure'),
    ('#F4A460', '#ffffff', 'SandyBrown'),
    ('#F5DEB3', '#FF0000', 'Wheat'),
    ('#F5F5DC', '#FA8072', 'Beige'),
    ('#F5F5F5', '#FF00FF', 'WhiteSmoke'),
    ('#F5FFFA', '#9370DB', 'MintCream'),
    ('#F8F8FF', '#777777', 'GhostWhite'),
    ('#FA8072', '#ffffff', 'Salmon'),
    ('#FAEBD7', '#111111', 'AntiqueWhite'),
    ('#FAF0E6', '#222222', 'Linen'),
    ('#FAFAD2', '#333333', 'LightGoldenRodYellow'),
    ('#FDF5E6', '#444444', 'OldLace'),
    ('#FF0000', '#ffffff', 'Red'),
    ('#FF00FF', '#ffffff', 'Fuchsia'),
    ('#FF00FF', '#ffffff', 'Magenta'),
    ('#FF1493', '#ffffff', 'DeepPink'),
    ('#FF4500', '#ffffff', 'OrangeRed'),
    ('#FF6347', '#ffffff', 'Tomato'),
    ('#FF69B4', '#DC143C', 'HotPink'),
    ('#FF7F50', '#ffffff', 'Coral'),
    ('#FF8C00', '#ffffff', 'DarkOrange'),
    ('#FFA07A', '#ffffff', 'LightSalmon'),
    ('#FFA500', '#ffffff', 'Orange'),
    ('#FFB6C1', '#444444', 'LightPink'),
    ('#FFC0CB', '#666666', 'Pink'),
    ('#FFD700', '#000000', 'Gold'),
    ('#FFDAB9', '#FF0000', 'PeachPuff'),
    ('#FFDEAD', '#FF00FF', 'NavajoWhite'),
    ('#FFE4B5', '#FF00FF', 'Moccasin'),
    ('#FFE4C4', '#FF1493', 'Bisque'),
    ('#FFE4E1', '#FF4500', 'MistyRose'),
    ('#FFEBCD', '#FF6347', 'BlanchedAlmond'),
    ('#FFEFD5', '#FF69B4', 'PapayaWhip'),
    ('#FFF0F5', '#FF7F50', 'LavenderBlush'),
    ('#FFF5EE', '#FF8C00', 'SeaShell'),
    ('#FFF8DC', '#228B22', 'Cornsilk'),
    ('#FFFACD', '#2E8B57', 'LemonChiffon'),
    ('#FFFAF0', '#2F4F4F', 'FloralWhite'),
    ('#FFFAFA', '#32CD32', 'Snow'),
    ('#FFFF00', '#3CB371', 'Yellow'),
    ('#FFFFE0', '#40E0D0', 'LightYellow'),
    ('#FFFFF0', '#4169E1', 'Ivory'),
    ('#FFFFFF', '#000000', 'White'),
]

class TagDescriptor(PropertySet):   
    id = Property()
    color_id = Property(int)
    background_color = Property()
    foreground_color = Property()
    color_name = Property()


class TagDescriptorFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


def get_tags():
    with get_db().transaction() as t:
        tags = t.query(Tag).order_by(Tag.id).all()

        return TagDescriptorFeed(
            count=len(tags),
            entries=[
                TagDescriptor(
                    id=tag.id,
                    color_id=tag.color,
                    background_color=colors[tag.color][0],
                    foreground_color=colors[tag.color][1],
                    color_title=colors[tag.color][2],
                ) for tag in tags
            ]
        )


def get_tag_by_id(id):
    with get_db().transaction() as t:
        tag = t.query(Tag).filter(Tag.id==id).one()

        return TagDescriptor(
            id=tag.id,
            color_id=tag.color,
            background_color=colors[tag.color][0],
            foreground_color=colors[tag.color][1],
            color_name=colors[tag.color][2],
        )


def delete_tag_by_id(id):
    with get_db().transaction() as t:
        t.query(Tag).filter(Tag.id==id).delete()


def add_tag(td):
    if not td.id:
        raise ValueError("Tag id must not be empty")

    with get_db().transaction() as t:
        tag = Tag()
        tag.id = td.id.lower()
        tag.color = td.color_id if td.color_id is not None else random.randrange(0, len(colors))
        t.add(tag)
        t.commit()
        id = tag.id

    return get_tag_by_id(id)


def ensure_tag(tag_id):
    """
    Check if a tag with id `tag_id` exists. If not, create it.
    """
    if not tag_id:
        raise ValueError("Tag id must not be empty")

    with get_db().transaction() as t:
        try:
            t.query(Tag).filter(Tag.id == tag_id).one()
        except NoResultFound:
            tag = Tag()
            tag.id = tag_id
            tag.color = random.randrange(0, len(colors))
            t.add(tag)
