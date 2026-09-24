Custom Labels
=============

Custom labels are a powerful feature that allows to add more labels to metrics when Prometheus
scrapes the targets.

By default, there are no custom labels. The Promgen's administrator can add custom labels to a
specific model such as Service or Project via the Django's admin interface. Once added, Promgen will
automatically add those labels as new fields of the model on the web interface and in the API schema.
After user inputs the values for those labels, Promgen will add them to the targets when generating
the Prometheus configuration file.

Here is an example of a custom label added to the Service model:

1. The administrator adds a custom label called "environment" to the Service model via the Django's
admin interface.

.. image:: /images/custom_labels_1.png

2. The user creates a new Service called "webapp" and inputs the value "production" for the
"environment" label.

.. image:: /images/custom_labels_2.png

3. The "environment" label is now displayed as a new field in the Service model on the web
interface and also in the API schema.

.. image:: /images/custom_labels_3.png

4. Promgen generates the Prometheus configuration file and adds the label "environment=production"
to the targets associated with the "webapp" service.

.. code-block:: none
    :caption: Scrape config

    [
      {
        "labels": {
            ...
          "environment": "production"
        },
        "targets": [
            ...
        ]
      }
    ]


Notes
-----

The name of the custom label must be a valid Prometheus label name. It also cannot be a reserved
label name such as "job" or "instance" or any other label name that Prometheus uses internally.

The value of the custom label must be a valid Prometheus label value. If user inputs an empty value
for the custom label, Promgen will not add that label to the targets.

Custom labels are unique per model but not unique across models. If a custom label with the same
name is added to both the Service and Project models, Promgen will prioritize the custom label from
the Project model when generating the Prometheus configuration file.
