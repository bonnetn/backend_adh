from connexion import NoContent
from adh.model.database import Database as db
from sqlalchemy import or_
from adh.exceptions import RoomNotFound, SwitchNotFound, PortNotFound
from adh.model.models import Port, Chambre, Switch
from adh.auth import auth_simple_user


@auth_simple_user
def filterPort(admin, limit=100, offset=0,
               switchID=None, roomNumber=None, terms=None):
    """ [API] Filter the port list according to some criteria """
    if limit < 0:
        return 'Limit must be a positive number', 400

    s = db.get_db().get_session()
    q = s.query(Port)
    if switchID:
        q = q.join(Switch)
        q = q.filter(Switch.id == switchID)
    if roomNumber:
        q = q.join(Chambre)
        q = q.filter(Chambre.numero == roomNumber)
    if terms:
        q = q.filter(or_(
            Port.numero.contains(terms),
            Port.oid.contains(terms),
        ))

    count = q.count()
    q = q.order_by(Port.switch_id.asc(), Port.numero.asc())
    q = q.offset(offset)
    q = q.limit(limit)
    result = q.all()

    result = map(dict, result)
    result = list(result)
    headers = {
        'access-control-expose-headers': 'X-Total-Count',
        'X-Total-Count': str(count)
    }
    return result, 200, headers


@auth_simple_user
def createPort(admin, switchID, body):
    """ [API] Create a port in the database """

    session = db.get_db().get_session()
    try:
        port = Port.from_dict(session, body)
    except SwitchNotFound:
        return "Switch not found", 400
    except RoomNotFound:
        return "Room not found", 400

    session.add(port)
    session.commit()
    headers = {
        'Location': '/switch/{}/port/{}'.format(port.switch_id, port.id)
    }
    return NoContent, 200, headers


@auth_simple_user
def getPort(admin, switchID, portID):
    """ [API] Get a port from the database """
    s = db.get_db().get_session()
    try:
        result = Port.find(s, portID)
    except PortNotFound:
        return NoContent, 404

    result = dict(result)
    return result, 200


@auth_simple_user
def updatePort(admin, switchID, portID, body):
    """ [API] Update a port in the database """

    s = db.get_db().get_session()

    try:
        new_port = Port.from_dict(s, body)
    except SwitchNotFound:
        return "Switch not found", 400

    try:
        new_port.id = Port.find(s, portID).id
    except PortNotFound:
        return "Port not found", 404

    s.merge(new_port)
    s.commit()

    return NoContent, 204


@auth_simple_user
def deletePort(admin, switchID, portID):
    """ [API] Delete a port from the database """
    session = db.get_db().get_session()
    try:
        session.delete(Port.find(session, portID))
    except PortNotFound:
        return NoContent, 404
    session.commit()
    return NoContent, 204
