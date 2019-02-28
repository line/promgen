/*
# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
*/

Vue.config.devtools = true

var dataStore = {
    newSilence: { 'labels': {} },
    globalSilences: [],
    globalAlerts: []
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
            fetch('/proxy/v1/silences', { method: 'POST', body: JSON.stringify(this.newSilence) }).then(function (response) {
                location.reload();
            })
        },
        silenceRemoveLabel: function (label) {
            console.log('silenceRemoveLabel', label)
            this.$delete(this.newSilence.labels, label)
        },
        showSilenceForm: function (event) {
            document.getElementById('silence-form').classList.remove('collapse');
            scroll(0, 0);
        },
        silenceAppendLabel: function (event) {
            console.log('silenceAppendLabel', event.target.dataset);
            this.$set(this.newSilence.labels, event.target.dataset.label, event.target.dataset.value);
            this.showSilenceForm(event);
        },
        silenceSetLabels: function (event) {
            console.log('silenceSetLabels', event.target.dataset);
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
        fetchSilences: function () {
            let this_ = this;
            fetch('/proxy/v1/silences')
                .then(function (response) {
                    return response.json();
                })
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
                .then(function (response) {
                    return response.json();
                })
                .then(function (alerts) {
                    this_.globalAlerts = alerts.data;
                });

        }
    },
    computed: {
        alertLabelsService: function () {
            return new Set(this.globalAlerts
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.service)
                .map(x => x.labels.service)
                .sort()
            );
        },
        alertLabelsProject: function () {
            return new Set(this.globalAlerts
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.project)
                .map(x => x.labels.project)
                .sort()
            );
        },
        alertLabelsRule: function () {
            return new Set(this.globalAlerts
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.alertname)
                .map(x => x.labels.alertname)
                .sort()
            );
        },
        silenceLabelsService: function () {
            return new Set(this.globalSilences
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.service)
                .map(x => x.labels.service)
                .sort()
            );
        },
        silenceLabelsProject: function () {
            return new Set(this.globalSilences
                .filter(x => x.status.state == 'active')
                .filter(x => x.labels.project)
                .map(x => x.labels.project)
                .sort()
            );
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
