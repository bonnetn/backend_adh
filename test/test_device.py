import json

import pytest
from adh.model.database import Database as db
from CONFIGURATION import TEST_DATABASE as db_settings
from adh.model.models import Ordinateur, Portable, Adherent

from .resource import (
    base_url, INVALID_MAC, INVALID_IP, INVALID_IPv6, TEST_HEADERS
)


@pytest.fixture
def member1():
    yield Adherent(
        nom='Dubois',
        prenom='Jean-Louis',
        mail='j.dubois@free.fr',
        login='dubois_j',
        password='a',
    )


@pytest.fixture
def member2():
    yield Adherent(
        nom='Reignier',
        prenom='Edouard',
        mail='bgdu78@hotmail.fr',
        login='reignier',
        password='b',
    )


@pytest.fixture
def wired_device(member1):
    yield Ordinateur(
        mac='96:24:F6:D0:48:A7',
        ip='157.159.42.42',
        dns='bonnet_n4651',
        adherent=member1,
        ipv6='e91f:bd71:56d9:13f3:5499:25b:cc84:f7e4'
    )


@pytest.fixture
def wireless_device(member2):
    yield Portable(
        mac='80:65:F3:FC:44:A9',
        adherent=member2,
    )


@pytest.fixture
def wireless_device_dict():
    '''
    Device that will be inserted/updated when tests are run.
    It is not present in the api_client by default
    '''
    yield {
      'mac': '01:23:45:67:89:AC',
      'ipAddress': '127.0.0.1',
      'ipv6Address': 'c69f:6c5:754c:d301:df05:ba81:76a8:ddc4',
      'connectionType': 'wireless',
      'username': 'dubois_j'
    }


@pytest.fixture
def wired_device_dict():
    yield {
      'mac': '01:23:45:67:89:AD',
      'ipAddress': '127.0.0.1',
      'ipv6Address': 'dbb1:39b7:1e8f:1a2a:3737:9721:5d16:166',
      'connectionType': 'wired',
      'username': 'dubois_j'
    }


def prep_db(session,
            member1,
            member2,
            wired_device,
            wireless_device):
    session.add_all([
        member1,
        member2,
        wired_device,
        wireless_device
    ])
    session.commit()


@pytest.fixture
def api_client(member1,
               member2,
               wired_device,
               wireless_device):
    from .context import app
    with app.app.test_client() as c:
        db.init_db(db_settings, testing=True)
        prep_db(db.get_db().get_session(),
                member1,
                member2,
                wired_device,
                wireless_device)
        yield c


def test_device_filter_all_devices(api_client):
    r = api_client.get(
        '{}/device/'.format(base_url),
        headers=TEST_HEADERS,
    )
    assert r.status_code == 200

    response = json.loads(r.data.decode('utf-8'))
    assert len(response) == 2


@pytest.mark.parametrize('user,expected', [
    ('reignier', 1),
    ('dubois_j', 1),
    ('gates_bi', 0),  # Non existant user
    ('dubois', 0),    # Exact match
])
def test_device_filter_wired_by_username(
        api_client, user, expected):
    r = api_client.get(
        '{}/device/?username={}'.format(
            base_url,
            user
        ),
        headers=TEST_HEADERS
    )
    assert r.status_code == 200

    response = json.loads(r.data.decode('utf-8'))
    assert len(response) == expected


@pytest.mark.parametrize('terms,expected', [
    ('96:24:F6:D0:48:A7', 1),   # Should find sample wired device
    ('96:', 1),
    ('e91f', 1),
    ('157.159', 1),
    ('80:65:F3:FC:44:A9', 1),  # Should find sample wireless device
    ('F3:FC', 1),
    (':', 2),                  # Should find everything
    ('00:', 0),                # Should find nothing
])
def test_device_filter_by_terms(
        api_client, wired_device, terms, expected):
    r = api_client.get(
        '{}/device/?terms={}'.format(
            base_url,
            terms,
        ),
        headers=TEST_HEADERS
    )
    assert r.status_code == 200

    response = json.loads(r.data.decode('utf-8'))
    assert len(response) == expected


def test_device_filter_invalid_limit(api_client, member1):
    r = api_client.get(
        '{}/device/?limit={}'.format(base_url, -1),
        headers=TEST_HEADERS
    )
    assert r.status_code == 400


