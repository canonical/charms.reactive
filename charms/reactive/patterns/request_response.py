import sys
import weakref
from uuid import uuid4

from charms.reactive.flags import toggle_flag
from charms.reactive.endpoints import Endpoint


__all__ = [
    'Field',
    'BaseRequest',
    'BaseResponse',
    'RequesterEndpoint',
    'ResponderEndpoint',
]


class SetNameBackport(type):
    """
    Metaclass to backport the __set_name__ behavior for data descriptors,
    which was added in Python 3.6, to earlier versions.
    """
    if sys.version_info[0:2] < (3, 6):
        def __init__(cls, name, bases, namespace):
            super().__init__(name, bases, namespace)
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name)
                if hasattr(attr, '__set_name__'):
                    attr.__set_name__(cls, attr_name)


class Field(property):
    """
    Defines a Field property for a Request or Response object.

    Can be set or retrieved like a normal attribute, and will be automatically
    serialized over the relation using JSON.
    """
    def __init__(self, description):
        self.__doc__ = description
        self._class = None
        self._name = None

    def __repr__(self):
        return '<Field {}.{}>'.format(self._class, self._name)

    def __set_name__(self, owner, name):
        self._class = owner.__name__
        self._name = name

    def __set__(self, instance, value):
        instance._update_field(self._name, value)

    def __get__(self, instance, owner):
        if instance is None:
            # called as class attribute, so return the Field instance instead
            # of blowing up on None not having a _get_field method (also allows
            # introspecting the class to find the fields)
            return self
        else:
            return instance._get_field(self._name)


class FieldHolderDictProxy(dict):
    """
    Base class for field holders that makes it act like a dict for easy
    serialization.
    """
    def __init__(self):
        cls = type(self)
        super().__init__({attr_name: getattr(self, attr_name)
                          for attr_name in dir(cls)
                          if isinstance(getattr(cls, attr_name), Field)})

    def _update_field(self, field_name, field_value):
        self[field_name] = field_value


