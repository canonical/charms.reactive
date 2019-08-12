Patterns
========

When creating charms, layers, or interface layers with reactive, some common
patterns can come up.  This page documents some of them.

Request / Response
------------------

A common pattern in interface layers is for one charm to generate individual
requests, which then need to be paired with a specific response from the other
charm.  This can be tricky to accomplish with relation data, due to the fact
that a given unit can only publish its data for the entire relation, rather than
a specific remote unit, plus the fact that a given unit may want to submit
multiple requests.

The request and response Endpoint classes can help with this.  To use this
pattern, the interface layer should define classes which inherit from
:class:`~charms.reactive.patterns.request_response.RequesterEndpoint`
and
:class:`~charms.reactive.patterns.request_response.ResponderEndpoint`
instead of directly from :class:`~charms.reactive.endpoints.Endpoint`.
It would then also need to define subclasses of
:class:`~charms.reactive.patterns.request_response.BaseRequest` and
:class:`~charms.reactive.patterns.request_response.BaseResponse` which
define some 
:class:`~charms.reactive.patterns.request_response.Field` attributes.
Then, requesting charms can
:meth:`~charms.reactive.patterns.request_response.BaseRequest.create`
requests, responding charms can process 
:meth:`~charms.reactive.patterns.request_response.ResponderEndpoint.new_requests`
and 
:meth:`~charms.reactive.patterns.request_response.BaseRequest.respond`
to them, and finally the requesting charm can then use those
:meth:`~charms.reactive.patterns.request_response.RequesterEndpoint.responses`.

An example of using this pattern can be found in the grafana-dashboard_ interface.

.. _grafana-dashboard: https://github.com/juju-solutions/interface-grafana-dashboard
