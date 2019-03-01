/*
# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
*/

Vue.config.devtools = true

var dataStore = {
    newSilence: { 'labels': {} },
    globalSilences: [],
    globalAlerts: [],
    globalMessages: []
};

var app = new Vue({
    el: '#vue',
    data: dataStore,
    methods: {
        toggleTarget: function (target) {
            let tgt = document.getElementById(target);
            tgt.classList.toggle('collapse');
        },
        silenceExpire: function (id) {
            fetch('/proxy/v1/silences/' + id, { method: 'DELETE' }).then(function (response) {
                location.reload();
            })
        },
        silenceChangeEvent: function (event) {
            this.newSilence[event.target.name] = event.target.value;
        },
        silenceSubmit: function (event) {
            let this_ = this;
            fetch('/proxy/v1/silences', { method: 'POST', body: JSON.stringify(this.newSilence) })
                .then(function (response) {
                    if (response.ok) {
                        location.reload();
                    } else {
                        return response.json()
                    }
                })
                .then(function (result) {
                    this_.globalMessages = [];
                    for (key in result.messages) {
                        this_.$set(this_.globalMessages, key, result.messages[key]);
                    }
                })
        },
        silenceRemoveLabel: function (label) {
            console.debug('silenceRemoveLabel', label)
            this.$delete(this.newSilence.labels, label)
        },
        showSilenceForm: function (event) {
            document.getElementById('silence-form').classList.remove('collapse');
            scroll(0, 0);
        },
        silenceAppendLabel: function (event) {
            console.debug('silenceAppendLabel', event.target.dataset);
            this.$set(this.newSilence.labels, event.target.dataset.label, event.target.dataset.value);
            this.showSilenceForm(event);
        },
        silenceSetLabels: function (event) {
            console.debug('silenceSetLabels', event.target.dataset);
            this.$set(this.newSilence, 'labels', {});
            for (key in event.target.dataset) {
                this.$set(this.newSilence.labels, key, event.target.dataset[key]);
            }
            this.showSilenceForm(event);
        },
        silenceAlert: function (alert) {
            this.$set(this.newSilence, 'labels', {});
            for (key in alert.labels) {
                this.$set(this.newSilence.labels, key, alert.labels[key]);
            }
            this.showSilenceForm(event);
        },
        filterBy: function (source, label) {
            let labels = new Set();
            for (var a in source.filter(x => x.status.state == 'active')) {
                for (var l in source[a].labels) {
                    if (l == label) {
                        labels.add(source[a].labels[label]);
                    }
                }
            }
            return labels;
        },
        fetchSilences: function () {
            let this_ = this;
            fetch('/proxy/v1/silences')
                .then(response => response.json())
                .then(function (silences) {
                    this_.globalSilences = silences.data;

                    // Pull out the matchers and do a simpler label map
                    // To make other code easier
                    for (var i in this_.globalSilences) {
                        var silence = this_.globalSilences[i];
                        silence.labels = {}
                        for (var m in silence.matchers) {
                            let matcher = silence.matchers[m]
                            silence.labels[matcher.name] = matcher.value
                        }
                    }
                });
        },
        fetchAlerts: function () {
            let this_ = this;
            fetch('/proxy/v1/alerts')
                .then(response => response.json())
                .then(function (alerts) {
                    this_.globalAlerts = alerts.data;
                });

        }

    },
    computed: {
        alertLabelsService: function () {
            return this.filterBy(this.globalAlerts, 'service');
        },
        alertLabelsProject: function () {
            return this.filterBy(this.globalAlerts, 'project');
        },
        alertLabelsRule: function () {
            return this.filterBy(this.globalAlerts, 'alertname');
        },
        silenceLabelsService: function () {
            return this.filterBy(this.globalSilences, 'service');
        },
        silenceLabelsProject: function () {
            return this.filterBy(this.globalSilences, 'project');
        },
        filterActiveAlerts: function () {
            return this.globalAlerts.filter(alert => alert.status.state == 'active');
        },
        filterActiveSilences: function () {
            return this.globalSilences.filter(silence => silence.status.state == 'active');
        }
    },
    mounted: function () {
        this.fetchAlerts();
        this.fetchSilences();
    }
})