class BaseRequest(FieldHolderDictProxy, metaclass=SetNameBackport):
    """
    Base class for requests using the request / response pattern.

    Subclasses **must** set the ``RESPONSE_CLASS`` attribute to a subclass of
    the :class:`BaseResponse` which defines the fields that the response will
    use.  They must also define additional attributes as :class:`Field`s.

    For example::

        class TLSResponse(BaseResponse):
            key = Field('Private key for the cert')
            cert = Field('Public cert info')


        class TLSRequest(BaseRequest):
            RESPONSE_CLASS = TLSResponse

            common_name = Field('Common Name (CN) for the cert to be created')
            sans = Field('List of Subject Alternative Names (SANs)')
    """
    RESPONSE_CLASS = None  # must be defined by subclass

    request_id = Field('UUID for this request.  Will be automatically generated.')

    _cache = None

    @classmethod
    def _load(cls, request_sources):
        """
        Load the requests and any associated responses from relation data.

        Must be called prior to requests being accessed.  This is done
        automatically by :class:`RequesterEndpoint` and
        :class:`ResponderEndpoint` base classes.

        :param request_sources: Where the requests should be loaded from.
          For example, the Endpoint initiating requests would use
          ``self.relations`` while the Endpoint processing requests might use
          ``self.all_joined_units``.
        """
        cls._cache = {}  # set here so that each subclass gets its own cache
        for source in request_sources:
            requests = (source.to_publish if hasattr(source, 'to_publish')
                        else source.received)
            for key, request_data in requests.items():
                if not key.startswith('request_'):
                    continue
                request = cls(source, request_data['request_id'])
                request.response = cls.RESPONSE_CLASS._load(request)
                cls._cache[request.request_id] = request

    @classmethod
    def create(cls, relation, **fields):
        """
        Create a new request.

        Fields and their values can be passed in to pre-populate the request as
        keyword arguments, or can be set individually on the resulting request.
        """
        request_id = fields.setdefault('request_id', str(uuid4()))
        # pre-populate the field data directly in the data store (more
        # efficient than calling _update_field for every field)
        relation.to_publish['request_' + request_id] = fields
        cls._cache[request_id] = cls(relation, request_id)
        return cls._cache[request_id]

    @classmethod
    def get(cls, request_id):
        """
        Get a specific request by ID.
        """
        return cls._cache.get(request_id)

    @classmethod
    def get_all(cls):
        """
        Get a list of all requests (in order of their ID).
        """
        return sorted(cls._cache.values(), key=lambda r: r._id)

    @classmethod
    def find(cls, relation=None, **fields):
        """
        Find the first request whose fields match the given values.

        :param relation: If given, look for the request on a specific relation.
        :param **fields: Name / value pairs to match by.
        """
        for request in cls._cache.values():
            if all(getattr(request, field_name) == field_value
                   for field_name, field_value in fields.items()):
                return request
        else:
            return None

    @classmethod
    def find_all(cls, **fields):
        """
        Find all requests whose fields match the given values.

        :param **fields: Name / value pairs to match by.
        """
        found = []
        for request in cls._cache.values():
            if all(getattr(request, field_name) == field_value
                   for field_name, field_value in fields.items()):
                found.append(request)
        return found

    @classmethod
    def create_or_update(cls, match_fields, relation, **fields):
        """
        Find a request and update it, or create a new one.

        If multiple requests match, only the first one is updated.

        :param match_fields: List of the field names to match by.
        :param relation: Relation to find or create the request on.
        :param **fields: Name / value pairs to match by and update to.
        :returns: The new or updated request.

        Example::

            for relation in self.relations:
                JobRequest.create_or_update(match_fields=['job_name'],
                                            relation=relation,
                                            job_name='foo',
                                            job_data=job_data)
        """
        request = cls.find(relation, **{field: fields[field]
                                        for field in match_fields})
        if request:
            # update
            for field_name, field_value in fields.items():
                request._update_field(field_name, field_value)
        else:
            # create
            request = cls.create(relation, **fields)
        return request

    def __init__(self, source, request_id):
        if self.RESPONSE_CLASS is None:
            raise TypeError('RESPONSE_CLASS must be defined by subclass')
        self._id = request_id  # cache the ID so that we can determine the key
        self._source = source
        self.response = None
        if self.is_received:
            self._source_data = source.received
        else:
            self._source_data = source.to_publish
        super().__init__()

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self._id)

    @property
    def _key(self):
        return 'request_{}'.format(self._id)

    @property
    def is_created(self):
        """
        Whether this request was created by this side of the relation.
        """
        return hasattr(self._source, 'to_publish')

    @property
    def is_received(self):
        """
        Whether this request was received by the other side of the relation.
        """
        return not self.is_created

    def create_response(self, **fields):
        """
        Create a response to this request.

        Fields and their values can be passed in to pre-populate the response
        as keyword arguments, or can be set individually on the resulting
        response.

        Returns the response object (which can also be accessed as
        ``request.response``).
        """
        self.response = self.RESPONSE_CLASS.create(self, **fields)
        return self.response

    def respond(self, **fields):
        """
        Respond to this request.  (Alias of :meth:`create_response`.)

        Fields and their values can be passed in to pre-populate the response
        as keyword arguments, or can be set individually on the resulting
        response.

        Returns the response object (which can also be accessed as
        ``request.response``).
        """
        return self.create_response(**fields)

    def _get_field(self, name):
        return self._source_data.get(self._key, {}).get(name)

    def _update_field(self, name, value):
        if self.is_received:
            raise AttributeError("can't change field for received request")
        if name == 'request_id':
            raise AttributeError("request_id can't be modified")
        data = self._source_data[self._key]
        data[name] = value
        # reading serialized dict gets a copy, so we have to explicitly write
        # it back to ensure updated items get written
        self._source_data[self._key] = data
        # update the proxy for serialization
        super()._update_field(name, value)

    @property
    def ingress_address(self):
        """
        Address to use if a connection to the requester is required.
        """
        return self._source_data['ingress-address']

    @property
    def egress_subnets(self):
        """
        Subnets over which network traffic to the requester will flow.
        """
        return self._source_data['egress-subnets']


class BaseResponse(FieldHolderDictProxy, metaclass=SetNameBackport):
    """
    Base class for responses using the request / response pattern.
    """
    @classmethod
    def _load(cls, request):
        response = cls(request)
        if response._key not in response._source_data:
            return None  # no response found
        else:
            return response

    @classmethod
    def create(cls, request, **fields):
        """
        Create a response to the given request.

        Fields and their values can be passed in to pre-populate the response
        as keyword arguments, or can be set individually on the resulting
        response.
        """
        if request.is_created:
            raise ValueError("can't respond to requests we created")
        # pre-populate the field data directly in the data store (more
        # efficient than calling _update_field for every field)
        request._source.relation.to_publish['response_' + request.request_id] = fields
        response = cls(request)
        request.response = response
        return response

    def __init__(self, request):
        self.request = weakref.proxy(request)
        if request.is_received:
            self._source_data = request._source.relation.to_publish
        else:
            for unit in request._source.joined_units:
                if self._key in unit.received:
                    self._source_data = unit.received
                    break
            else:
                self._source_data = {}
        super().__init__()

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self.request._id)

    @property
    def _key(self):
        return 'response_{}'.format(self.request.request_id)

    @property
    def is_received(self):
        return not self.request.is_received

    def _get_field(self, name):
        return self._source_data.get(self._key, {}).get(name)

    def _update_field(self, name, value):
        if self.is_received:
            raise AttributeError("can't change field for received response")
        data = self._source_data[self._key]
        data[name] = value
        # reading serialized dict gets a copy, so we have to explicitly write
        # it back to ensure updated items get written
        self._source_data[self._key] = data
        # update the proxy for serialization
        super()._update_field(name, value)