def test_device_filter_hit_limit(api_client, member1):
    s = db.get_db().get_session()
    LIMIT = 10

    # Create a lot of devices
    for i in range(LIMIT*2):
        suffix = "{0:04X}".format(i)
        dev = Portable(
            adherent=member1,
            mac='00:00:00:00:'+suffix[:2]+":"+suffix[2:]
        )
        s.add(dev)
    s.commit()

    r = api_client.get(
        '{}/device/?limit={}'.format(base_url, LIMIT),
        headers=TEST_HEADERS,
    )
    assert r.status_code == 200

    response = json.loads(r.data.decode('utf-8'))
    assert len(response) == LIMIT


def test_device_put_create_wireless_without_ip(api_client,
                                               wireless_device_dict):
    ''' Can create a valid wireless device ? '''
    del wireless_device_dict['ipAddress']
    addr = '{}/device/{}'.format(base_url, wireless_device_dict['mac'])
    r = api_client.put(addr,
                       data=json.dumps(wireless_device_dict),
                       content_type='application/json',
                       headers=TEST_HEADERS)
    assert r.status_code == 201


def test_device_put_create_wireless(api_client, wireless_device_dict):
    ''' Can create a valid wireless device ? '''
    addr = '{}/device/{}'.format(base_url, wireless_device_dict['mac'])
    r = api_client.put(addr,
                       data=json.dumps(wireless_device_dict),
                       content_type='application/json',
                       headers=TEST_HEADERS)
    assert r.status_code == 201


def test_device_put_create_wired_without_ip(api_client, wired_device_dict):
    ''' Can create a valid wired device ? '''
    del wired_device_dict['ipAddress']
    r = api_client.put('{}/device/{}'.format(base_url,
                                             wired_device_dict['mac']),
                       data=json.dumps(wired_device_dict),
                       content_type='application/json',
                       headers=TEST_HEADERS)
    assert r.status_code == 201


def test_device_put_create_wired(api_client, wired_device_dict):
    ''' Can create a valid wired device ? '''
    r = api_client.put('{}/device/{}'.format(base_url,
                                             wired_device_dict['mac']),
                       data=json.dumps(wired_device_dict),
                       content_type='application/json',
                       headers=TEST_HEADERS)
    assert r.status_code == 201


def test_device_put_create_different_mac_addresses(api_client,
                                                   wired_device_dict):
    ''' Create with invalid mac address '''
    wired_device_dict['mac'] = "11:11:11:11:11:11"
    r = api_client.put('{}/device/{}'.format(base_url, "22:22:22:22:22:22"),
                       data=json.dumps(wired_device_dict),
                       content_type='application/json',
                       headers=TEST_HEADERS)
    assert r.status_code == 400


