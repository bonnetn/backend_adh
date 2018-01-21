from connexion import NoContent
from itertools import islice
from store import get_db
from model.database import Database as db
from model import models
import sqlalchemy


def is_wired(macAddress):
    """ Return true if the mac address corresponds to a wired device """
    session = db.get_db().get_session()
    queryWired = session.query(models.Ordinateur)
    queryWired = queryWired.filter(models.Ordinateur.mac == macAddress)

    return session.query(queryWired.exists()).scalar()


def is_wireless(macAddress):
    """ Return true if the mac address corresponds to a wireless device """
    session = db.get_db().get_session()
    queryWireless = session.query(models.Portable)
    queryWireless = queryWireless.filter(models.Portable.mac == macAddress)

    return session.query(queryWireless.exists()).scalar()


def get_adherent(body):
    s = db.get_db().get_session()
    q = s.query(models.Adherent)
    q = q.filter(models.Adherent.login == body['username'])
    return q.one()


def create_wireless_device(body):
    s = db.get_db().get_session()
    dev = models.Portable(
        mac=body['mac'],
        adherent=get_adherent(body),
    )
    s.add(dev)
    s.commit()


def create_wired_device(body):
    s = db.get_db().get_session()
    dev = models.Ordinateur(
        mac=body['mac'],
        adherent=get_adherent(body),
    )
    s.add(dev)
    s.commit()


def update_wireless_device(macAddress, body):
    s = db.get_db().get_session()
    q = s.query(models.Portable).filter(models.Portable.mac == macAddress)
    dev = q.one()
    dev.mac = body['mac']
    dev.adherent = get_adherent(body)
    s.commit()


def update_wired_device(macAddress, body):
    s = db.get_db().get_session()
    q = s.query(models.Ordinateur).filter(models.Ordinateur.mac == macAddress)
    dev = q.one()

    dev.mac = body['mac']
    dev.adherent = get_adherent(body)
    s.commit()


def delete_wireless_device(macAddress):
    s = db.get_db().get_session()
    q = s.query(models.Portable).filter(models.Portable.mac == macAddress)
    dev = q.one()
    s.delete(dev)
    s.commit()


def delete_wired_device(macAddress):
    s = db.get_db().get_session()
    q = s.query(models.Ordinateur).filter(models.Ordinateur.mac == macAddress)
    dev = q.one()
    s.delete(dev)
    s.commit()


def findInDevice(user, terms):
    txt = ""
    txt += user["mac"] + " "
    txt += user["ipAddress"] + " "
    txt += user["ipv6Address"] + " "
    return txt.lower().find(terms.lower()) != -1


def filterDevice(limit=100, username=None, terms=None):
    DEVICES = get_db()["DEVICES"]
    all_devices = list(DEVICES.values())

    if username is not None:
        all_devices = filter(lambda x: x["username"] == username, all_devices)

    if terms is not None:
        all_devices = filter(lambda x: findInDevice(x, terms), all_devices)

    return list(islice(all_devices, limit))


def putDevice(macAddress, body):
    try:
        wired = is_wired(macAddress)
        wireless = is_wireless(macAddress)
        wanted_type = body["connectionType"]

        if wired and wireless:
            if wanted_type == "wired":
                delete_wireless_device(macAddress)
                update_wired_device(macAddress, body)
            else:
                delete_wired_device(macAddress)
                update_wireless_device(macAddress, body)
        elif wired:
            if wanted_type == "wireless":
                delete_wired_device(macAddress)
                create_wireless_device(body)
            else:
                update_wired_device(macAddress, body)
        elif wireless:
            if wanted_type == "wired":
                delete_wireless_device(macAddress)
                create_wired_device(body)
            else:
                update_wireless_device(macAddress, body)
        else:  # Create device
            if wanted_type == "wired":
                create_wired_device(body)
            else:
                create_wireless_device(body)
            return NoContent, 201
        return NoContent, 204

    except sqlalchemy.orm.exc.NoResultFound:
        return 'Invalid username', 400


def getDevice(macAddress):
    s = db.get_db().get_session()
    if is_wireless(macAddress):
        q = s.query(models.Portable)
        q = q.filter(models.Portable.mac == macAddress)
        r = q.one()
        return {
            'username': r.adherent.login,
            'mac': r.mac,
        }, 200
    elif is_wired(macAddress):
        q = s.query(models.Ordinateur)
        q = q.filter(models.Ordinateur.mac == macAddress)
        r = q.one()
        return {
            'username': r.adherent.login,
            'mac': r.mac,
            'ipAddress': r.ip,
        }, 200
    else:
        return NoContent, 404


def deleteDevice(macAddress):
    s = db.get_db().get_session()
    if is_wireless(macAddress):
        q = s.query(models.Portable)
        q = q.filter(models.Portable.mac == macAddress)
        r = q.one()
        s.delete(r)
        s.commit()
        return NoContent, 204

    elif is_wired(macAddress):
        q = s.query(models.Ordinateur)
        q = q.filter(models.Ordinateur.mac == macAddress)
        r = q.one()
        s.delete(r)
        s.commit()
        return NoContent, 204

    else:
        return NoContent, 404
