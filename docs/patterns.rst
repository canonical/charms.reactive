Patterns
========

When creating charms, layers, or interface layers with reactive, some common
patterns can come up.  This page documents some of them.

Request / Response
------------------

A common pattern in interface layers is for one charm to generate individual
requests, which then need to be paired with a specific response from the other
charm.  This can be tricky to accomplish with relation data, due to the fact
that a given unit can only publish its data for the entire relation, rather
than a specific remote unit, plus the fact that a given unit may want to submit
multiple requests.  The framework provides some base classes to assist with
this pattern.

An interface layer would first define a request and response type, which
inherit from
:class:`~charms.reactive.patterns.request_response.BaseRequest` and
:class:`~charms.reactive.patterns.request_response.BaseResponse` respectively,
and which each define a set of
:class:`~charms.reactive.patterns.request_response.Field` attributes to hold
the data for the request and response.  Each field can provide a description,
for documentation purposes.

.. note:: The request class must explicitly point to the class which implements
    the associated response, via the ``RESPONSE_CLASS`` attribute, so that the
    correct class can be used when creating responses to requests.

For example::

    from charms.reactive import BaseRequest, BaseResponse, Field


    class CertResponse(BaseResponse):
        signed_cert = Field(description="""
                            The text of the public certificate signed by the CA.
                            """)

    class CertRequest(BaseRequest):
        RESPONSE_CLASS = CertResponse  # point to response implementation

        csr_data = Field(description="""
                         The text of the generated Certificate Signing Request.
                         """)

Then, the interface layer would define endpoint classes which inherit from
:class:`~charms.reactive.patterns.request_response.RequesterEndpoint`
and
:class:`~charms.reactive.patterns.request_response.ResponderEndpoint`
rather than directly from :class:`~charms.reactive.endpoints.Endpoint`.
These classes would point to the appropriate request implementation to use via
the ``REQUEST_CLASS`` attribute, and they would inherit various properties and
methods for interacting with the requests and responses (although it may make
sense for them to wrap some of these with methods of their own more specialized
for their specific needs).

For example::

    from charms.reactive import RequesterEndpoint, ResponderEndpoint


    class CertRequester(RequesterEndpoint):
        REQUEST_CLASS = CertRequest  # point to request implementation

        @property
        def related_cas(self):
            """
            A list of the related CAs which can sign certs.
            """
            return self.relations

        def send_csr(self, related_ca, csr_data):
            """
            Send a CSR to the specified related CA.

            Returns the created request.
            """
            return CertRequest.create(relation=related_ca,
                                      csr_data=csr_data)


    class CertResponder(ResponderEndpoint):
        REQUEST_CLASS = CertRequest  # point to request implementation

        # no additional implementation needed beyond the inherited properties / methods

Charms using this interface layer could then submit requests and provide responses.

For example, a client charm might look something like::

    @when('endpoint.certs.joined')
    @when_not('charm.cert_requested')
    def request_cert():
        cert_provider = endpoint_from_name('certs')
        if len(cert_provider.related_cas) == 0:
            return
        if len(cert_provider.related_cas) > 1:
            status.blocked('Too many CAs')
            return
        ca = cert_provider.related_cas[0]
        csr_data = generate_csr()
        request = cert_provider.send_csr(ca, csr_data)
        unitdata.kv().set('current_cert_request', request.request_id)  # for reissues
        set_flag('charm.cert_requested')

    @when('endpoint.certs.all_responses')
    def write_cert():
        cert_provider = endpoint_from_name('certs')
        current_request = unitdata.kv().get('current_cert_request')  # handle reissues
        response = cert_provider.response_by_field(request_id=current_request)
        CERT_PATH.write_text(response.signed_cert)

And the corresponding provider charm might look something like::

    @when('endpoint.cert_clients.new_requests')
    def sign_certs():
        cert_clients = endpoint_from_name('cert_clients')
        for request in cert_clients.new_requests:
            signed_cert = sign_cert(request.csr_data)
            request.respond(signed_cert=signed_cert)