class FieldFinders(type):
    """
    Metaclass for defining ``response_by_FIELD`` methods on
    ``RequesterEndpoint`` classes.

    This is done as a metaclass to handle fields on derived classes but
    to still allow the methods to show up in the class's documentation.
    """
    # Is this too much magic?  Should we just provide response_by_field
    # and leave it up to the endpoint author to define which search methods
    # make sense?
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        for field_name in dir(cls.REQUEST_CLASS):
            field = getattr(cls.REQUEST_CLASS, field_name)
            if not isinstance(field, Field):
                continue

            def _make_finder(field_name):
                # has to be nested to make closure work properly
                def _finder(self, field_value, relation=None):
                    return self.response_by_field(**{field_name: field_value,
                                                     'relation': relation})
                _finder.__name__ = 'response_by_{}'.format(field_name)
                _finder.__doc__ = """
                    Find the response by the value of its request's {} field.

                    If ``relation`` is given, limit the search to that
                    relation.
                    """.format(field_name)
                return _finder
            _finder = _make_finder(field_name)
            setattr(cls, _finder.__name__, _finder)


class RequesterEndpoint(Endpoint, metaclass=FieldFinders):
    """
    Base class for Endpoints that create requests in the request / response
    pattern.

    Subclasses **must** set the ``REQUEST_CLASS`` attribute to a subclass
    of :class:`BaseRequest` which defines the fields the request will use.

    Will automatically manage the following flags:

      * ``endpoint.{endpoint_name}.has_responses`` Set if any responses are
        available
      * ``endpoint.{endpoint_name}.all_responses`` Set if all requests have
        responses.
    """
    REQUEST_CLASS = None  # must be defined by subclass

    def __init__(self, *args, **kwargs):
        if self.REQUEST_CLASS is None:
            raise TypeError('REQUEST_CLASS must be defined by subclass')
        super().__init__(*args, **kwargs)
        self.REQUEST_CLASS._load(self.relations)

    def _manage_flags(self):
        super()._manage_flags()
        toggle_flag(self.expand_name('endpoint.{endpoint_name}.has_responses'),
                    self.responses)
        toggle_flag(self.expand_name('endpoint.{endpoint_name}.all_responses'),
                    len(self.responses) == len(self.requests))

    @property
    def requests(self):
        """
        A list of all requests which have been submitted.
        """
        return self.REQUEST_CLASS.get_all()

    @property
    def responses(self):
        """
        A list of all responses which have been received.
        """
        return [request.response
                for request in self.requests
                if request.response is not None]

    def response_by_field(self, relation=None, **fields):
        """
        Find a response by the value(s) of fields on its request.

        :param relation: If given, limit the search to that relation.
        :param **fields: Name / value pairs to match by.
        """
        request = self.REQUEST_CLASS.find(relation=relation, **fields)
        return request.response if request else None


class ResponderEndpoint(Endpoint):
    """
    Base class for Endpoints that respond to requests in the request / response
    pattern.

    Subclasses **must** set the ``REQUEST_CLASS`` attribute to a subclass
    of :class:`BaseRequest` which defines the fields the request will use.

    Will automatically manage the following flags:

      * ``endpoint.{endpoint_name}.has_requests`` Set if any requests are
        available
      * ``endpoint.{endpoint_name}.new_requests`` Set if any unhandled requests
        are available.
    """
    REQUEST_CLASS = None  # must be defined by subclass

    def __init__(self, *args, **kwargs):
        if self.REQUEST_CLASS is None:
            raise TypeError('REQUEST_CLASS must be defined by subclass')
        super().__init__(*args, **kwargs)
        self.REQUEST_CLASS._load(self.all_joined_units)

    def _manage_flags(self):
        super()._manage_flags()
        toggle_flag(self.expand_name('endpoint.{endpoint_name}.has_requests'),
                    self.all_requests)
        toggle_flag(self.expand_name('endpoint.{endpoint_name}.new_requests'),
                    self.new_requests)

    @property
    def all_requests(self):
        """
        A list of all requests, including ones which have been responded to.
        """
        return self.REQUEST_CLASS.get_all()

    @property
    def new_requests(self):
        """
        A list of requests which have not been responded.

        Requests should be handled by the charm and then responded to by
        calling ``request.respond(...)``.
        """
        return list(filter(lambda request: request.response is None,
                           self.all_requests))
