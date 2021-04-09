# Copyright 2019 Canonical Limited.
#
# This file is part of charms.reactive.
#
# charms.reactive is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

import json
from mock import Mock, patch

from charms.reactive import (
    Field,
    BaseRequest,
    BaseResponse,
    RequesterEndpoint,
    ResponderEndpoint,
)


class TResponse(BaseResponse):
    actual_foo = Field('The fooness actually provided')
    actual_bar = Field('The barness actually provided')


class TRequest(BaseRequest):
    RESPONSE_CLASS = TResponse
    foo = Field('The fooness requested')
    bar = Field('The barness requested')


class TRequester(RequesterEndpoint):
    REQUEST_CLASS = TRequest

    rel = Mock(name='req_rel',
               spec=['to_publish', 'joined_units'],
               to_publish={})
    unit = Mock(name='req_unit',
                spec=['relation', 'received'],
                relation=rel,
                received=rel.to_publish)

    _endpoint_name = 'requester'
    _relations = [rel]
    _all_joined_units = []

    def __init__(self):
        # patch out Endpoint's init so that we just use our mock relation data
        # but can still test the RequesterEndpoint init logic
        with patch('charms.reactive.endpoints.Endpoint.__init__'):
            super().__init__()


class TRequester2(TRequester):
    rel = Mock(name='req_rel2',
               spec=['to_publish', 'joined_units'],
               to_publish={})
    unit = Mock(name='req_unit2',
                spec=['relation', 'received'],
                relation=rel,
                received=rel.to_publish)
    _relations = [rel]
    _all_joined_units = []


class TResponder(ResponderEndpoint):
    REQUEST_CLASS = TRequest

    rel = Mock(name='res_rel',
               spec=['to_publish', 'joined_units'],
               to_publish={})
    unit = Mock(name='res_unit',
                spec=['relation', 'received'],
                relation=rel,
                received=rel.to_publish)

    _endpoint_name = 'responder'
    _relations = [rel]
    _all_joined_units = []

    def __init__(self):
        # patch out Endpoint's init so that we just use our mock relation data
        # but can still test the ResponderEndpoint init logic
        with patch('charms.reactive.endpoints.Endpoint.__init__'):
            super().__init__()


def test_request_response():
    # hook up the relations so that each side sees the other side's unit
    TRequester.rel.joined_units = [TResponder.unit]
    TRequester._all_joined_units = [TResponder.unit]
    TResponder.rel.joined_units = [TRequester.unit]
    TResponder._all_joined_units = [TRequester.unit]

    requester = TRequester()

    assert len(requester.requests) == 0
    assert len(requester.responses) == 0

    req1 = TRequest.create(requester.rel, foo='foo', bar='bar')
    req2 = TRequest.create(requester.rel, foo='unfoo', bar='unbar')
    assert len(requester.requests) == 2
    assert len(requester.responses) == 0
    assert len(req1.request_id) > 0
    assert len(req2.request_id) > 0
    assert TRequest.find(foo='foo') is req1
    assert TRequest.find(bar='unbar') is req2
    assert TRequest.find(foo='other') is None

    responder = TResponder()
    assert len(responder.all_requests) == 2
    assert len(responder.new_requests) == 2

    rreq1 = TRequest.find(foo='foo')
    rreq2 = TRequest.find(foo='unfoo')
    rreq1.create_response(actual_foo='FOO', actual_bar='BAR')
    rreq2.create_response(actual_foo='unfoo', actual_bar='unbar')
    assert len(responder.all_requests) == 2
    assert len(responder.new_requests) == 0

    assert len(requester.requests) == 2
    assert len(requester.responses) == 2

    res1 = requester.response_by_foo('foo')
    res2 = requester.response_by_bar('unbar')
    assert res1
    assert res2
    assert requester.response_by_foo('other') is None
    assert requester.response_by_foo('FOO') is None
    assert (res1.actual_foo, res1.actual_bar) == ('FOO', 'BAR')
    assert (res2.actual_foo, res2.actual_bar) == ('unfoo', 'unbar')

    # verify that they can be serialized
    assert json.dumps(req1) != '{}'
    assert json.dumps(res1) != '{}'


def test_multi_request(req_id=None):
    # hook up the relations so that each side sees the other side's unit
    TRequester.rel.joined_units = [TResponder.unit]
    TRequester._all_joined_units = [TResponder.unit]
    TResponder.rel.joined_units = [TRequester.unit, TRequester2.unit]
    TResponder._all_joined_units = [TRequester.unit, TRequester2.unit]

    TRequester.rel.to_publish.clear()
    TRequester2.rel.to_publish.clear()

    requester1 = TRequester()
    requester2 = TRequester2()
    responder = TResponder()

    TRequest._load([])
    assert len(requester1.requests) == 0
    assert len(requester1.responses) == 0
    assert len(responder.all_requests) == 0

    TRequest._load([requester1.rel])
    req1 = TRequest.create_or_update(
        match_fields=['foo'],
        relation=requester1.rel,
        request_id=req_id,
        foo='foo',
        bar='bar',
    )
    # re-update same request
    TRequest.create_or_update(
        match_fields=['foo'],
        relation=requester1.rel,
        request_id=req_id,
        foo='foo',
        bar='bar',
    )
    TRequest._load([requester2.rel])
    req2 = TRequest.create_or_update(
        match_fields=['foo'],
        relation=requester2.rel,
        request_id=req_id,
        foo='foo',
        bar='bar',
    )
    assert req1 is not req2
    TRequest._load(TResponder.rel.joined_units)
    expected = 2 if req_id is None else 1
    assert len(responder.all_requests) == expected


def test_explicit_id_dedupe():
    test_multi_request('req:1')