@pytest.mark.parametrize('test_mac', INVALID_MAC)
def test_device_put_create_invalid_mac_address(api_client,
                                               test_mac,
                                               wired_device_dict):
    ''' Create with invalid mac address '''
    wired_device_dict['mac'] = test_mac
    r = api_client.put(
        '{}/device/{}'.format(base_url, wired_device_dict['mac']),
        data=json.dumps(wired_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS,
    )
    assert r.status_code == 400 or r.status_code == 405


@pytest.mark.parametrize('test_ip', INVALID_IPv6)
def test_device_put_create_invalid_ipv6(api_client, test_ip,
                                        wired_device_dict):
    ''' Create with invalid ip address '''
    wired_device_dict['ipv6Address'] = test_ip
    r = api_client.put(
        '{}/device/{}'.format(base_url, wired_device_dict['mac']),
        data=json.dumps(wired_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS,
    )
    assert r.status_code == 400


@pytest.mark.parametrize('test_ip', INVALID_IP)
def test_device_put_create_invalid_ipv4(api_client, test_ip,
                                        wired_device_dict):
    ''' Create with invalid ip address '''
    wired_device_dict['ipAddress'] = test_ip
    r = api_client.put(
        '{}/device/{}'.format(base_url, wired_device_dict['mac']),
        data=json.dumps(wired_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS,
    )
    assert r.status_code == 400


def test_device_put_create_invalid_username(api_client, wired_device_dict):
    ''' Create with invalid mac address '''
    wired_device_dict['username'] = 'abcdefgh'
    r = api_client.put(
        '{}/device/{}'.format(base_url, wired_device_dict['mac']),
        data=json.dumps(wired_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS,
    )
    assert r.status_code == 400


def test_device_put_update_wireless(api_client, wireless_device,
                                    wireless_device_dict):
    ''' Can update a valid wireless device ? '''
    r = api_client.put(
        '{}/device/{}'.format(base_url, wireless_device.mac),
        data=json.dumps(wireless_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS)
    assert r.status_code == 204


def test_device_put_update_wired(api_client, wired_device, wired_device_dict):
    ''' Can update a valid wired device ? '''
    r = api_client.put(
        '{}/device/{}'.format(base_url, wired_device.mac),
        data=json.dumps(wired_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS)
    assert r.status_code == 204


def test_device_put_update_wired_to_wireless(api_client, wired_device,
                                             wireless_device_dict):
    ''' Can update a valid wired device and cast it into a wireless d ? '''
    r = api_client.put(
        '{}/device/{}'.format(base_url, wired_device.mac),
        data=json.dumps(wireless_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS)
    assert r.status_code == 204


def test_device_put_update_wireless_to_wired(api_client,
                                             wireless_device,
                                             wired_device_dict):
    ''' Can update a valid wireless device and cast it into a wired d ? '''
    r = api_client.put(
        '{}/device/{}'.format(base_url, wireless_device.mac),
        data=json.dumps(wired_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS)
    assert r.status_code == 204


def test_device_put_update_wired_and_wireless_to_wireless(
        api_client,
        wired_device,
        wireless_device_dict):
    '''
    Test if the controller is able to handle the case where the MAC address is
    in the Wireless table _AND_ the Wired table
    Tests the case where we want to move the mac to the wireless table
    '''
    # Add a wireless device that has the same mac as WIRED_DEVICE
    dev_with_same_mac = Portable(
        mac=wired_device.mac,
        adherent_id=1,
    )
    session = db.get_db().get_session()
    session.add(dev_with_same_mac)
    session.commit()

    # Then try to update it...
    r = api_client.put(
        '{}/device/{}'.format(base_url, wired_device.mac),
        data=json.dumps(wireless_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS)
    assert r.status_code == 204


def test_device_put_update_wired_and_wireless_to_wired(api_client,
                                                       wireless_device,
                                                       wired_device_dict):
    '''
    Test if the controller is able to handle the case where the MAC address is
    in the Wireless table _AND_ the Wired table
    Tests the case where we want to move the mac to the wired table
    '''
    # Add a wired device that has the same mac as WIRELESS_DEVICE
    dev_with_same_mac = Ordinateur(
        mac=wireless_device.mac,
        adherent_id=1,
    )
    session = db.get_db().get_session()
    session.add(dev_with_same_mac)
    session.commit()

    # Then try to update it...
    r = api_client.put(
        '{}/device/{}'.format(base_url, wireless_device.mac),
        data=json.dumps(wired_device_dict),
        content_type='application/json',
        headers=TEST_HEADERS)
    assert r.status_code == 204


def test_device_get_unknown_mac(api_client):
    mac = '00:00:00:00:00:00'
    r = api_client.get(
        '{}/device/{}'.format(base_url, mac),
        headers=TEST_HEADERS,
    )
    assert r.status_code == 404


def test_device_get_valid_wired(api_client, wired_device):
    mac = wired_device.mac
    r = api_client.get(
        '{}/device/{}'.format(base_url, mac),
        headers=TEST_HEADERS,
    )
    assert r.status_code == 200
    assert json.loads(r.data.decode('utf-8'))


def test_device_get_valid_wireless(api_client, wireless_device):
    mac = wireless_device.mac
    r = api_client.get(
        '{}/device/{}'.format(base_url, mac),
        headers=TEST_HEADERS,
    )
    assert r.status_code == 200
    assert json.loads(r.data.decode('utf-8'))


def test_device_delete_wired(api_client, wired_device):
    mac = wired_device.mac
    r = api_client.delete(
        '{}/device/{}'.format(base_url, mac),
        headers=TEST_HEADERS,
    )
    assert r.status_code == 204

    s = db.get_db().get_session()
    q = s.query(Ordinateur)
    q = q.filter(Ordinateur.mac == mac)
    assert not s.query(q.exists()).scalar(), "Object not actually deleted"


def test_device_delete_wireless(api_client, wireless_device):
    mac = wireless_device.mac
    r = api_client.delete(
        '{}/device/{}'.format(base_url, mac),
        headers=TEST_HEADERS,
    )
    assert r.status_code == 204

    s = db.get_db().get_session()
    q = s.query(Portable)
    q = q.filter(Portable.mac == mac)
    assert not s.query(q.exists()).scalar(), "Object not actually deleted"


def test_device_delete_unexistant(api_client):
    mac = '00:00:00:00:00:00'
    r = api_client.delete(
        '{}/device/{}'.format(base_url, mac),
        headers=TEST_HEADERS,
    )
    assert r.status_code == 404
