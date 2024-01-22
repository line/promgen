Alerting Rules
==============

Promgen supports the concept of a global set of rules and then configuring overrides at the
Service or Project level

When working with many services, there are times that a global rule will not cover all use cases.
In this case, Promgen allows the user to override a parent rule using an <exclude> tag.

For example, we may want to check overall file system usage across all of our machines

.. code-block:: none

    node_filesystem_free / node_filesystem_size < 0.20

This may be an acceptable default for our service, but perhaps a different service wants to be warned
at only 10%. Since the global rule already warns us at 20% we need to do something different. Promgen
supports a special <exclude> tag to handle this use case

.. code-block:: none
    :caption: Original Rules

    node_filesystem_free{<exclude>}
        / node_filesystem_size{<exclude>} < 0.20
    node_filesystem_free{service="A", <exclude>}
        / node_filesystem_size{service="A", <exclude>} < 0.10
    node_filesystem_free{service="B"}
        / node_filesystem_size{service="B"} < 0.15


This will be properly expanded into the following rules so that we can have a general default but
be more specific with certain services

.. code-block:: none
    :caption: Expanded Rules

    node_filesystem_free{service=~"A|B"}
        / node_filesystem_size{service=~"A|B"} < 0.20
    node_filesystem_free{service="A",}
        / node_filesystem_size{service="A",} < 0.10
    node_filesystem_free{service="B"}
       / node_filesystem_size{service="B"} < 0.15


Visuallizing it as a hierarchy it would look like this

.. code-block:: yaml

    # Global Rule excludes children
    example_rule{service!~"A|B",}:
        # Service A override includes self
        - example_rule{service="A",}
        # Service B override includes self, but excludes children
        - example_rule{service="B", project!~"C"}:
            # Project Override
            - example_rule{project="C"}
