# Copyright in layered charms

Each layer must state its copyright in a file named `LICENSE.layer-<layer-name>`. This is to ensure that `charm build` will preserve the copyright declaration of each layer.


The built charm will contain all the licenses of every layer as shown in the following example.

```
.
├── hooks
│   ├── ...
├── reactive
│   ├── ...
├── LICENSE.layer-apt
├── LICENSE.layer-lets-encrypt
├── LICENSE.layer-nginx
├── LICENSE.layer-ssl-termination-proxy
└── README.md
```
